"""
Dynamic Prompt System V2 - Ultra-simplified, single prompt approach
Follows LangGraph best practices: provide context, let LLM reason dynamically
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DynamicPromptV2:
    """
    Ultra-simplified prompt system:
    1. Single system_prompt per language (no templates)
    2. Rich context building without prescriptive formatting
    3. Natural LLM reasoning based on context
    4. Full preservation of documents and knowledge resources
    """
    
    def __init__(self, language: str = "pt_BR"):
        """
        Initialize with user's preferred language
        
        Args:
            language: Language code (pt_BR, en_US, es_ES, sv_SE)
        """
        self.language = self._normalize_language(language)
        self.locales_path = Path(__file__).parent.parent / "locales" / "ai_prompts"
        self.system_prompt = self._load_system_prompt()
    
    def _normalize_language(self, language: str) -> str:
        """
        Normalize language codes to our standard format
        
        Args:
            language: Raw language code from user preferences
            
        Returns:
            Normalized language code
        """
        # Map common variations to our standard codes
        language_map = {
            'pt': 'pt_BR',
            'pt-BR': 'pt_BR',
            'pt_BR': 'pt_BR',
            'en': 'en_US',
            'en-US': 'en_US',
            'en_US': 'en_US',
            'es': 'es_ES',
            'es-ES': 'es_ES',
            'es_ES': 'es_ES',
            'sv': 'sv_SE',
            'sv-SE': 'sv_SE',
            'sv_SE': 'sv_SE'
        }
        
        normalized = language_map.get(language, language)
        
        # Validate that we have this language, fallback to pt_BR
        available_languages = ['pt_BR', 'en_US', 'es_ES', 'sv_SE']
        if normalized not in available_languages:
            logger.warning(f"Language {language} not available, falling back to pt_BR")
            return 'pt_BR'
        
        return normalized
    
    def _load_system_prompt(self) -> str:
        """
        Load system prompt from .md file first, fallback to JSON
        
        Returns:
            System prompt string
        """
        try:
            # Try .md file first (preferred format)
            md_prompt_file = self.locales_path / self.language / "system_prompt.md"
            
            if md_prompt_file.exists():
                logger.info(f"Loading system prompt from {md_prompt_file}")
                with open(md_prompt_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            
            # Fallback to JSON format
            json_prompt_file = self.locales_path / self.language / "rag_prompts.json"
            
            if not json_prompt_file.exists():
                logger.warning(f"Prompt files for {self.language} not found, falling back to pt_BR")
                
                # Try pt_BR .md first
                fallback_md = self.locales_path / "pt_BR" / "system_prompt.md"
                if fallback_md.exists():
                    with open(fallback_md, "r", encoding="utf-8") as f:
                        return f.read().strip()
                
                # Then pt_BR JSON
                json_prompt_file = self.locales_path / "pt_BR" / "rag_prompts.json"
            
            # Load from JSON
            with open(json_prompt_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
            
            system_prompt = prompts.get("system_prompt", "")
            
            if not system_prompt:
                logger.error(f"No system_prompt found in {json_prompt_file}")
                return "You are Knight ⚔️, a helpful HR assistant."
            
            return system_prompt
            
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return "You are Knight ⚔️, a helpful HR assistant."
    
    def build_context(self,
                     query: str,
                     documents: List[Dict[str, Any]] = None,
                     resources: Dict[str, List[Any]] = None,
                     chat_history: List[Dict[str, str]] = None,
                     user_context: Dict[str, Any] = None,
                     **kwargs) -> str:
        """
        Build rich context for the LLM without prescriptive formatting
        
        Args:
            query: User's current question
            documents: Retrieved documents from RAG (markdown processed)
            resources: Knowledge resources (links and downloadable documents)
            chat_history: Recent conversation history
            user_context: Additional user context (department, role, etc.)
            **kwargs: Additional context parameters
        
        Returns:
            Context string with all relevant information
        """
        context_parts = []
        
        # Start with system prompt (includes personality, examples, and instructions)
        context_parts.append(self.system_prompt)
        
        # Add conversation history if available
        if chat_history and len(chat_history) > 0:
            history_lines = []
            for msg in chat_history[-5:]:  # Last 5 messages for context
                role = "Usuário" if msg.get('role') == 'user' else "Assistente"
                content = msg.get('content', '').strip()
                if content:
                    history_lines.append(f"{role}: {content}")
            
            if history_lines:
                context_parts.append("\nConversa recente:")
                context_parts.extend(history_lines)
        
        # Add retrieved documents from company knowledge base
        if documents and len(documents) > 0:
            context_parts.append("\nInformações relevantes dos documentos da empresa:")
            
            for i, doc in enumerate(documents[:5], 1):  # Top 5 documents
                content = doc.get('content', '').strip()
                if content:
                    # Include source metadata if available
                    metadata = doc.get('metadata', {})
                    source = metadata.get('source', metadata.get('title', 'Documento'))
                    
                    context_parts.append(f"\n[{source}]")
                    context_parts.append(content[:1000])  # Limit each doc to 1000 chars
        
        # Add available knowledge resources
        if resources:
            # Useful links
            if resources.get('links') and len(resources['links']) > 0:
                context_parts.append("\nLinks úteis disponíveis:")
                for link in resources['links'][:3]:  # Top 3 links
                    title = link.get('title', '')
                    url = link.get('url', '')
                    ai_guidance = link.get('ai_guidance', '')
                    
                    if title and url:
                        context_parts.append(f"- {title}: {url}")
                        if ai_guidance:
                            context_parts.append(f"  (Orientação: {ai_guidance})")
            
            # Downloadable documents/forms
            if resources.get('documents') and len(resources['documents']) > 0:
                context_parts.append("\nFormulários/Documentos disponíveis para download:")
                for doc in resources['documents'][:2]:  # Top 2 documents
                    title = doc.get('title', '')
                    file_type = doc.get('file_type', '')
                    ai_guidance = doc.get('ai_guidance', '')
                    
                    if title:
                        doc_info = f"- {title}"
                        if file_type:
                            doc_info += f" ({file_type})"
                        context_parts.append(doc_info)
                        if ai_guidance:
                            context_parts.append(f"  (Orientação: {ai_guidance})")
        
        # Add user context if available
        if user_context:
            context_info = []
            if user_context.get('department'):
                context_info.append(f"Departamento: {user_context['department']}")
            if user_context.get('role'):
                context_info.append(f"Cargo: {user_context['role']}")
            if user_context.get('name'):
                context_info.append(f"Nome: {user_context['name']}")
            
            if context_info:
                context_parts.append("\nInformações do usuário:")
                context_parts.extend(context_info)
        
        # Add the current query
        context_parts.append(f"\nPergunta atual: {query}")
        
        # Join all parts with appropriate spacing
        full_context = "\n".join(context_parts)
        
        return full_context
    
    def format_response_with_resources(self, 
                                      response: str,
                                      resources_used: Dict[str, List[Any]] = None) -> Dict[str, Any]:
        """
        Format the final response with any resources that were suggested
        
        Args:
            response: The LLM's response text
            resources_used: Resources that the LLM decided to include
        
        Returns:
            Formatted response dictionary
        """
        formatted = {
            "response": response,
            "suggested_links": [],
            "suggested_documents": [],
            "metadata": {
                "language": self.language,
                "prompt_version": "v2-simplified"
            }
        }
        
        if resources_used:
            if resources_used.get('links'):
                formatted["suggested_links"] = [
                    {
                        "id": link.get("id"),
                        "title": link.get("title"),
                        "url": link.get("url"),
                        "description": link.get("description"),
                        "category": link.get("category")
                    }
                    for link in resources_used['links']
                ]
            
            if resources_used.get('documents'):
                formatted["suggested_documents"] = [
                    {
                        "id": doc.get("id"),
                        "title": doc.get("title"),
                        "description": doc.get("description"),
                        "file_url": doc.get("file_url"),
                        "file_type": doc.get("file_type"),
                        "category": doc.get("category")
                    }
                    for doc in resources_used['documents']
                ]
        
        return formatted
    
    def switch_language(self, language: str) -> None:
        """
        Switch to a different language dynamically
        
        Args:
            language: Language code
        """
        self.language = self._normalize_language(language)
        self.system_prompt = self._load_system_prompt()
        logger.info(f"Switched prompt language to: {self.language}")
    
    def get_system_prompt(self) -> str:
        """
        Get the current system prompt
        
        Returns:
            System prompt string
        """
        return self.system_prompt


# Singleton instance management
_instance: Optional[DynamicPromptV2] = None


def get_prompt_builder(language: str = None) -> DynamicPromptV2:
    """
    Get or create the singleton prompt builder instance
    
    Args:
        language: Optional language to switch to
    
    Returns:
        DynamicPromptV2 instance
    """
    global _instance
    
    if _instance is None:
        _instance = DynamicPromptV2(language or "pt_BR")
    elif language and language != _instance.language:
        _instance.switch_language(language)
    
    return _instance


def reset_prompt_builder():
    """Reset the singleton instance (useful for testing)"""
    global _instance
    _instance = None