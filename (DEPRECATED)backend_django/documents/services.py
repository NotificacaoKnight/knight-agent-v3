import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
from django.conf import settings
from django.core.files.storage import default_storage
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import ConversionResult
import pypdf as PyPDF2
from docx import Document as DocxDocument
import openpyxl
from pptx import Presentation

# Configure logging for document processing
logger = logging.getLogger('documents.processor')

class DocumentProcessor:
    """Serviço para processamento de documentos usando Docling com tratamento robusto de erros"""
    
    def __init__(self):
        self.converter = DocumentConverter()
        
        # Configurações otimizadas para português - PDF
        self.pdf_options = PdfPipelineOptions()
        self.pdf_options.do_ocr = True
        self.pdf_options.ocr_options.lang = ["por", "eng"]  # Português e inglês
        
        # Para documentos Word, usar configurações padrão do converter
        # DocxPipelineOptions não existe na versão atual do Docling
        
    def process_document(self, document_path: str, output_dir: str) -> Dict:
        """Processa documento e converte para markdown"""
        try:
            # Determinar formato do arquivo
            file_extension = Path(document_path).suffix.lower()
            
            if file_extension == '.pdf':
                return self._process_pdf(document_path, output_dir)
            elif file_extension in ['.docx', '.doc']:
                return self._process_word(document_path, output_dir)
            elif file_extension in ['.xlsx', '.xls']:
                return self._process_excel(document_path, output_dir)
            elif file_extension in ['.pptx', '.ppt']:
                return self._process_powerpoint(document_path, output_dir)
            elif file_extension in ['.txt', '.md']:
                return self._process_text(document_path, output_dir)
            else:
                raise ValueError(f"Formato de arquivo não suportado: {file_extension}")
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'markdown_content': '',
                'metadata': {}
            }
    
    def _process_pdf(self, document_path: str, output_dir: str) -> Dict:
        """Processa PDF usando Docling com tratamento robusto de erros"""
        logger.info(f"Iniciando processamento de PDF: {document_path}")
        
        try:
            # Usar Docling para conversão
            logger.info("Tentando conversão com Docling...")
            result: ConversionResult = self.converter.convert(
                document_path,
                pipeline_options=self.pdf_options
            )
            
            # Verificar se o resultado é válido
            if not result or not hasattr(result, 'document'):
                logger.warning("Resultado inválido do Docling para PDF")
                return self._process_pdf_fallback(document_path, output_dir)
            
            # Extrair markdown
            try:
                markdown_content = result.document.export_to_markdown()
                logger.info(f"Markdown extraído com sucesso via Docling: {len(markdown_content)} caracteres")
            except Exception as export_error:
                logger.error(f"Erro ao exportar markdown do Docling para PDF: {export_error}")
                return self._process_pdf_fallback(document_path, output_dir)
            
            # Verificar se o conteúdo é válido
            if not markdown_content or not markdown_content.strip():
                logger.warning("Conteúdo markdown vazio do Docling para PDF, usando fallback")
                return self._process_pdf_fallback(document_path, output_dir)
            
            # Extrair metadados de forma segura
            metadata = self._extract_docling_metadata(result, 'docling')
            metadata['text_length'] = len(markdown_content)
            
            # Salvar markdown processado
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"PDF processado com sucesso via Docling: {output_path}")
            return {
                'success': True,
                'markdown_content': markdown_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except IndexError as ie:
            logger.error(f"Erro de índice no Docling para PDF (list index out of range): {ie}")
            return self._process_pdf_fallback(document_path, output_dir)
        except Exception as e:
            logger.error(f"Erro geral no processamento Docling para PDF: {e}")
            # Fallback para PyPDF2 se Docling falhar
            return self._process_pdf_fallback(document_path, output_dir)
    
    def _process_pdf_fallback(self, document_path: str, output_dir: str) -> Dict:
        """Fallback para processamento de PDF com PyPDF2"""
        logger.info(f"Usando fallback PyPDF2 para PDF: {document_path}")
        
        try:
            with open(document_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            text_content.append(f"## Página {page_num + 1}\n\n{text}\n")
                    except Exception as page_error:
                        logger.warning(f"Erro ao extrair texto da página {page_num + 1}: {page_error}")
                        continue
                
                markdown_content = "\n".join(text_content)
                
                if not markdown_content.strip():
                    logger.error("Nenhum conteúdo extraído do PDF via PyPDF2")
                    return {
                        'success': False,
                        'error': 'Nenhum conteúdo extraído do PDF',
                        'markdown_content': '',
                        'metadata': {}
                    }
                
                metadata = {
                    'pages': len(pdf_reader.pages),
                    'title': pdf_reader.metadata.get('/Title', '') if pdf_reader.metadata else '',
                    'author': pdf_reader.metadata.get('/Author', '') if pdf_reader.metadata else '',
                    'text_length': len(markdown_content),
                    'processing_method': 'pypdf2_fallback'
                }
                
                output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logger.info(f"PDF processado com sucesso via PyPDF2 fallback: {output_path}")
                return {
                    'success': True,
                    'markdown_content': markdown_content,
                    'output_path': output_path,
                    'metadata': metadata
                }
                
        except Exception as e:
            logger.error(f"Erro no fallback PyPDF2: {e}")
            return {
                'success': False,
                'error': f"Falha no fallback PyPDF2: {str(e)}",
                'markdown_content': '',
                'metadata': {}
            }
    
    def _process_word(self, document_path: str, output_dir: str) -> Dict:
        """Processa documentos Word com tratamento robusto de erros"""
        logger.info(f"Iniciando processamento de documento Word: {document_path}")
        
        # Primeiro, tentar validar o arquivo
        try:
            if not self._validate_docx_file(document_path):
                logger.warning(f"Arquivo DOCX inválido ou corrompido: {document_path}")
                return self._process_word_fallback(document_path, output_dir, error="Arquivo DOCX inválido")
        except Exception as e:
            logger.error(f"Erro na validação do arquivo DOCX: {e}")
            return self._process_word_fallback(document_path, output_dir, error=str(e))
        
        # Tentar Docling com tratamento robusto de IndexError
        try:
            logger.info("Tentando conversão com Docling...")
            result: ConversionResult = self.converter.convert(document_path)
            
            # Verificar se o resultado é válido
            if not result or not hasattr(result, 'document'):
                logger.warning("Resultado inválido do Docling")
                return self._process_word_fallback(document_path, output_dir, error="Resultado inválido do Docling")
            
            # Tentar extrair markdown
            markdown_content = ""
            try:
                markdown_content = result.document.export_to_markdown()
                logger.info(f"Markdown extraído com sucesso via Docling: {len(markdown_content)} caracteres")
            except IndexError as index_error:
                logger.error(f"IndexError do Docling (list index out of range): {index_error}")
                return self._process_word_fallback(document_path, output_dir, error=f"IndexError do Docling: {index_error}")
            except Exception as export_error:
                logger.error(f"Erro ao exportar markdown do Docling: {export_error}")
                return self._process_word_fallback(document_path, output_dir, error=f"Erro na exportação: {export_error}")
            
            # Verificar se o conteúdo é válido
            if not markdown_content or not markdown_content.strip():
                logger.warning("Conteúdo markdown vazio do Docling, usando fallback")
                return self._process_word_fallback(document_path, output_dir, error="Conteúdo vazio")
            
            # Extrair metadados de forma segura
            metadata = self._extract_docling_metadata(result, 'docling')
            metadata['text_length'] = len(markdown_content)
            
            # Salvar resultado
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Documento Word processado com sucesso via Docling: {output_path}")
            return {
                'success': True,
                'markdown_content': markdown_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except IndexError as ie:
            logger.error(f"Erro de índice no Docling (list index out of range): {ie}")
            return self._process_word_fallback(document_path, output_dir, error=f"Erro de índice: {ie}")
        except Exception as e:
            logger.error(f"Erro geral no processamento Docling: {e}")
            return self._process_word_fallback(document_path, output_dir, error=str(e))
    
    def _validate_docx_file(self, document_path: str) -> bool:
        """Valida se o arquivo DOCX pode ser processado"""
        try:
            # Tentar abrir com python-docx para validação básica
            doc = DocxDocument(document_path)
            # Verificar se tem pelo menos algum conteúdo
            has_content = any(p.text.strip() for p in doc.paragraphs[:10])  # Verificar primeiros 10 parágrafos
            return has_content
        except Exception as e:
            logger.error(f"Erro na validação do arquivo DOCX: {e}")
            return False
    
    def _process_word_fallback(self, document_path: str, output_dir: str, error: str = "") -> Dict:
        """Processamento de fallback para documentos Word usando python-docx"""
        logger.info(f"Usando fallback python-docx para: {document_path} (Razão: {error})")
        
        try:
            doc = DocxDocument(document_path)
            paragraphs = []
            
            # Processar parágrafos de forma mais robusta
            for i, paragraph in enumerate(doc.paragraphs):
                try:
                    if paragraph.text and paragraph.text.strip():
                        # Detectar estilos de cabeçalho de forma segura
                        style_name = getattr(paragraph.style, 'name', '') if paragraph.style else ''
                        
                        if style_name.startswith('Heading'):
                            level_str = style_name.replace('Heading ', '').strip()
                            if level_str.isdigit() and int(level_str) <= 6:
                                level = int(level_str)
                                markdown_text = f"{'#' * level} {paragraph.text.strip()}"
                            else:
                                markdown_text = f"## {paragraph.text.strip()}"
                        else:
                            markdown_text = paragraph.text.strip()
                        
                        if markdown_text:  # Só adicionar se não estiver vazio
                            paragraphs.append(markdown_text)
                            
                except Exception as para_error:
                    logger.warning(f"Erro ao processar parágrafo {i}: {para_error}")
                    continue
            
            # Processar tabelas também
            try:
                for table in doc.tables:
                    table_md = self._convert_docx_table_to_markdown(table)
                    if table_md:
                        paragraphs.append(table_md)
            except Exception as table_error:
                logger.warning(f"Erro ao processar tabelas: {table_error}")
            
            markdown_content = "\n\n".join(paragraphs) if paragraphs else ""
            
            if not markdown_content.strip():
                logger.error("Nenhum conteúdo extraído do documento Word")
                return {
                    'success': False,
                    'error': 'Nenhum conteúdo encontrado no documento',
                    'markdown_content': '',
                    'metadata': {}
                }
            
            metadata = {
                'paragraphs': len(doc.paragraphs),
                'tables': len(doc.tables),
                'text_length': len(markdown_content),
                'processing_method': 'python-docx-fallback',
                'fallback_reason': error
            }
            
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Documento Word processado com sucesso via fallback: {output_path}")
            return {
                'success': True,
                'markdown_content': markdown_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Erro no fallback python-docx: {e}")
            return {
                'success': False,
                'error': f"Falha no fallback: {str(e)}",
                'markdown_content': '',
                'metadata': {}
            }
    
    def _convert_docx_table_to_markdown(self, table) -> str:
        """Converte tabela do DOCX para markdown"""
        try:
            if not table.rows:
                return ""
            
            markdown_rows = []
            
            for i, row in enumerate(table.rows):
                cells = []
                for cell in row.cells:
                    cell_text = cell.text.strip().replace('\n', ' ').replace('|', '\\|')
                    cells.append(cell_text)
                
                if cells and any(cell for cell in cells):  # Só processar se tem conteúdo
                    row_md = "| " + " | ".join(cells) + " |"
                    markdown_rows.append(row_md)
                    
                    # Adicionar separador após primeira linha (cabeçalho)
                    if i == 0 and len(cells) > 0:
                        separator = "|" + "|".join([" --- " for _ in cells]) + "|"
                        markdown_rows.append(separator)
            
            return "\n".join(markdown_rows) if markdown_rows else ""
            
        except Exception as e:
            logger.warning(f"Erro ao converter tabela para markdown: {e}")
            return ""
    
    def _extract_docling_metadata(self, result: ConversionResult, method: str) -> Dict:
        """Extrai metadados de forma segura do resultado do Docling"""
        metadata = {
            'processing_method': method
        }
        
        try:
            if hasattr(result, 'document') and result.document:
                doc = result.document
                
                # Extrair metadados básicos de forma segura
                metadata.update({
                    'pages': len(doc.pages) if hasattr(doc, 'pages') and doc.pages else 0,
                    'title': getattr(doc, 'title', '') or '',
                    'author': getattr(doc, 'author', '') or '',
                    'creation_date': str(getattr(doc, 'creation_date', '')) or '',
                })
                
                # Contar elementos estruturais se disponível
                if hasattr(doc, 'pages') and doc.pages:
                    try:
                        total_elements = sum(len(page.elements) for page in doc.pages if hasattr(page, 'elements'))
                        metadata['total_elements'] = total_elements
                    except Exception:
                        pass
        
        except Exception as e:
            logger.warning(f"Erro ao extrair metadados do Docling: {e}")
        
        return metadata
    
    def _process_excel(self, document_path: str, output_dir: str) -> Dict:
        """Processa planilhas Excel"""
        try:
            workbook = openpyxl.load_workbook(document_path, read_only=True)
            markdown_content = []
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                markdown_content.append(f"# {sheet_name}\n")
                
                # Converter para tabela markdown
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    if any(cell for cell in row if cell is not None):
                        row_data = [str(cell) if cell is not None else '' for cell in row]
                        rows.append(row_data)
                
                if rows:
                    # Cabeçalho da tabela
                    header = "| " + " | ".join(rows[0]) + " |"
                    separator = "|" + "|".join([" --- " for _ in rows[0]]) + "|"
                    markdown_content.append(header)
                    markdown_content.append(separator)
                    
                    # Dados da tabela
                    for row in rows[1:]:
                        row_md = "| " + " | ".join(row) + " |"
                        markdown_content.append(row_md)
                
                markdown_content.append("\n")
            
            final_content = "\n".join(markdown_content)
            
            metadata = {
                'sheets': len(workbook.sheetnames),
                'sheet_names': workbook.sheetnames,
                'text_length': len(final_content),
                'processing_method': 'openpyxl'
            }
            
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            return {
                'success': True,
                'markdown_content': final_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'markdown_content': '',
                'metadata': {}
            }
    
    def _process_powerpoint(self, document_path: str, output_dir: str) -> Dict:
        """Processa apresentações PowerPoint"""
        try:
            presentation = Presentation(document_path)
            markdown_content = []
            
            for slide_num, slide in enumerate(presentation.slides, 1):
                markdown_content.append(f"# Slide {slide_num}\n")
                
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        # Detectar títulos (normalmente o primeiro texto grande)
                        if shape.text.strip() and len(shape.text.strip()) < 100:
                            markdown_content.append(f"## {shape.text}\n")
                        else:
                            markdown_content.append(f"{shape.text}\n")
                
                markdown_content.append("\n---\n")
            
            final_content = "\n".join(markdown_content)
            
            metadata = {
                'slides': len(presentation.slides),
                'text_length': len(final_content),
                'processing_method': 'python-pptx'
            }
            
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            return {
                'success': True,
                'markdown_content': final_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'markdown_content': '',
                'metadata': {}
            }
    
    def _process_text(self, document_path: str, output_dir: str) -> Dict:
        """Processa arquivos de texto simples"""
        try:
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Se já for markdown, manter como está
            if document_path.endswith('.md'):
                markdown_content = content
            else:
                # Converter texto simples para markdown básico
                lines = content.split('\n')
                markdown_lines = []
                
                for line in lines:
                    if line.strip():
                        markdown_lines.append(line)
                    else:
                        markdown_lines.append('')
                
                markdown_content = '\n'.join(markdown_lines)
            
            metadata = {
                'lines': len(content.split('\n')),
                'text_length': len(markdown_content),
                'processing_method': 'text_reader'
            }
            
            output_path = os.path.join(output_dir, f"{Path(document_path).stem}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return {
                'success': True,
                'markdown_content': markdown_content,
                'output_path': output_path,
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'markdown_content': '',
                'metadata': {}
            }

def calculate_file_checksum(file_path: str) -> str:
    """Calcula checksum MD5 do arquivo"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()