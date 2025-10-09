"""
LLM Provider abstraction layer for FastAPI
Supports multiple providers with automatic fallback
"""
import os
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from enum import Enum

import cohere
import together
from groq import Groq
import openai
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    COHERE = "cohere"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self):
        self.api_key = None
        self.client = None
        self.model = None
        self.initialized = False

    @abstractmethod
    def initialize(self):
        """Initialize the provider client"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text from prompt"""
        pass

    @abstractmethod
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context"""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        pass

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Stream text generation token by token (optional)

        Not all providers need to implement this.
        Default implementation returns None.
        """
        return None


class OpenAIProvider(LLMProvider):
    """OpenAI/GPT provider implementation"""

    def initialize(self):
        """Initialize OpenAI client"""
        if self.initialized:
            return

        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.model = settings.OPENAI_MODEL or "gpt-4o-mini"
        self.initialized = True
        logger.info(f"OpenAI provider initialized with model {self.model}")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using OpenAI"""
        if not self.initialized:
            self.initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context"""
        system_message = f"Use the following context to answer the question:\n\n{context}"

        if not self.initialized:
            self.initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation with context error: {e}")
            raise

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "OpenAI",
            "model": self.model,
            "initialized": self.initialized
        }

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Stream generation for OpenAI"""
        if not self.initialized:
            self.initialize()

        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": prompt})

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


class CohereProvider(LLMProvider):
    """Cohere provider implementation"""

    def initialize(self):
        """Initialize Cohere client"""
        if self.initialized:
            return

        self.api_key = settings.COHERE_API_KEY
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not configured")

        self.client = cohere.AsyncClient(self.api_key)
        self.model = "command-r-plus"
        self.initialized = True
        logger.info("Cohere provider initialized")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using Cohere"""
        if not self.initialized:
            self.initialize()

        try:
            response = await self.client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model=self.model,
                **kwargs
            )
            return response.generations[0].text
        except Exception as e:
            logger.error(f"Cohere generation error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context using Cohere's RAG"""
        if not self.initialized:
            self.initialize()

        try:
            # Cohere supports documents parameter for RAG
            response = await self.client.chat(
                message=prompt,
                documents=[{"text": context}],
                max_tokens=max_tokens,
                temperature=temperature,
                model=self.model,
                **kwargs
            )
            return response.text
        except Exception as e:
            logger.error(f"Cohere RAG generation error: {e}")
            raise

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "Cohere",
            "model": self.model,
            "initialized": self.initialized
        }

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Stream generation for Cohere

        Uses Cohere's streaming API if available, otherwise simulates streaming.
        """
        if not self.initialized:
            self.initialize()

        try:
            # Try native streaming with Cohere's chat endpoint
            if context:
                # Use chat endpoint with documents for better RAG
                stream = await self.client.chat_stream(
                    message=prompt,
                    documents=[{"text": context}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=self.model,
                    **kwargs
                )
            else:
                # Use chat endpoint without documents
                stream = await self.client.chat_stream(
                    message=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=self.model,
                    **kwargs
                )

            # Stream tokens as they arrive
            async for event in stream:
                if event.event_type == "text-generation":
                    yield event.text

        except AttributeError:
            # Fallback if streaming not available - simulate it
            logger.info("Cohere streaming not available, simulating...")

            if context:
                response = await self.generate_with_context(prompt, context, max_tokens, temperature, **kwargs)
            else:
                response = await self.generate(prompt, max_tokens, temperature, **kwargs)

            # Simulate streaming by yielding words
            words = response.split(' ')
            for i, word in enumerate(words):
                if i > 0:
                    yield ' '
                yield word
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Cohere streaming error: {e}")
            raise


class GroqProvider(LLMProvider):
    """Groq provider implementation"""

    def initialize(self):
        """Initialize Groq client"""
        if self.initialized:
            return

        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")

        self.client = Groq(api_key=self.api_key)
        self.model = "mixtral-8x7b-32768"
        self.initialized = True
        logger.info("Groq provider initialized")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using Groq"""
        if not self.initialized:
            self.initialize()

        try:
            # Groq uses sync client, wrap in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context"""
        system_message = f"Context:\n{context}\n\nQuestion: {prompt}"
        return await self.generate(system_message, max_tokens, temperature, **kwargs)

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "Groq",
            "model": self.model,
            "initialized": self.initialized
        }

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Simulated streaming for Groq

        Note: Groq's sync client doesn't support native streaming,
        so we simulate it by chunking the response.
        """
        if not self.initialized:
            self.initialize()

        try:
            # Generate complete response
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt
            response = await self.generate(full_prompt, max_tokens, temperature, **kwargs)

            # Simulate streaming by yielding words
            words = response.split(' ')
            for i, word in enumerate(words):
                if i > 0:
                    yield ' '
                yield word
                # Small delay to simulate streaming
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Groq streaming simulation error: {e}")
            raise


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider implementation (using OpenAI-compatible API)"""

    def initialize(self):
        """Initialize DeepSeek client"""
        if self.initialized:
            return

        self.api_key = settings.DEEPSEEK_API_KEY
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        # DeepSeek uses OpenAI-compatible API
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-chat"
        self.initialized = True
        logger.info("DeepSeek provider initialized")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using DeepSeek"""
        if not self.initialized:
            self.initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek generation error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context"""
        system_message = f"Context:\n{context}"

        if not self.initialized:
            self.initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek generation with context error: {e}")
            raise

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "DeepSeek",
            "model": self.model,
            "initialized": self.initialized
        }

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Stream generation for DeepSeek (OpenAI-compatible)"""
        if not self.initialized:
            self.initialize()

        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": prompt})

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"DeepSeek streaming error: {e}")
            raise


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""

    def initialize(self):
        """Initialize Gemini client"""
        if self.initialized:
            return

        self.api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL or "gemini-1.5-flash")
        self.initialized = True
        logger.info("Gemini provider initialized")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using Gemini"""
        if not self.initialized:
            self.initialize()

        try:
            # Gemini uses sync client, wrap in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    )
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text with context"""
        full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
        return await self.generate(full_prompt, max_tokens, temperature, **kwargs)

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "Google Gemini",
            "model": settings.GEMINI_MODEL or "gemini-1.5-flash",
            "initialized": self.initialized
        }

    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Stream generation for Gemini"""
        if not self.initialized:
            self.initialize()

        try:
            # Combine context and prompt
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            # Gemini uses sync streaming, wrap in executor
            loop = asyncio.get_event_loop()

            # Create streaming response
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    ),
                    stream=True
                )
            )

            # Stream chunks
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise


class LLMProviderManager:
    """Manager for LLM providers with automatic fallback"""

    def __init__(self):
        self.providers = {}
        self.current_provider = None
        self.fallback_order = [
            ProviderType.DEEPSEEK,
            ProviderType.GEMINI,
            ProviderType.OPENAI,
            ProviderType.COHERE,
            ProviderType.GROQ,
        ]

    def get_provider(self, provider_type: Optional[ProviderType] = None) -> LLMProvider:
        """Get a specific provider or the default"""
        if provider_type is None:
            # Read from environment variable directly for real-time updates
            current_provider = os.environ.get('LLM_PROVIDER', settings.LLM_PROVIDER) or ProviderType.DEEPSEEK
            provider_type = ProviderType(current_provider)

        # Check cache
        if provider_type in self.providers:
            return self.providers[provider_type]

        # Create new provider
        provider = self._create_provider(provider_type)
        self.providers[provider_type] = provider
        return provider

    def _create_provider(self, provider_type: ProviderType) -> LLMProvider:
        """Create a provider instance"""
        provider_map = {
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.COHERE: CohereProvider,
            ProviderType.GROQ: GroqProvider,
            ProviderType.DEEPSEEK: DeepSeekProvider,
            ProviderType.GEMINI: GeminiProvider,
        }

        provider_class = provider_map.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")

        return provider_class()

    async def generate_with_fallback(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        context: Optional[str] = None,
        **kwargs
    ) -> tuple[str, str]:
        """
        Generate text with automatic fallback

        Returns:
            tuple: (generated_text, provider_used)
        """
        errors = []

        for provider_type in self.fallback_order:
            try:
                provider = self.get_provider(provider_type)

                if context:
                    result = await provider.generate_with_context(
                        prompt, context, max_tokens, temperature, **kwargs
                    )
                else:
                    result = await provider.generate(
                        prompt, max_tokens, temperature, **kwargs
                    )

                logger.info(f"Successfully generated with {provider_type}")
                return result, provider_type

            except Exception as e:
                error_msg = f"{provider_type} failed: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

        # All providers failed
        error_summary = "\n".join(errors)
        logger.error(f"All providers failed:\n{error_summary}")
        raise Exception(f"All LLM providers failed:\n{error_summary}")

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get information about available providers"""
        available = []

        for provider_type in ProviderType:
            try:
                provider = self.get_provider(provider_type)
                provider.initialize()
                available.append({
                    "type": provider_type,
                    "info": provider.get_info(),
                    "available": True
                })
            except Exception as e:
                available.append({
                    "type": provider_type,
                    "available": False,
                    "error": str(e)
                })

        return available


# Global manager instance
llm_manager = LLMProviderManager()