"""
Configuração do Celery para Knight Agent
"""
import os
from celery import Celery
from django.conf import settings

# Definir módulo de configuração Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')

# Criar instância do Celery
app = Celery('knight_backend')

# Configurar Celery usando settings do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobrir tarefas automaticamente em todos os apps Django
app.autodiscover_tasks()

# Configurações específicas do Celery
app.conf.update(
    # Configurações de conexão
    broker_connection_retry_on_startup=True,
    
    # Configurações de tarefas
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,
    
    # Configurações de workers
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Configurações de resultados
    result_expires=3600,  # 1 hora
    
    # Configurações de retry
    task_default_retry_delay=60,  # 1 minuto
    task_max_retries=3,
    
    # Configurações de beat (agendamento)
    beat_schedule={
        'cleanup-old-files': {
            'task': 'documents.tasks.cleanup_old_processed_files',
            'schedule': 3600.0,  # A cada hora
        },
    },
)

@app.task(bind=True)
def debug_task(self):
    """Tarefa de debug para testar Celery"""
    print(f'Request: {self.request!r}')
    return "Celery está funcionando!"