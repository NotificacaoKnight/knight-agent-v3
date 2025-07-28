import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from django.conf import settings

import cohere
import together
from groq import Groq
import openai
import google.generativeai as genai

class LLMProvider(ABC):
    """Interface abstrata para provedores de LLM"""
    
    @abstractmethod
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando o LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor está disponível"""
        pass

class CohereProvider(LLMProvider):
    """Provedor Cohere - Recomendado para RAG"""
    
    def __init__(self):
        self.api_key = settings.COHERE_API_KEY
        self.client = cohere.Client(self.api_key) if self.api_key else None
        self.model = "command-r-plus"  # Modelo otimizado para RAG
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando Cohere"""
        try:
            # Preparar documentos de contexto
            documents = []
            if context:
                for i, doc in enumerate(context):
                    documents.append({
                        "id": str(i),
                        "text": doc
                    })
            
            # Usar RAG nativo do Cohere se houver contexto
            if documents:
                response = self.client.chat(
                    message=prompt,
                    documents=documents,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    preamble="Você é o Knight, um assistente IA interno da empresa. "
                            "Responda sempre em português brasileiro de forma clara e útil. "
                            "Use apenas as informações fornecidas nos documentos para responder. "
                            "Se não souber a resposta, diga que não tem informações suficientes "
                            "e sugira entrar em contato com o RH."
                )
                
                return {
                    'success': True,
                    'response': response.text,
                    'model': self.model,
                    'provider': 'cohere',
                    'documents_used': len(documents),
                    'citations': getattr(response, 'citations', [])
                }
            else:
                # Chat simples sem RAG
                response = self.client.chat(
                    message=prompt,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                return {
                    'success': True,
                    'response': response.text,
                    'model': self.model,
                    'provider': 'cohere'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'cohere'
            }
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.client)

class TogetherProvider(LLMProvider):
    """Provedor Together AI"""
    
    def __init__(self):
        self.api_key = settings.TOGETHER_API_KEY
        self.base_url = "https://api.together.xyz/v1"
        self.model = "meta-llama/Llama-2-70b-chat-hf"
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando Together AI"""
        try:
            # Construir prompt com contexto
            system_prompt = (
                "Você é o Knight, um assistente IA interno da empresa. "
                "Responda sempre em português brasileiro de forma clara e útil. "
                "Use apenas as informações fornecidas no contexto para responder. "
                "Se não souber a resposta, diga que não tem informações suficientes "
                "e sugira entrar em contato com o RH."
            )
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                full_prompt = f"{system_prompt}\n\nContexto:\n{context_text}\n\nPergunta: {prompt}\n\nResposta:"
            else:
                full_prompt = f"{system_prompt}\n\nPergunta: {prompt}\n\nResposta:"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'model': self.model,
                    'provider': 'together',
                    'documents_used': len(context) if context else 0
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'provider': 'together'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'together'
            }
    
    def is_available(self) -> bool:
        return bool(self.api_key)

class GroqProvider(LLMProvider):
    """Provedor Groq - Rápido para inferência"""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = "llama3-70b-8192"  # Modelo rápido
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando Groq"""
        try:
            system_prompt = (
                "Você é o Knight, um assistente IA interno da empresa. "
                "Responda sempre em português brasileiro de forma clara e útil. "
                "Use apenas as informações fornecidas no contexto para responder. "
                "Se não souber a resposta, diga que não tem informações suficientes "
                "e sugira entrar em contato com o RH."
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                messages.append({"role": "user", "content": f"Contexto:\n{context_text}"})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'model': self.model,
                'provider': 'groq',
                'documents_used': len(context) if context else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'groq'
            }
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.client)

class OllamaProvider(LLMProvider):
    """Provedor Ollama - Self-hosted"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando Ollama"""
        try:
            system_prompt = (
                "Você é o Knight, um assistente IA interno da empresa. "
                "Responda sempre em português brasileiro de forma clara e útil. "
                "Use apenas as informações fornecidas no contexto para responder. "
                "Se não souber a resposta, diga que não tem informações suficientes "
                "e sugira entrar em contato com o RH."
            )
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                full_prompt = f"{system_prompt}\n\nContexto:\n{context_text}\n\nPergunta: {prompt}\n\nResposta:"
            else:
                full_prompt = f"{system_prompt}\n\nPergunta: {prompt}\n\nResposta:"
            
            data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'response': result['response'],
                    'model': self.model,
                    'provider': 'ollama',
                    'documents_used': len(context) if context else 0
                }
            else:
                return {
                    'success': False,
                    'error': f"Ollama Error: {response.status_code}",
                    'provider': 'ollama'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'ollama'
            }
    
    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

class DeepSeekProvider(LLMProvider):
    """Provedor DeepSeek - API compatível com OpenAI"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        self.base_url = "https://api.deepseek.com"
        self.model = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando DeepSeek"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'DeepSeek API key não configurada',
                    'provider': 'deepseek'
                }
            
            system_prompt = (
                "Você é o Knight, um assistente IA interno da empresa. "
                "Responda sempre em português brasileiro de forma clara e útil. "
                "Use apenas as informações fornecidas no contexto para responder. "
                "Se não souber a resposta baseada no contexto fornecido, diga que não tem informações suficientes "
                "e sugira entrar em contato com o RH ou a pessoa responsável."
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                messages.append({"role": "user", "content": f"Contexto:\n{context_text}"})
            
            messages.append({"role": "user", "content": prompt})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get('usage', {})
                
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'model': self.model,
                    'provider': 'deepseek',
                    'documents_used': len(context) if context else 0,
                    'usage': {
                        'input_tokens': usage.get('prompt_tokens', 0),
                        'output_tokens': usage.get('completion_tokens', 0),
                        'total_tokens': usage.get('total_tokens', 0)
                    }
                }
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('error', {}).get('message', error_detail)
                except:
                    pass
                
                return {
                    'success': False,
                    'error': f"DeepSeek API Error ({response.status_code}): {error_detail}",
                    'provider': 'deepseek'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'deepseek'
            }
    
    def is_available(self) -> bool:
        """Verifica se o DeepSeek está disponível"""
        return bool(self.api_key)

class GeminiProvider(LLMProvider):
    """Provedor Google Gemini"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"Erro ao inicializar Gemini: {e}")
                self.model = None
        else:
            self.model = None
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando Google Gemini"""
        try:
            if not self.model:
                return {
                    'success': False,
                    'error': 'Gemini não está configurado ou API key inválida',
                    'provider': 'gemini'
                }
            
            system_prompt = (
                "Você é o Knight, um assistente IA interno da empresa. "
                "Responda sempre em português brasileiro de forma clara e útil. "
                "Use apenas as informações fornecidas no contexto para responder. "
                "Se não souber a resposta baseada no contexto fornecido, diga que não tem informações suficientes "
                "e sugira entrar em contato com o RH ou a pessoa responsável."
            )
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                full_prompt = f"{system_prompt}\n\nContexto:\n{context_text}\n\nPergunta do usuário: {prompt}\n\nResposta:"
            else:
                full_prompt = f"{system_prompt}\n\nPergunta do usuário: {prompt}\n\nResposta:"
            
            # Configurar parâmetros de geração
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                top_k=40
            )
            
            # Gerar resposta
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            )
            
            if response.text:
                return {
                    'success': True,
                    'response': response.text,
                    'model': self.model_name,
                    'provider': 'gemini',
                    'documents_used': len(context) if context else 0,
                    'usage': {
                        'input_tokens': getattr(response.usage_metadata, 'prompt_token_count', 0),
                        'output_tokens': getattr(response.usage_metadata, 'candidates_token_count', 0),
                        'total_tokens': getattr(response.usage_metadata, 'total_token_count', 0)
                    } if hasattr(response, 'usage_metadata') else {}
                }
            else:
                # Resposta foi bloqueada por filtros de segurança
                return {
                    'success': False,
                    'error': 'Resposta bloqueada pelos filtros de segurança do Gemini',
                    'provider': 'gemini',
                    'safety_ratings': getattr(response, 'candidates', [{}])[0].get('safety_ratings', []) if hasattr(response, 'candidates') else []
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'gemini'
            }
    
    def is_available(self) -> bool:
        """Verifica se o Gemini está disponível"""
        return bool(self.api_key and self.model)

class LLMManager:
    """Gerenciador de provedores LLM com fallback automático"""
    
    def __init__(self):
        self.providers = {
            'deepseek': DeepSeekProvider(),
            'cohere': CohereProvider(),
            'together': TogetherProvider(),
            'groq': GroqProvider(),
            'ollama': OllamaProvider(),
            'gemini': GeminiProvider(),
            'mock': MockProvider()
        }
        self.primary_provider = settings.LLM_PROVIDER
        self.fallback_order = ['deepseek', 'gemini', 'cohere', 'groq', 'together', 'ollama']
    
    def get_available_providers(self) -> List[str]:
        """Lista provedores disponíveis"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        provider: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta com fallback automático"""
        
        # Usar provedor especificado ou primário
        target_provider = provider or self.primary_provider
        
        # Tentar provedor principal
        if target_provider in self.providers:
            llm_provider = self.providers[target_provider]
            if llm_provider.is_available():
                result = llm_provider.generate_response(prompt, context, **kwargs)
                if result['success']:
                    return result
        
        # Fallback para outros provedores
        for fallback_provider in self.fallback_order:
            if fallback_provider == target_provider:
                continue
                
            llm_provider = self.providers[fallback_provider]
            if llm_provider.is_available():
                result = llm_provider.generate_response(prompt, context, **kwargs)
                if result['success']:
                    result['fallback_used'] = True
                    result['original_provider'] = target_provider
                    return result
        
        # Se nenhum provedor funcionou
        return {
            'success': False,
            'error': 'Nenhum provedor LLM disponível',
            'provider': 'none'
        }


class MockProvider(LLMProvider):
    """Provider mock para testes - não precisa de configuração externa"""
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta mock para desenvolvimento"""
        
        # Resposta baseada no contexto se disponível
        if context and len(context) > 0:
            response = f"""Olá! Sou o Knight Agent, seu assistente IA corporativo.

Com base nos documentos disponíveis, posso ajudá-lo com informações sobre:
• Políticas e procedimentos da empresa
• Documentos corporativos
• Manuais e diretrizes

Sua pergunta: "{prompt[:100]}..."

*Esta é uma resposta de teste. Configure um provedor LLM real (Cohere, Groq, etc.) para respostas completas.*

**Documentos consultados:** {len(context)} documentos encontrados."""
        else:
            response = f"""Olá! Sou o Knight Agent, seu assistente IA corporativo.

Você perguntou: "{prompt[:100]}..."

Estou aqui para ajudar com:
• Consultas sobre documentos corporativos
• Políticas e procedimentos da empresa
• Informações gerais sobre a organização

*Esta é uma resposta de teste do sistema. Para respostas completas, configure um provedor LLM (Ollama, Cohere, Groq, etc.).*

Para configurar um provedor real, consulte o arquivo .env do projeto."""
        
        return {
            'success': True,
            'response': response,
            'provider': 'mock',
            'model': 'mock-model',
            'usage': {
                'input_tokens': len(prompt.split()),
                'output_tokens': len(response.split()),
                'total_tokens': len(prompt.split()) + len(response.split())
            },
            'response_time': 0.5,
            'context_used': len(context) > 0 if context else False
        }
    
    def is_available(self) -> bool:
        """Mock provider está sempre disponível"""
        return True