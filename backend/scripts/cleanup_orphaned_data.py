"""
Script para limpar dados órfãos do banco de dados

Execução: python scripts/cleanup_orphaned_data.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import get_async_db


async def cleanup_orphaned_data():
    """Remove dados órfãos e sessões antigas vazias"""
    print("🧹 Iniciando limpeza de dados...")

    async for db in get_async_db():
        try:
            # 1. Sessões vazias criadas há mais de 30 dias
            result = await db.execute(text("""
                DELETE FROM chat_sessions
                WHERE message_count = 0
                AND created_at < NOW() - INTERVAL '30 days'
                RETURNING id
            """))
            deleted_sessions = result.rowcount
            print(f"✓ Removidas {deleted_sessions} sessões vazias antigas")

            # 2. Link requests órfãos (mensagem não existe mais)
            result = await db.execute(text("""
                DELETE FROM link_requests
                WHERE message_id NOT IN (SELECT id FROM chat_messages)
                RETURNING id
            """))
            deleted_links = result.rowcount
            print(f"✓ Removidos {deleted_links} link requests órfãos")

            # 3. Document requests órfãos
            result = await db.execute(text("""
                DELETE FROM document_requests
                WHERE message_id NOT IN (SELECT id FROM chat_messages)
                RETURNING id
            """))
            deleted_docs = result.rowcount
            print(f"✓ Removidos {deleted_docs} document requests órfãos")

            # 4. Feedback órfão
            result = await db.execute(text("""
                DELETE FROM chat_feedback
                WHERE message_id NOT IN (SELECT id FROM chat_messages)
                RETURNING id
            """))
            deleted_feedback = result.rowcount
            print(f"✓ Removidos {deleted_feedback} feedbacks órfãos")

            await db.commit()

            print(f"\n✅ Limpeza concluída com sucesso!")
            print(f"Total removido: {deleted_sessions + deleted_links + deleted_docs + deleted_feedback} registros")

        except Exception as e:
            print(f"❌ Erro durante limpeza: {e}")
            await db.rollback()
            raise
        finally:
            break  # Exit after first db session


if __name__ == "__main__":
    asyncio.run(cleanup_orphaned_data())
