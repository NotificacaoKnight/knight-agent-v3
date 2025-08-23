#!/bin/bash
echo "🤖 Alternando para OpenAI..."
python3 switch_llm.py openai
echo ""
echo "✅ Pronto! OpenAI configurado como provedor principal."
echo "💡 Reinicie o servidor para aplicar: python manage.py runserver"