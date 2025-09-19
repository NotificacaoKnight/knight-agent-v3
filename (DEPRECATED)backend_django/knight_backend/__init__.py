"""
Inicialização do projeto Knight Backend
Configurações essenciais que devem ser definidas antes de qualquer import
"""
import os

# Forçar modo offline para HuggingFace antes de qualquer carregamento
# Isso evita tentativas de download e resolve erros HTTP 429
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1' 
os.environ['HF_DATASETS_OFFLINE'] = '1'

# Configurações adicionais para PyTorch em modo offline
os.environ['TORCH_HOME'] = os.path.join(os.path.expanduser('~'), '.cache', 'torch')

# Configuração do Celery para Django
from .celery import app as celery_app

__all__ = ('celery_app',)