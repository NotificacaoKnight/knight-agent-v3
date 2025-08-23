#!/bin/bash
echo "🧠 Alternando para DeepSeek..."
python3 switch_llm.py deepseek
echo ""
echo "✅ Pronto! DeepSeek configurado como provedor principal."
echo "💡 Reinicie o servidor para aplicar: python manage.py runserver"