import os
import tempfile
import base64
from typing import Dict, Any, Optional
from django.conf import settings
from agno.agent import Agent


class AudioTranscriptionService:
    """Serviço para transcrição de áudio usando Agno com Gemini"""
    
    def __init__(self):
        self.gemini_api_key = getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        self.agent = None
        
        if self.gemini_api_key:
            try:
                from agno.models.google import Gemini
                
                model = Gemini(
                    id="gemini-1.5-flash",
                    api_key=self.gemini_api_key
                )
                
                self.agent = Agent(
                    name="Audio Transcriber",
                    role="Transcritor de áudio",
                    description="Especialista em transcrever áudio para texto em português brasileiro",
                    instructions=[
                        "Você é um especialista em transcrição de áudio",
                        "Transcreva o áudio fornecido para texto em português brasileiro",
                        "Mantenha a pontuação adequada e estrutura natural da fala",
                        "Se houver termos técnicos ou corporativos, preserve-os",
                        "Responda APENAS com o texto transcrito, sem comentários adicionais"
                    ],
                    model=model,
                    markdown=False
                )
            except Exception as e:
                print(f"Erro ao configurar Agno para transcrição: {e}")
                self.agent = None
        else:
            print("API key do Gemini não configurada para transcrição de áudio")
    
    def is_available(self) -> bool:
        """Verifica se o serviço de transcrição está disponível"""
        return bool(self.agent and self.gemini_api_key)
    
    def transcribe_audio(
        self, 
        audio_file_content: bytes, 
        filename: str = "audio.webm",
        language: str = "pt"
    ) -> Dict[str, Any]:
        """
        Transcreve áudio para texto usando Agno com Gemini
        
        Args:
            audio_file_content: Conteúdo do arquivo de áudio em bytes
            filename: Nome do arquivo (usado para determinar formato)
            language: Idioma para transcrição (padrão: português)
        
        Returns:
            Dict com resultado da transcrição
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'Serviço de transcrição não configurado. Verifique a API key do Gemini.',
                'transcription': ''
            }
        
        try:
            # Validar tamanho do arquivo (max 20MB)
            max_size = 20 * 1024 * 1024  # 20MB
            if len(audio_file_content) > max_size:
                return {
                    'success': False,
                    'error': f'Arquivo muito grande ({len(audio_file_content) / 1024 / 1024:.1f}MB). Máximo permitido: 20MB',
                    'transcription': ''
                }
            
            # Validar se tem conteúdo mínimo - mas ser mais tolerante
            min_size = 1000  # ~1KB mínimo (header básico)
            if len(audio_file_content) < min_size:
                return {
                    'success': False,
                    'error': 'Áudio muito curto ou vazio. Grave por pelo menos 1 segundo.',
                    'transcription': ''
                }
            
            # Log dos primeiros bytes para debug
            header = audio_file_content[:16]
            print(f"Header do arquivo: {header}")
            print(f"Header hex: {header.hex()}")
            
            # Salvar temporariamente o arquivo de áudio
            file_extension = filename.split(".")[-1] if "." in filename else "webm"
            with tempfile.NamedTemporaryFile(suffix=f'.{file_extension}', delete=False) as temp_file:
                temp_file.write(audio_file_content)
                temp_file_path = temp_file.name
            
            try:
                # Determinar tipo MIME
                mime_type = self._get_mime_type(filename)
                
                print(f"Processando áudio: {filename}, Tamanho: {len(audio_file_content)} bytes, MIME: {mime_type}")
                
                # Criar o prompt de transcrição
                prompt = "Por favor, transcreva este áudio para texto em português brasileiro. Responda APENAS com o texto transcrito."
                
                # Usar o modelo do Agno diretamente para transcrição de áudio
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.gemini_api_key)
                    print("✅ Google Generative AI configurado com sucesso")
                except Exception as e:
                    print(f"❌ Erro ao importar/configurar Google Generative AI: {e}")
                    raise
                
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                # Upload do arquivo de áudio com retry para diferentes MIME types
                audio_file = None
                mime_types_to_try = [mime_type, 'audio/webm', 'audio/wav', 'audio/mp3', 'audio/ogg']
                
                for attempt_mime in mime_types_to_try:
                    try:
                        print(f"Tentando upload com MIME type: {attempt_mime}")
                        audio_file = genai.upload_file(temp_file_path, mime_type=attempt_mime)
                        print(f"✅ Upload bem-sucedido com MIME type: {attempt_mime}")
                        break
                    except Exception as e:
                        print(f"❌ Erro com MIME type {attempt_mime}: {e}")
                        continue
                
                if not audio_file:
                    raise Exception("Não foi possível fazer upload do arquivo com nenhum tipo MIME suportado")
                
                # Aguardar o processamento do arquivo
                import time
                time.sleep(1)
                
                # Gerar resposta
                response = model.generate_content([prompt, audio_file])
                
                # Extrair transcription
                transcription = response.text if hasattr(response, 'text') else str(response)
                
                print(f"Resposta do Gemini: '{transcription}'")
                
                # Verificar se é silêncio ou resposta vazia
                if not transcription or transcription.strip() == "":
                    return {
                        'success': False,
                        'error': 'Não foi possível transcrever o áudio',
                        'transcription': ''
                    }
                
                # Lista expandida de padrões que indicam áudio vazio/alucinação
                noise_patterns = [
                    # Sons repetitivos
                    'pipipi', 'popopo', 'papapa', 'tatata', 'lalala', 'bababa',
                    'dadada', 'nanana', 'mamama', 'kakaka', 'gagaga', 'rarara',
                    'sasasa', 'vavava', 'fafafa', 'zazaza', 'xaxaxa', 'cacaca',
                    
                    # Onomatopeias comuns
                    'blablabla', 'shshsh', 'sssss', 'fffff', 'mmmmm', 'zzzzz',
                    'brrrrr', 'grrrrr', 'pfffff', 'tssss', 'psssss', 'shhhh',
                    
                    # Vogais repetidas
                    'aaaaa', 'eeeee', 'iiiii', 'ooooo', 'uuuuu',
                    'aaah', 'eeeh', 'iiih', 'oooh', 'uuuh',
                    'aaa', 'eee', 'iii', 'ooo', 'uuu',
                    
                    # Risadas
                    'hahaha', 'hehehe', 'hihihi', 'hohoho', 'huhuhu',
                    'kkkk', 'rsrsrs', 'haha', 'hehe', 'hihi',
                    
                    # Interjeições
                    'ah', 'eh', 'ih', 'oh', 'uh', 'ai', 'oi', 'ui',
                    'hm', 'hmm', 'hmmm', 'uhm', 'ahm', 'ehm',
                    
                    # Outros padrões comuns
                    '...', '..', '.', '!', '?', '-', '--',
                    'bip', 'bop', 'tic', 'tac', 'toc', 'pic', 'pac',
                    'piu', 'pow', 'puf', 'plim', 'plom', 'blim', 'blom'
                ]
                
                # Limpar e normalizar texto
                cleaned_text = transcription.strip().lower()
                # Remover pontuação e espaços
                for char in '.,:;!?-–—\'\"()[]{}':
                    cleaned_text = cleaned_text.replace(char, '')
                cleaned_text = cleaned_text.strip()
                
                # Verificar padrões de ruído (busca mais flexível)
                is_noise = False
                for pattern in noise_patterns:
                    if pattern in cleaned_text or cleaned_text == pattern:
                        is_noise = True
                        break
                
                # Verificações adicionais
                is_too_short = len(cleaned_text) < 4  # Menos de 4 caracteres
                is_repetitive = len(set(cleaned_text.replace(' ', ''))) <= 3  # 3 ou menos caracteres únicos
                
                # Verificar se é apenas números ou caracteres especiais
                is_only_numbers = cleaned_text.replace(' ', '').isdigit()
                
                # Verificar se parece uma palavra real em português (heurística simples)
                common_short_words = ['sim', 'não', 'nao', 'oi', 'olá', 'ola', 'bom', 'boa', 'dia', 'tarde', 'noite']
                is_valid_short_word = cleaned_text in common_short_words
                
                # Log para debug
                print(f"Análise da transcrição:")
                print(f"  - Original: '{transcription}'")
                print(f"  - Limpo: '{cleaned_text}'")
                print(f"  - É ruído: {is_noise}")
                print(f"  - Muito curto: {is_too_short}")
                print(f"  - Repetitivo: {is_repetitive}")
                print(f"  - Só números: {is_only_numbers}")
                print(f"  - Palavra válida: {is_valid_short_word}")
                
                # Aplicar todas as verificações
                if (is_noise or is_too_short or is_repetitive or is_only_numbers) and not is_valid_short_word:
                    print("  → Detectado como ÁUDIO VAZIO")
                    # Marcar como áudio vazio mas retornar sucesso
                    return {
                        'success': True,
                        'transcription': '[ÁUDIO_VAZIO]',
                        'language': language,
                        'model': 'gemini-1.5-flash',
                        'is_empty': True
                    }
                
                return {
                    'success': True,
                    'transcription': transcription.strip(),
                    'language': language,
                    'model': 'gemini-1.5-flash'
                }
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Erro detalhado na transcrição: {e}")
            print(f"Stack trace: {error_details}")
            
            # Log mais detalhado baseado no tipo de erro
            if "400 Request contains an invalid argument" in str(e):
                error_msg = "Formato de áudio não suportado ou arquivo corrompido"
            elif "403" in str(e):
                error_msg = "Erro de autenticação com API do Gemini"
            elif "429" in str(e):
                error_msg = "Limite de requisições excedido. Tente novamente em alguns minutos"
            elif "File too large" in str(e):
                error_msg = "Arquivo de áudio muito grande. Limite máximo: 20MB"
            else:
                error_msg = f"Erro na transcrição: {str(e)}"
            
            return {
                'success': False,
                'error': error_msg,
                'transcription': ''
            }
    
    def _extract_response_text(self, response) -> str:
        """Extrai texto da resposta do Agno"""
        if hasattr(response, 'content'):
            if isinstance(response.content, list) and len(response.content) > 0:
                return response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            else:
                return str(response.content)
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    
    def _get_mime_type(self, filename: str) -> str:
        """Determina tipo MIME baseado no nome do arquivo"""
        extension = filename.split('.')[-1].lower() if '.' in filename else 'webm'
        
        mime_types = {
            'mp3': 'audio/mpeg',
            'mp4': 'audio/mp4',
            'wav': 'audio/wav',
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac',
            'm4a': 'audio/m4a',
            'aac': 'audio/aac'
        }
        
        # Sempre usar audio/webm como padrão para arquivos do navegador
        detected_type = mime_types.get(extension, 'audio/webm')
        print(f"Arquivo: {filename}, Extensão: {extension}, MIME detectado: {detected_type}")
        return detected_type
    
    def get_supported_formats(self) -> list:
        """Retorna formatos de áudio suportados pelo Gemini"""
        return [
            'mp3', 'mp4', 'wav', 'webm', 'ogg', 'flac', 'm4a', 'aac'
        ]


# Instância global do serviço
transcription_service = AudioTranscriptionService()