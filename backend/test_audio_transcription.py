#!/usr/bin/env python3
"""
Script para testar a transcrição de áudio com Gemini API
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import logging

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from chat.audio_transcription import GeminiAudioTranscriptionService
from django.core.files.uploadedfile import SimpleUploadedFile

# Configurar logging para ver detalhes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gemini_api_connection():
    """Testa se a API do Gemini está funcionando"""
    try:
        import google.generativeai as genai
        from django.conf import settings
        
        api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
        if not api_key:
            print("❌ GEMINI_API_KEY não encontrada")
            return False
            
        genai.configure(api_key=api_key)
        
        # Teste simples com texto
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Diga apenas 'OK' se você está funcionando.")
        
        if response.text:
            print(f"✅ Conexão com Gemini OK: {response.text.strip()}")
            return True
        else:
            print("❌ Gemini não retornou resposta")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao conectar com Gemini: {e}")
        return False

def create_test_audio_file():
    """Cria um arquivo de áudio de teste simples (silêncio)"""
    try:
        # Criar um arquivo WebM vazio simples para teste
        # Nota: Este é apenas um placeholder - em produção usaria áudio real
        webm_header = b'\x1a\x45\xdf\xa3'  # Início básico do cabeçalho WebM
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as f:
            # Escrever dados mínimos para simular um arquivo WebM
            f.write(webm_header)
            f.write(b'\x00' * 1024)  # 1KB de dados
            return f.name
            
    except Exception as e:
        print(f"❌ Erro ao criar arquivo de teste: {e}")
        return None

def test_audio_transcription_service():
    """Testa o serviço de transcrição de áudio"""
    try:
        print("\n🎯 Testando serviço de transcrição...")
        
        service = GeminiAudioTranscriptionService()
        print("✅ Serviço inicializado com sucesso")
        
        # Criar arquivo de teste
        test_file_path = create_test_audio_file()
        if not test_file_path:
            return False
            
        try:
            # Ler arquivo como se fosse um upload
            with open(test_file_path, 'rb') as f:
                file_content = f.read()
                
            uploaded_file = SimpleUploadedFile(
                name="test_audio.webm",
                content=file_content,
                content_type="audio/webm"
            )
            
            print("🔄 Testando transcrição...")
            result = service.transcribe_audio(uploaded_file)
            
            if result['success']:
                print(f"✅ Transcrição bem-sucedida!")
                print(f"   Serviço: {result['service']}")
                print(f"   Tamanho: {result.get('length', 0)} caracteres")
                print(f"   Texto: {result['transcription'][:100]}...")
            else:
                print(f"❌ Erro na transcrição: {result['error']}")
                
            return result['success']
            
        finally:
            # Limpar arquivo de teste
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
                
    except Exception as e:
        print(f"❌ Erro no teste de transcrição: {e}")
        return False

def main():
    """Função principal do teste"""
    print("🔧 Testando Sistema de Transcrição de Áudio")
    print("=" * 50)
    
    # Teste 1: Conexão com Gemini
    print("\n1. Testando conexão com Gemini API...")
    if not test_gemini_api_connection():
        print("\n❌ Falha na conexão com Gemini. Verifique a GEMINI_API_KEY.")
        return
    
    # Teste 2: Serviço de transcrição
    print("\n2. Testando serviço de transcrição...")
    if test_audio_transcription_service():
        print("\n✅ Todos os testes passaram!")
        print("\n💡 Sugestões para uso:")
        print("   - Grave áudios de até 20MB")
        print("   - Use áudios com boa qualidade")
        print("   - Fale claramente em português")
    else:
        print("\n❌ Falha nos testes de transcrição.")
        print("\n🔧 Verifique:")
        print("   - GEMINI_API_KEY está configurada corretamente")
        print("   - Conexão com internet está funcionando")
        print("   - Não há bloqueios de firewall")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()