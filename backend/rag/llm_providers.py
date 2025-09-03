import os
import json
import requests
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
from django.conf import settings
from dotenv import load_dotenv

import cohere
import together
from groq import Groq
import openai
import google.generativeai as genai


class ConfigManager:
    """Gerenciador centralizado e otimizado de configurações LLM"""
    
    _env_loaded = False
    _config_cache = {}
    _cache_lock = threading.Lock()
    
    @classmethod
    def get_config(cls, key: str, default=None):
        """Busca configuração com fallback chain otimizado"""
        # Cache hit - performance crítica
        with cls._cache_lock:
            if key in cls._config_cache:
                return cls._config_cache[key]
        
        # Ordem de prioridade: os.environ → Django settings → default
        value = os.environ.get(key)
        if value is None:
            value = getattr(settings, key, None)
        
        final_value = value if value is not None else default
        
        # Cache para próximas chamadas
        with cls._cache_lock:
            cls._config_cache[key] = final_value
        
        return final_value
    
    @classmethod
    def reload_env(cls):
        """Recarrega .env de forma otimizada (apenas quando necessário)"""
        if not cls._env_loaded:
            env_path = Path(__file__).parent.parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path, override=True)
                cls._env_loaded = True
                cls._sync_with_django()
    
    @classmethod
    def _sync_with_django(cls):
        """Sincroniza configurações críticas com Django settings"""
        critical_configs = [
            'LLM_PROVIDER', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY',
            'GEMINI_API_KEY', 'COHERE_API_KEY', 'GROQ_API_KEY', 'TOGETHER_API_KEY'
        ]
        
        if hasattr(settings, '_wrapped'):
            for config in critical_configs:
                value = os.getenv(config)
                if value is not None:
                    setattr(settings._wrapped, config, value)
    
    @classmethod
    def clear_cache(cls):
        """Limpa cache de configurações (usado no reload)"""
        with cls._cache_lock:
            cls._config_cache.clear()
    
    @classmethod
    def set_config(cls, key: str, value: str):
        """Define configuração no ambiente (para switch de provider)"""
        os.environ[key] = value
        with cls._cache_lock:
            cls._config_cache[key] = value


class ProviderCache:
    """Cache inteligente para instâncias de providers com TTL"""
    
    def __init__(self, ttl_seconds=3600):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
    
    def get(self, key: str):
        """Busca provider do cache com verificação de TTL"""
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
                else:
                    # Expirou - remover e cleanup
                    provider = self._cache.pop(key, None)
                    self._timestamps.pop(key, None)
                    if provider and hasattr(provider, 'cleanup'):
                        provider.cleanup()
        return None
    
    def set(self, key: str, provider):
        """Armazena provider no cache"""
        with self._lock:
            self._cache[key] = provider
            self._timestamps[key] = time.time()
    
    def remove(self, key: str):
        """Remove provider específico do cache"""
        with self._lock:
            provider = self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            if provider and hasattr(provider, 'cleanup'):
                provider.cleanup()
    
    def clear(self):
        """Limpa todo o cache"""
        with self._lock:
            for provider in self._cache.values():
                if hasattr(provider, 'cleanup'):
                    provider.cleanup()
            self._cache.clear()
            self._timestamps.clear()


class LLMProvider(ABC):
    """Interface abstrata otimizada para provedores de LLM com lazy loading"""
    
    def __init__(self):
        self._api_key = None
        self._client = None
        self._model = None
        self._initialized = False
        self._lock = threading.Lock()
    
    @property
    def api_key(self):
        """Lazy loading da API key com fallback chain"""
        if self._api_key is None:
            with self._lock:
                if self._api_key is None:
                    self._api_key = self._get_api_key()
        return self._api_key
    
    @property
    def client(self):
        """Lazy loading do cliente"""
        if self._client is None and self.api_key:
            with self._lock:
                if self._client is None:
                    self._client = self._create_client()
        return self._client
    
    @property
    def model(self):
        """Lazy loading do modelo"""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._get_model()
        return self._model
    
    @abstractmethod
    def _get_api_key(self) -> Optional[str]:
        """Implementar busca específica da API key para cada provider"""
        pass
    
    @abstractmethod
    def _create_client(self):
        """Implementar criação específica do cliente para cada provider"""
        pass
    
    @abstractmethod
    def _get_model(self) -> str:
        """Implementar busca específica do modelo para cada provider"""
        pass
    
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
    
    def is_available(self) -> bool:
        """Verifica se o provedor está disponível (implementação padrão)"""
        return bool(self.api_key and self.client)
    
    def reload_config(self):
        """Recarrega configurações do provider (força refresh)"""
        with self._lock:
            self._api_key = None
            self._client = None
            self._model = None
            self._initialized = False
    
    def cleanup(self):
        """Cleanup de recursos do provider"""
        with self._lock:
            if self._client and hasattr(self._client, 'close'):
                try:
                    self._client.close()
                except:
                    pass
            self._client = None

class CohereProvider(LLMProvider):
    """Provedor Cohere - Recomendado para RAG com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain"""
        return ConfigManager.get_config('COHERE_API_KEY')
    
    def _create_client(self):
        """Cria cliente Cohere com lazy loading"""
        try:
            return cohere.Client(self.api_key)
        except Exception:
            return None
    
    def _get_model(self) -> str:
        """Retorna modelo otimizado para RAG"""
        return ConfigManager.get_config('COHERE_MODEL', 'command-r-plus')
    
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
                    preamble="Você é o Knight, assistente de RH da empresa. "
                            "Responda em português de forma clara e natural. "
                            "Use as informações dos documentos fornecidos. "
                            "Quando tiver documentos ou links relevantes disponíveis, mencione-os na resposta. "
                            "Se tiver acesso a documentos para download, informe que estão disponíveis. "
                            "Seja consistente: se documentos estão sendo retornados, você TEM acesso a eles."
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
    """Provedor Together AI com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.together.xyz/v1"
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain"""
        return ConfigManager.get_config('TOGETHER_API_KEY')
    
    def _create_client(self):
        """Together usa requests HTTP, não cliente específico"""
        return True  # Placeholder - Together usa requests direto
    
    def _get_model(self) -> str:
        """Retorna modelo Together AI"""
        return ConfigManager.get_config('TOGETHER_MODEL', 'meta-llama/Llama-2-70b-chat-hf')
    
    def is_available(self) -> bool:
        """Verifica disponibilidade específica do Together"""
        return bool(self.api_key)
    
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
                "e sugira entrar em contato com o RH. "
                "Quando houver LINKS ÚTEIS ou DOCUMENTOS PARA DOWNLOAD disponíveis no contexto, "
                "mencione-os na sua resposta quando forem relevantes para ajudar o usuário."
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
                timeout=15  # Reduzido para velocidade
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
    """Provedor Groq - Rápido para inferência com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain"""
        return ConfigManager.get_config('GROQ_API_KEY')
    
    def _create_client(self):
        """Cria cliente Groq com lazy loading"""
        try:
            return Groq(api_key=self.api_key)
        except Exception:
            return None
    
    def _get_model(self) -> str:
        """Retorna modelo otimizado para velocidade"""
        return ConfigManager.get_config('GROQ_MODEL', 'llama3-70b-8192')
    
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
                "e sugira entrar em contato com o RH. "
                "Quando houver LINKS ÚTEIS ou DOCUMENTOS PARA DOWNLOAD disponíveis no contexto, "
                "mencione-os na sua resposta quando forem relevantes para ajudar o usuário."
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


class DeepSeekProvider(LLMProvider):
    """Provedor DeepSeek - API compatível com OpenAI com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.deepseek.com"
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain"""
        return ConfigManager.get_config('DEEPSEEK_API_KEY')
    
    def _create_client(self):
        """DeepSeek usa requests HTTP, não cliente específico"""
        return True  # Placeholder - DeepSeek usa requests direto
    
    def _get_model(self) -> str:
        """Retorna modelo DeepSeek"""
        return ConfigManager.get_config('DEEPSEEK_MODEL', 'deepseek-chat')
    
    def is_available(self) -> bool:
        """Verifica disponibilidade específica do DeepSeek"""
        return bool(self.api_key)
    
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
                "Você é o Knight, assistente de RH da empresa. "
                "Responda em português brasileiro de forma clara e direta. "
                "Use as informações do contexto fornecido. "
                "Quando tiver documentos ou links relevantes disponíveis, mencione-os na resposta. "
                "Se tiver acesso a documentos para download, informe que estão disponíveis. "
                "Seja consistente: se documentos estão sendo retornados, você TEM acesso a eles. "
                "Seja natural e conversacional."
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
                timeout=15  # Reduzido para velocidade
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


class OpenAIProvider(LLMProvider):
    """Provedor OpenAI - GPT-4 e GPT-3.5 com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain"""
        return ConfigManager.get_config('OPENAI_API_KEY')
    
    def _create_client(self):
        """Cria cliente OpenAI com lazy loading"""
        try:
            return openai.OpenAI(api_key=self.api_key)
        except Exception:
            return None
    
    def _get_model(self) -> str:
        """Retorna modelo OpenAI"""
        return ConfigManager.get_config('OPENAI_MODEL', 'gpt-4o-mini')
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta usando OpenAI"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'OpenAI não está configurado ou API key inválida',
                    'provider': 'openai'
                }
            
            system_prompt = (
                "Você é o Knight, assistente de RH da empresa. "
                "Responda em português brasileiro de forma clara e direta. "
                "Use as informações do contexto fornecido. "
                "Quando tiver documentos ou links relevantes disponíveis, mencione-os na resposta. "
                "Se tiver acesso a documentos para download, informe que estão disponíveis. "
                "Seja consistente: se documentos estão sendo retornados, você TEM acesso a eles. "
                "Seja natural e conversacional."
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if context:
                context_text = "\n\n".join([f"Documento {i+1}:\n{doc}" for i, doc in enumerate(context)])
                user_message = f"Contexto:\n{context_text}\n\nPergunta: {prompt}"
            else:
                user_message = prompt
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30
            )
            
            usage = response.usage
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'model': self.model,
                'provider': 'openai',
                'documents_used': len(context) if context else 0,
                'usage': {
                    'input_tokens': usage.prompt_tokens,
                    'output_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                error_msg = "Rate limit excedido. Tente novamente em alguns segundos."
            elif "insufficient quota" in error_msg.lower():
                error_msg = "Cota da API OpenAI esgotada."
            elif "invalid api key" in error_msg.lower():
                error_msg = "Chave da API OpenAI inválida."
            
            return {
                'success': False,
                'error': f"OpenAI Error: {error_msg}",
                'provider': 'openai'
            }
    
    def is_available(self) -> bool:
        """Verifica se o OpenAI está disponível"""
        return bool(self.api_key)


class GeminiProvider(LLMProvider):
    """Provedor Google Gemini com lazy loading otimizado"""
    
    def __init__(self):
        super().__init__()
        self._configured = False
    
    def _get_api_key(self) -> Optional[str]:
        """Busca API key com fallback chain (Google ou Gemini)"""
        key = ConfigManager.get_config('GEMINI_API_KEY')
        if not key:
            key = ConfigManager.get_config('GOOGLE_API_KEY')
        return key
    
    def _create_client(self):
        """Cria cliente Gemini com lazy loading"""
        try:
            if not self._configured and self.api_key:
                genai.configure(api_key=self.api_key)
                self._configured = True
            return genai.GenerativeModel(self.model)
        except Exception:
            return None
    
    def _get_model(self) -> str:
        """Retorna modelo Gemini"""
        return ConfigManager.get_config('GEMINI_MODEL', 'gemini-1.5-flash')
    
    def is_available(self) -> bool:
        """Verifica disponibilidade específica do Gemini"""
        return bool(self.api_key)
    
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
                "Você é o Knight, assistente de RH da empresa. "
                "Responda em português brasileiro de forma clara e direta. "
                "Use as informações do contexto fornecido. "
                "Quando tiver documentos ou links relevantes disponíveis, mencione-os na resposta. "
                "Se tiver acesso a documentos para download, informe que estão disponíveis. "
                "Seja consistente: se documentos estão sendo retornados, você TEM acesso a eles. "
                "Seja natural e conversacional."
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
    """Gerenciador otimizado de provedores LLM com lazy loading, cache e hot reload inteligente"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LLMManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Inicialização única e thread-safe"""
        self._provider_cache = ProviderCache(ttl_seconds=3600)  # Cache 1h
        self._config_manager = ConfigManager()
        self._fallback_order = ['openai', 'deepseek', 'gemini', 'cohere', 'groq', 'together']
        self._provider_classes = {
            'openai': OpenAIProvider,
            'deepseek': DeepSeekProvider,
            'cohere': CohereProvider,
            'together': TogetherProvider,
            'groq': GroqProvider,
            'gemini': GeminiProvider,
            'mock': MockProvider
        }
        
        # Carregar configurações iniciais
        self._config_manager.reload_env()
        self._primary_provider = self._config_manager.get_config('LLM_PROVIDER', 'deepseek')
        self._initialized = True
    
    @property
    def primary_provider(self) -> str:
        """Lazy loading do provider primário"""
        return self._config_manager.get_config('LLM_PROVIDER', self._primary_provider)
    
    def _get_provider(self, name: str) -> Optional[LLMProvider]:
        """Lazy loading otimizado de providers com cache"""
        # Verificar cache primeiro
        provider = self._provider_cache.get(name)
        if provider is not None:
            return provider
        
        # Criar provider apenas se necessário
        if name in self._provider_classes:
            try:
                provider = self._provider_classes[name]()
                self._provider_cache.set(name, provider)
                return provider
            except Exception:
                return None
        
        return None
    
    def reload_config(self):
        """Força recarregamento otimizado das configurações"""
        self._config_manager.reload_env()
        self._config_manager.clear_cache()
        return True
    
    def reload_provider(self, provider_name: str):
        """Recarrega apenas um provider específico (otimização crítica)"""
        if provider_name in self._provider_classes:
            # Remover do cache - será recriado no próximo uso
            self._provider_cache.remove(provider_name)
            self._config_manager.clear_cache()
            return True
        return False
    
    def switch_provider(self, new_provider: str):
        """Muda provider de forma otimizada sem recriar outros"""
        if new_provider in self._provider_classes:
            self._config_manager.set_config('LLM_PROVIDER', new_provider)
            self._primary_provider = new_provider
            return True
        return False
    
    def get_current_provider(self) -> str:
        """Retorna o provedor atual"""
        return self.primary_provider
    
    def get_available_providers(self) -> List[str]:
        """Lista provedores disponíveis com lazy loading"""
        available = []
        for name in self._provider_classes.keys():
            if name == 'mock':
                available.append(name)  # Mock sempre disponível
                continue
            
            # Lazy check - só cria provider se não estiver no cache
            provider = self._provider_cache.get(name)
            if provider is None:
                # Check rápido sem criar o provider
                api_key = self._config_manager.get_config(f'{name.upper()}_API_KEY')
                if api_key:
                    available.append(name)
            else:
                if provider.is_available():
                    available.append(name)
        
        return available
    
    @property
    def fallback_order(self) -> List[str]:
        """Retorna a ordem de fallback dos providers (read-only)"""
        return self._fallback_order.copy()
    
    def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        provider: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera resposta otimizada com lazy loading e fallback automático"""
        
        # Usar provedor especificado ou primário
        target_provider = provider or self.primary_provider
        
        # Tentar provedor principal com lazy loading
        llm_provider = self._get_provider(target_provider)
        if llm_provider and llm_provider.is_available():
            result = llm_provider.generate_response(prompt, context, **kwargs)
            if result.get('success'):
                return result
        
        # Fallback otimizado para outros provedores
        for fallback_provider in self._fallback_order:
            if fallback_provider == target_provider:
                continue
                
            llm_provider = self._get_provider(fallback_provider)
            if llm_provider and llm_provider.is_available():
                result = llm_provider.generate_response(prompt, context, **kwargs)
                if result.get('success'):
                    result['fallback_used'] = True
                    result['original_provider'] = target_provider
                    result['fallback_provider'] = fallback_provider
                    return result
        
        # Se nenhum provedor funcionou
        return {
            'success': False,
            'error': 'Nenhum provedor LLM disponível',
            'provider': 'none',
            'attempted_providers': [target_provider] + self._fallback_order
        }
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso dos providers"""
        stats = {
            'cache_size': len(self._provider_cache._cache),
            'primary_provider': self.primary_provider,
            'available_providers': self.get_available_providers(),
            'cached_providers': list(self._provider_cache._cache.keys()),
            'fallback_order': self._fallback_order
        }
        return stats
    
    def clear_cache(self):
        """Limpa todo o cache de providers"""
        self._provider_cache.clear()
        self._config_manager.clear_cache()
    
    def cleanup(self):
        """Cleanup completo do manager"""
        self.clear_cache()
        with self._lock:
            self._initialized = False
    
    def get_dynamic_parameters(self, query_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Determina parâmetros dinâmicos baseados na análise da query"""
        
        query_analysis = query_analysis or {}
        complexity = query_analysis.get('complexity_score', 0.5)
        urgency = query_analysis.get('urgency_level', 'normal')
        creativity_needed = query_analysis.get('needs_creativity', False)
        
        # Temperatura baseada na complexidade e criatividade
        if creativity_needed or 'analis' in str(query_analysis.get('query', '')).lower():
            temperature = 0.8
        elif urgency in ['high', 'critical']:
            temperature = 0.4  # Mais determinístico para urgências
        elif complexity > 0.7:
            temperature = 0.7
        else:
            temperature = 0.6
        
        # Max tokens baseado na complexidade
        if urgency in ['high', 'critical']:
            max_tokens = 300
        elif complexity > 0.7:
            max_tokens = 800
        elif complexity < 0.3:
            max_tokens = 400
        else:
            max_tokens = 600
            
        # Top-p para controlar diversidade
        top_p = 0.9 if creativity_needed else 0.8
        
        # Penalidades para evitar repetição
        frequency_penalty = 0.3 if creativity_needed else 0.1
        presence_penalty = 0.2 if creativity_needed else 0.1
        
        return {
            'temperature': temperature,
            'max_tokens': max_tokens,
            'top_p': top_p,
            'frequency_penalty': frequency_penalty,
            'presence_penalty': presence_penalty
        }
    
    def generate_natural_response(
        self,
        prompt: str,
        context: List[str] = None,
        query_analysis: Dict[str, Any] = None,
        **override_params
    ) -> Dict[str, Any]:
        """Gera resposta com parâmetros dinâmicos naturais"""
        
        # Obter parâmetros dinâmicos
        dynamic_params = self.get_dynamic_parameters(query_analysis)
        
        # Aplicar overrides se fornecidos
        dynamic_params.update(override_params)
        
        # Usar método generate_response existente com parâmetros dinâmicos
        return self.generate_response(
            prompt=prompt,
            context=context,
            **dynamic_params
        )


# Função global para obter instância singleton do LLMManager
def get_llm_manager():
    """Retorna instância singleton do LLMManager"""
    return LLMManager()


class MockProvider(LLMProvider):
    """Provider mock otimizado para testes - não precisa de configuração externa"""
    
    def __init__(self):
        super().__init__()
    
    def _get_api_key(self) -> Optional[str]:
        """Mock sempre tem 'API key' disponível"""
        return "mock-api-key"
    
    def _create_client(self):
        """Mock sempre tem 'client' disponível"""
        return True
    
    def _get_model(self) -> str:
        """Retorna modelo mock"""
        return "mock-model"
    
    def is_available(self) -> bool:
        """Mock está sempre disponível"""
        return True
    
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