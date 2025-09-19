"""
Serviço de transcrição de áudio usando Google Gemini
"""
import os
import tempfile
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.files.storage import default_storage
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAudioTranscriptionService:
    """Serviço para transcrever áudio usando Google Gemini"""
    
    def __init__(self):
        # Lazy initialization - configurar apenas quando necessário
        self.model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Inicializa o serviço apenas quando necessário"""
        if self._initialized:
            return
        
        # Configurar Gemini API
        api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
        if not api_key:
            logger.warning("GEMINI_API_KEY não encontrada - transcrição de áudio não estará disponível")
            return
        
        try:
            genai.configure(api_key=api_key)
            # Usar modelo Gemini 1.5 Flash para transcrição eficiente
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self._initialized = True
            logger.info("Serviço de transcrição Gemini inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar serviço de transcrição: {e}")
            self.model = None
        
    def _wait_for_file_active(self, uploaded_file, max_wait_time: int = 30) -> bool:
        """
        Aguarda o arquivo ficar no estado ACTIVE na API do Gemini
        
        Args:
            uploaded_file: Arquivo enviado para Gemini
            max_wait_time: Tempo máximo de espera em segundos
            
        Returns:
            True se o arquivo ficou ativo, False caso contrário
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                file_info = genai.get_file(uploaded_file.name)
                logger.info(f"Estado do arquivo {uploaded_file.name}: {file_info.state}")
                
                if file_info.state.name == 'ACTIVE':
                    return True
                elif file_info.state.name == 'FAILED':
                    logger.error(f"Processamento do arquivo falhou: {uploaded_file.name}")
                    return False
                    
                # Aguardar antes da próxima verificação
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Erro ao verificar estado do arquivo: {str(e)}")
                time.sleep(2)
                
        logger.error(f"Timeout aguardando arquivo ficar ativo: {uploaded_file.name}")
        return False
    
    def _get_audio_mime_type(self, file_path: str) -> str:
        """
        Determina o tipo MIME baseado na extensão do arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Tipo MIME do arquivo
        """
        extension = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.webm': 'audio/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg'
        }
        return mime_types.get(extension, 'audio/webm')
    
    def transcribe_audio(self, audio_file, language: str = 'pt-BR') -> Dict[str, Any]:
        """
        Transcrever arquivo de áudio usando Gemini
        
        Args:
            audio_file: Arquivo de áudio (Django UploadedFile ou file-like object)
            language: Código do idioma (padrão: pt-BR)
            
        Returns:
            Dict com resultado da transcrição
        """
        # Garantir que o serviço está inicializado
        self._ensure_initialized()
        
        if not self.model:
            return {
                'success': False,
                'error': 'Serviço de transcrição não está disponível',
                'text': ''
            }
        
        temp_file_path = None
        uploaded_file = None
        
        try:
            # Determinar extensão baseada no tipo de conteúdo ou padrão WebM
            file_extension = '.webm'  # Padrão para gravações do navegador
            
            # Salvar temporariamente o arquivo para upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                # Copiar conteúdo do arquivo
                audio_file.seek(0)
                temp_file.write(audio_file.read())
                temp_file_path = temp_file.name
            
            # Verificar tamanho do arquivo (limite de 20MB para Gemini)
            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:  # 20MB
                raise ValueError(f"Arquivo muito grande: {file_size / (1024*1024):.1f}MB. Limite: 20MB")
            
            logger.info(f"Fazendo upload do arquivo de áudio: {temp_file_path} ({file_size / 1024:.1f}KB)")
            
            # Upload do arquivo para Gemini com MIME type correto
            mime_type = self._get_audio_mime_type(temp_file_path)
            uploaded_file = genai.upload_file(temp_file_path, mime_type=mime_type)
            
            logger.info(f"Arquivo enviado com sucesso. URI: {uploaded_file.uri}")
            
            # CRUCIAL: Aguardar o arquivo ficar no estado ACTIVE
            if not self._wait_for_file_active(uploaded_file, max_wait_time=45):
                raise ValueError("Timeout: arquivo não ficou ativo na API do Gemini")
            
            logger.info(f"Arquivo está ATIVO. Iniciando transcrição...")
            
            # Prompt otimizado para transcrição em português
            prompt = f"""
Transcreva este arquivo de áudio em português brasileiro com alta precisão.

Instruções:
- Mantenha a pontuação adequada
- Use formatação natural para o português brasileiro
- Identifique diferentes oradores se houver múltiplos
- Preserve o contexto e significado original
- Remova hesitações e repetições desnecessárias (mas mantenha o sentido)

Por favor, retorne apenas a transcrição limpa e formatada do áudio:
"""
            
            # Gerar conteúdo com o arquivo de áudio
            response = self.model.generate_content([prompt, uploaded_file])
            
            if not response.text:
                raise ValueError("Gemini não retornou transcrição")
            
            transcription = response.text.strip()
            
            logger.info(f"Transcrição bem-sucedida: {len(transcription)} caracteres")
            
            return {
                'success': True,
                'transcription': transcription,
                'language': language,
                'service': 'gemini-1.5-flash',
                'length': len(transcription),
                'file_size_kb': file_size / 1024
            }
                
        except Exception as e:
            logger.error(f"Erro na transcrição com Gemini: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transcription': '',
                'language': language,
                'service': 'gemini-1.5-flash'
            }
            
        finally:
            # Limpeza garantida dos recursos
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"Arquivo temporário removido: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
                
            try:
                if uploaded_file:
                    genai.delete_file(uploaded_file.name)
                    logger.debug(f"Arquivo remoto removido: {uploaded_file.name}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo remoto: {e}")
    
    def transcribe_audio_with_speakers(self, audio_file, language: str = 'pt-BR') -> Dict[str, Any]:
        """
        Transcrever áudio com identificação de oradores
        
        Args:
            audio_file: Arquivo de áudio
            language: Código do idioma
            
        Returns:
            Dict com transcrição e identificação de oradores
        """
        temp_file_path = None
        uploaded_file = None
        
        try:
            # Determinar extensão baseada no tipo de conteúdo ou padrão WebM
            file_extension = '.webm'  # Padrão para gravações do navegador
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                audio_file.seek(0)
                temp_file.write(audio_file.read())
                temp_file_path = temp_file.name
            
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(temp_file_path)
            if file_size > 20 * 1024 * 1024:  # 20MB
                raise ValueError(f"Arquivo muito grande: {file_size / (1024*1024):.1f}MB. Limite: 20MB")
                
            logger.info(f"Fazendo upload do arquivo de áudio para diarização: {temp_file_path} ({file_size / 1024:.1f}KB)")
            
            # Upload com MIME type correto
            mime_type = self._get_audio_mime_type(temp_file_path)
            uploaded_file = genai.upload_file(temp_file_path, mime_type=mime_type)
            
            # Aguardar arquivo ficar ativo
            if not self._wait_for_file_active(uploaded_file, max_wait_time=45):
                raise ValueError("Timeout: arquivo não ficou ativo na API do Gemini")
                
            logger.info(f"Arquivo está ATIVO. Iniciando transcrição com identificação de oradores...")
            
            # Prompt especializado para diarização (identificação de oradores)
            prompt = f"""
Transcreva este arquivo de áudio em português brasileiro e identifique diferentes oradores se houver.

Formato desejado:
- Se houver apenas um orador: retorne apenas a transcrição
- Se houver múltiplos oradores: use o formato "Orador X: [fala]"

Instruções:
- Use formatação clara para português brasileiro
- Mantenha pontuação adequada
- Identifique mudanças de orador
- Preserve o contexto e significado
- Remova hesitações desnecessárias

Transcrição:
"""
            
            response = self.model.generate_content([prompt, uploaded_file])
            
            if not response.text:
                raise ValueError("Gemini não retornou transcrição com oradores")
            
            transcription = response.text.strip()
            
            # Detectar se há múltiplos oradores
            has_speakers = 'Orador' in transcription or 'orador' in transcription
            
            logger.info(f"Transcrição com oradores bem-sucedida: {len(transcription)} caracteres")
            
            return {
                'success': True,
                'transcription': transcription,
                'has_speakers': has_speakers,
                'language': language,
                'service': 'gemini-1.5-flash',
                'length': len(transcription),
                'file_size_kb': file_size / 1024
            }
                
        except Exception as e:
            logger.error(f"Erro na transcrição com oradores: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transcription': '',
                'has_speakers': False,
                'language': language,
                'service': 'gemini-1.5-flash'
            }
            
        finally:
            # Limpeza garantida dos recursos
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"Arquivo temporário removido: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
                
            try:
                if uploaded_file:
                    genai.delete_file(uploaded_file.name)
                    logger.debug(f"Arquivo remoto removido: {uploaded_file.name}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo remoto: {e}")
    
    def get_audio_duration_estimate(self, audio_file) -> float:
        """
        Estimar duração do áudio (placeholder - em produção usar biblioteca específica)
        
        Args:
            audio_file: Arquivo de áudio
            
        Returns:
            Duração estimada em segundos
        """
        try:
            # Placeholder - estimativa baseada no tamanho do arquivo
            # Em produção, usar bibliotecas como mutagen, pydub, etc.
            file_size = len(audio_file.read())
            audio_file.seek(0)  # Reset para início
            
            # Estimativa rough: ~1KB por segundo para áudio WebM comprimido
            estimated_duration = file_size / 1024
            
            return max(1.0, estimated_duration)  # Mínimo 1 segundo
            
        except Exception:
            return 5.0  # Fallback para 5 segundos