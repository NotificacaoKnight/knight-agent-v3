"""
Prompt Templates Naturalizados para o Sistema RAG
Prompts conversacionais em português brasileiro
"""
import random
from typing import Optional, Dict, Any


class PromptTemplates:
    """
    Gerenciador de prompts naturalizados para o Knight Agent

    Princípios:
    - Tom conversacional e prestativo
    - Persona consistente (Knight, assistente corporativo)
    - Instruções implícitas, não explícitas
    - Sem jargões técnicos
    """

    def __init__(self):
        self.persona_description = (
            "Você é o Knight, o assistente de IA da empresa. "
            "Sua função é ajudar colaboradores com informações corporativas "
            "de forma clara, direta e amigável."
        )

    def create_main_prompt(
        self,
        query: str,
        context: str = "",
        conversation_history: str = "",
        knowledge_resources: str = "",
        language: str = "pt",
        current_time: str = ""
    ) -> str:
        """
        Cria o prompt principal para geração de resposta

        Args:
            query: Pergunta do usuário
            context: Contexto extraído de documentos (já formatado naturalmente)
            conversation_history: Histórico de mensagens recentes
            knowledge_resources: Links e documentos disponíveis (já formatados)
            language: Idioma da resposta
            current_time: Horário atual do sistema (formato: "HH:MM - Período")

        Returns:
            Prompt completo para o LLM
        """
        if language == "pt":
            return self._create_portuguese_prompt(
                query, context, conversation_history, knowledge_resources, current_time
            )
        else:
            return self._create_english_prompt(
                query, context, conversation_history, knowledge_resources, current_time
            )

    def _create_portuguese_prompt(
        self,
        query: str,
        context: str,
        conversation_history: str,
        knowledge_resources: str,
        current_time: str = ""
    ) -> str:
        """Cria prompt em português brasileiro natural"""

        # Instruções de comportamento (implícitas)
        behavior_instructions = self._get_behavior_instructions_pt()

        # Montar seções do prompt
        sections = [
            f"# Sua identidade",
            self.persona_description,
            "",
            behavior_instructions
        ]

        # Adicionar informação de horário se disponível
        if current_time:
            sections.extend([
                "",
                "# Contexto temporal",
                f"Horário atual: {current_time}",
                ""
            ])

        # Adicionar contexto conversacional se disponível
        if conversation_history:
            sections.extend([
                "",
                "# Contexto da conversa",
                "Aqui está o histórico recente da nossa conversa:",
                conversation_history,
                ""
            ])

        # Adicionar informações disponíveis (contexto)
        if context:
            sections.extend([
                "",
                "# Informações disponíveis",
                "Consultei a base de conhecimento e encontrei estas informações relevantes:",
                context,
                ""
            ])

        # Adicionar recursos adicionais
        if knowledge_resources:
            sections.extend([
                "",
                "# Recursos úteis",
                knowledge_resources,
                ""
            ])

        # Adicionar a pergunta do usuário
        sections.extend([
            "",
            "# Pergunta do colaborador",
            query,
            "",
            "# Sua resposta",
            "Responda de forma natural e objetiva:"
        ])

        return "\n".join(sections)

    def _create_english_prompt(
        self,
        query: str,
        context: str,
        conversation_history: str,
        knowledge_resources: str,
        current_time: str = ""
    ) -> str:
        """Cria prompt em inglês natural"""

        persona_en = (
            "You are Knight, the company's AI assistant. "
            "Your role is to help employees with corporate information "
            "in a clear, direct, and friendly manner."
        )

        behavior_en = self._get_behavior_instructions_en()

        sections = [
            f"# Your identity",
            persona_en,
            "",
            behavior_en
        ]

        # Add time context if available
        if current_time:
            sections.extend([
                "",
                "# Time context",
                f"Current time: {current_time}",
                ""
            ])

        if conversation_history:
            sections.extend([
                "",
                "# Conversation context",
                "Here's the recent conversation history:",
                conversation_history,
                ""
            ])

        if context:
            sections.extend([
                "",
                "# Available information",
                "I consulted the knowledge base and found these relevant information:",
                context,
                ""
            ])

        if knowledge_resources:
            sections.extend([
                "",
                "# Useful resources",
                knowledge_resources,
                ""
            ])

        sections.extend([
            "",
            "# Employee's question",
            query,
            "",
            "# Your response",
            "Respond naturally and objectively:"
        ])

        return "\n".join(sections)

    def _get_behavior_instructions_pt(self) -> str:
        """Instruções de comportamento em português (naturais e implícitas)"""
        return """
## Diretrizes de Resposta

**Saudações e interações iniciais:**
- APENAS quando o usuário cumprimentar com "Olá", "Oi", "Bom dia", "Boa tarde" ou "Boa noite", responda com uma saudação natural
- Varie as saudações: "Oi!", "Olá!", "E aí!", "Boa noite!", "Como posso ajudar?", "No que posso te ajudar?", "Diga!"
- Seja casual e amigável, como um colega de trabalho prestativo
- Em todas as outras respostas, vá direto ao assunto SEM usar saudações de horário

**Formato de saída:**
- Respostas devem ter 2-5 sentenças para perguntas simples
- Para tópicos complexos, use parágrafos curtos e objetivos
- NÃO repita a pergunta do usuário
- NÃO termine com perguntas genéricas de acompanhamento ("Posso ajudar com mais alguma coisa?", "Tem mais dúvidas?")
- NÃO liste exemplos ou detalhes extras a menos que seja explicitamente solicitado

**Uso de informações da base de conhecimento:**
- Baseie suas respostas APENAS nas informações fornecidas na seção "Informações disponíveis"
- Use TODAS as informações relevantes disponíveis antes de sugerir contato com setores
- Cite fontes naturalmente quando relevante (ex: "Segundo o Manual do Colaborador...")
- Só sugira "entrar em contato com RH/setor X" como ÚLTIMA alternativa, quando realmente não houver informações suficientes

**Lacunas de informação:**
- Se as informações forem insuficientes: seja direto, admita a limitação, e sugira especificamente qual setor pode ajudar
- NUNCA invente ou assuma informações que não estejam nos documentos

**Recursos adicionais:**
- Se houver links/documentos na seção "Recursos úteis", mencione os mais relevantes naturalmente no texto
- Só mencione recursos diretamente relacionados à pergunta

**Tom e estilo:**
- Linguagem natural e descontraída, como uma conversa informal entre colegas
- Seja direto e objetivo, mas humano e acessível
- Use contrações quando natural ("tá", "pra", "você pode" ao invés de "pode-se")
- Evite formalismo corporativo excessivo ("prezado", "cordialmente", "à disposição")
- NÃO use emojis

**Esclarecimentos:**
- Se a pergunta for ambígua, faça UMA pergunta breve e direta para esclarecer
        """.strip()

    def _get_behavior_instructions_en(self) -> str:
        """Instruções de comportamento em inglês (naturais e implícitas)"""
        return """
## How you should act

- Be **objective and direct**, but always helpful
- Use **natural and conversational** language, as if talking to a colleague
- If the available information is sufficient, use it to provide a complete answer
- If important information is missing, be **honest** and suggest alternatives
- When there are useful links or documents, mention them **naturally** in the response (example: "You can check more details on the HR Portal")
- Cite sources when relevant, but naturally (example: "According to the Employee Manual...")
- If the question is ambiguous, ask for clarification in a friendly way
- Maintain a **professional but accessible** tone - not too formal nor too casual
- Prioritize **clarity**: if you need to explain something complex, break it into steps
- If you don't know something or the available information isn't enough, admit it without problem
        """.strip()

    def create_system_message(self, language: str = "pt") -> str:
        """
        Cria mensagem de sistema básica (para modelos que suportam)

        Args:
            language: Idioma

        Returns:
            Mensagem de sistema concisa
        """
        if language == "pt":
            return (
                f"{self.persona_description} "
                "Responda de forma clara, objetiva e amigável em português brasileiro. "
                "Seja honesto se não souber algo."
            )
        else:
            return (
                "You are Knight, the company's AI assistant. "
                "Respond clearly, objectively and in a friendly manner in English. "
                "Be honest if you don't know something."
            )

    def create_followup_suggestions_prompt(
        self,
        query: str,
        response: str,
        language: str = "pt"
    ) -> str:
        """
        Cria prompt para sugerir perguntas de acompanhamento

        Args:
            query: Pergunta original
            response: Resposta gerada
            language: Idioma

        Returns:
            Prompt para gerar 2-3 sugestões de perguntas
        """
        if language == "pt":
            return f"""
Com base nesta conversa:

Pergunta: {query}
Resposta: {response}

Sugira 2-3 perguntas relacionadas que o colaborador pode querer fazer em seguida.

Formato: liste apenas as perguntas, uma por linha, sem numeração.
Tom: natural e conversacional.

Perguntas sugeridas:
            """.strip()
        else:
            return f"""
Based on this conversation:

Question: {query}
Response: {response}

Suggest 2-3 related questions the employee might want to ask next.

Format: list only the questions, one per line, without numbering.
Tone: natural and conversational.

Suggested questions:
            """.strip()

    def create_query_clarification_prompt(
        self,
        query: str,
        language: str = "pt"
    ) -> str:
        """
        Cria prompt para quando a query é ambígua

        Args:
            query: Pergunta ambígua
            language: Idioma

        Returns:
            Prompt para pedir esclarecimentos
        """
        if language == "pt":
            return f"""
A pergunta "{query}" pode ter mais de uma interpretação.

Gere uma mensagem amigável pedindo esclarecimentos ao colaborador.

A mensagem deve:
- Ser breve e direta
- Listar as possíveis interpretações
- Pedir que o colaborador especifique qual delas se aplica

Mensagem:
            """.strip()
        else:
            return f"""
The question "{query}" may have more than one interpretation.

Generate a friendly message asking the employee for clarification.

The message should:
- Be brief and direct
- List the possible interpretations
- Ask the employee to specify which one applies

Message:
            """.strip()

    def get_greeting_variations(self, language: str = "pt") -> list:
        """
        Retorna variações de saudações para respostas

        Args:
            language: Idioma

        Returns:
            Lista de saudações naturais
        """
        if language == "pt":
            return [
                "Claro!",
                "Com certeza!",
                "Entendi sua pergunta.",
                "Vou te ajudar com isso.",
                "Deixa eu te explicar.",
                "Vou buscar essa informação pra você.",
                "Sobre isso, posso te dizer que",
                "Encontrei informações sobre",
                ""  # Sem saudação (direto ao ponto)
            ]
        else:
            return [
                "Sure!",
                "Of course!",
                "I understand your question.",
                "Let me help you with that.",
                "Let me explain.",
                "I'll find that information for you.",
                "About that, I can tell you that",
                "I found information about",
                ""  # No greeting (straight to the point)
            ]

    def get_closing_variations(self, language: str = "pt") -> list:
        """
        Retorna variações de fechamento para respostas

        Args:
            language: Idioma

        Returns:
            Lista de fechamentos naturais
        """
        if language == "pt":
            return [
                "Posso ajudar com mais alguma coisa?",
                "Tem mais alguma dúvida?",
                "Se precisar de mais informações, é só perguntar!",
                "Qualquer coisa, estou aqui para ajudar.",
                "Espero ter ajudado!",
                ""  # Sem fechamento
            ]
        else:
            return [
                "Can I help with anything else?",
                "Do you have any other questions?",
                "If you need more information, just ask!",
                "If you need anything, I'm here to help.",
                "I hope this helps!",
                ""  # No closing
            ]

    def format_with_personality(
        self,
        response: str,
        add_greeting: bool = False,
        add_closing: bool = False,
        language: str = "pt"
    ) -> str:
        """
        Adiciona personalidade à resposta (saudação/fechamento)

        Args:
            response: Resposta gerada
            add_greeting: Se deve adicionar saudação
            add_closing: Se deve adicionar fechamento
            language: Idioma

        Returns:
            Resposta com personalidade
        """
        parts = []

        if add_greeting:
            greeting = random.choice(self.get_greeting_variations(language))
            if greeting:
                parts.append(greeting)

        parts.append(response)

        if add_closing:
            closing = random.choice(self.get_closing_variations(language))
            if closing:
                parts.append(closing)

        # Juntar com espaçamento apropriado
        result = []
        for part in parts:
            if part.strip():
                result.append(part.strip())

        return "\n\n".join(result)


# Singleton instance
prompt_templates = PromptTemplates()
