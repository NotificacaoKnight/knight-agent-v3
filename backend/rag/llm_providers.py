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

class LLMManager:
    """Gerenciador de provedores LLM com fallback automático"""
    
    def __init__(self):
        self.providers = {
            'cohere': CohereProvider(),
            'together': TogetherProvider(),
            'groq': GroqProvider(),
            'ollama': OllamaProvider()
        }
        self.primary_provider = settings.LLM_PROVIDER
        self.fallback_order = ['cohere', 'groq', 'together', 'ollama']
    
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