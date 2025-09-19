"""
Agent Detector Service
Provides agent emojis and metadata for multi-agent system
"""
from typing import Dict, Optional


class AgentDetector:
    """Agent detection and metadata service"""

    def __init__(self):
        self.agent_emojis = {
            'knight': '⚔️',
            'wizard': '🧙‍♂️',
            'bard': '🎭'
        }

        self.agent_names = {
            'knight': 'Knight',
            'wizard': 'Wizard',
            'bard': 'Bard'
        }

        self.agent_descriptions = {
            'knight': 'Assistente técnico e profissional',
            'wizard': 'Especialista em análise e soluções',
            'bard': 'Criativo e comunicativo'
        }

    def get_agent_emoji(self, agent_type: str) -> str:
        """
        Get emoji for agent type

        Args:
            agent_type: Type of agent (knight, wizard, bard)

        Returns:
            Agent emoji or default robot emoji
        """
        return self.agent_emojis.get(agent_type.lower(), '🤖')

    def get_agent_name(self, agent_type: str) -> str:
        """
        Get display name for agent type

        Args:
            agent_type: Type of agent

        Returns:
            Agent display name
        """
        return self.agent_names.get(agent_type.lower(), 'Assistant')

    def get_agent_description(self, agent_type: str) -> str:
        """
        Get description for agent type

        Args:
            agent_type: Type of agent

        Returns:
            Agent description
        """
        return self.agent_descriptions.get(agent_type.lower(), 'Assistente IA')

    def get_agent_metadata(self, agent_type: str) -> Dict[str, str]:
        """
        Get complete metadata for agent type

        Args:
            agent_type: Type of agent

        Returns:
            Dictionary with emoji, name and description
        """
        agent = agent_type.lower()
        return {
            'type': agent,
            'emoji': self.get_agent_emoji(agent),
            'name': self.get_agent_name(agent),
            'description': self.get_agent_description(agent)
        }


# Singleton instance
agent_detector = AgentDetector()