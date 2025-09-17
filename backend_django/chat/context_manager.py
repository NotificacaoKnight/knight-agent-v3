from typing import List, Dict, Any
from .models import ChatSession, ChatMessage


class ChatContextManager:
    """Gerenciador de contexto conversacional simples com sliding window"""
    
    def should_include_history(self, user_message: str, session: ChatSession) -> bool:
        """
        Determina se deve incluir histórico da conversa.
        Sempre inclui se há mensagens suficientes na sessão.
        """
        try:
            # Incluir histórico se há pelo menos 2 mensagens na sessão
            message_count = session.messages.count()
            return message_count >= 2
            
        except Exception:
            return False
    
    def get_relevant_context(self, session: ChatSession, max_messages: int = 6) -> List[Dict[str, Any]]:
        """
        Obtém contexto conversacional usando sliding window.
        Retorna as últimas N mensagens no formato esperado pelo RAG.
        """
        try:
            # Buscar últimas N mensagens (excluindo handoffs)
            recent_messages = session.messages.filter(
                is_handoff=False
            ).order_by('-created_at')[:max_messages]
            
            # Converter para formato esperado pelo sistema RAG
            context = []
            for message in reversed(recent_messages):  # Ordem cronológica
                context.append({
                    'role': 'user' if message.message_type == 'user' else 'assistant',
                    'content': message.content
                })
            
            return context
            
        except Exception:
            return []