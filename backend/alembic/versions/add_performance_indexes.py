"""Add performance indexes for RAG and search optimization

Revision ID: add_performance_indexes_001
Revises: add_document_fields
Create Date: 2024-01-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_performance_indexes_001'
down_revision = 'add_document_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Add performance indexes for optimized queries
    """

    # Indexes for chat_sessions table
    # Index for user queries (most common access pattern)
    op.create_index(
        'ix_chat_sessions_user_created',
        'chat_sessions',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )

    # Index for finding recent sessions
    op.create_index(
        'ix_chat_sessions_created_desc',
        'chat_sessions',
        [sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    # Indexes for documents table
    # Index for document search and filtering
    op.create_index(
        'ix_documents_status_created',
        'documents',
        ['processing_status', 'created_at'],
        postgresql_using='btree'
    )

    # Index for user's documents
    op.create_index(
        'ix_documents_user_created',
        'documents',
        ['uploaded_by_id', 'created_at'],
        postgresql_using='btree'
    )

    # Full text search index on title and description
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_fulltext
        ON documents
        USING gin(to_tsvector('portuguese', coalesce(title, '') || ' ' || coalesce(description, '')))
    """)

    # Indexes for document_chunks table (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks') THEN
                -- Index for chunk retrieval by document
                CREATE INDEX IF NOT EXISTS ix_chunks_document_index
                ON document_chunks(document_id, chunk_index);

                -- Index for chunk metadata queries
                CREATE INDEX IF NOT EXISTS ix_chunks_document_metadata
                ON document_chunks(document_id, metadata);
            END IF;
        END $$;
    """)

    # Indexes for embeddings table (if using pgvector)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'embeddings') THEN
                -- HNSW index for vector similarity search
                CREATE INDEX IF NOT EXISTS ix_embeddings_vector_hnsw
                ON embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);

                -- B-tree index for document filtering
                CREATE INDEX IF NOT EXISTS ix_embeddings_document
                ON embeddings(document_id);

                -- Composite index for filtered vector search
                CREATE INDEX IF NOT EXISTS ix_embeddings_doc_chunk
                ON embeddings(document_id, chunk_id);
            END IF;
        END $$;
    """)

    # Indexes for knowledge resources
    op.execute("""
        DO $$
        BEGIN
            -- Indexes for useful_links table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'useful_links') THEN
                -- Index for category filtering
                CREATE INDEX IF NOT EXISTS ix_useful_links_category
                ON useful_links(category_id);

                -- Index for active links
                CREATE INDEX IF NOT EXISTS ix_useful_links_active
                ON useful_links(is_active);

                -- Full text search on ai_guidance
                CREATE INDEX IF NOT EXISTS ix_useful_links_ai_guidance
                ON useful_links
                USING gin(to_tsvector('portuguese', coalesce(ai_guidance, '')));
            END IF;

            -- Indexes for downloadable_documents table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'downloadable_documents') THEN
                -- Index for category filtering
                CREATE INDEX IF NOT EXISTS ix_downloads_category
                ON downloadable_documents(category_id);

                -- Index for active documents
                CREATE INDEX IF NOT EXISTS ix_downloads_active
                ON downloadable_documents(is_active);

                -- Full text search on ai_guidance
                CREATE INDEX IF NOT EXISTS ix_downloads_ai_guidance
                ON downloadable_documents
                USING gin(to_tsvector('portuguese', coalesce(ai_guidance, '')));
            END IF;
        END $$;
    """)

    # Indexes for user sessions
    op.create_index(
        'ix_user_sessions_active',
        'user_sessions',
        ['is_active', 'expires_at'],
        postgresql_using='btree'
    )

    # Index for token lookup
    op.create_index(
        'ix_user_sessions_token',
        'user_sessions',
        ['session_token'],
        postgresql_using='hash',
        unique=True
    )

    # Indexes for chat messages (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_messages') THEN
                -- Index for retrieving messages by session
                CREATE INDEX IF NOT EXISTS ix_messages_session_created
                ON chat_messages(session_id, created_at);

                -- Index for message type filtering
                CREATE INDEX IF NOT EXISTS ix_messages_role
                ON chat_messages(role);
            END IF;
        END $$;
    """)

def downgrade() -> None:
    """
    Remove performance indexes
    """

    # Remove chat_sessions indexes
    op.drop_index('ix_chat_sessions_user_created', 'chat_sessions')
    op.drop_index('ix_chat_sessions_created_desc', 'chat_sessions')

    # Remove documents indexes
    op.drop_index('ix_documents_status_created', 'documents')
    op.drop_index('ix_documents_user_created', 'documents')
    op.execute("DROP INDEX IF EXISTS ix_documents_fulltext")

    # Remove document_chunks indexes
    op.execute("DROP INDEX IF EXISTS ix_chunks_document_index")
    op.execute("DROP INDEX IF EXISTS ix_chunks_document_metadata")

    # Remove embeddings indexes
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_document")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_doc_chunk")

    # Remove knowledge resources indexes
    op.execute("DROP INDEX IF EXISTS ix_useful_links_category")
    op.execute("DROP INDEX IF EXISTS ix_useful_links_active")
    op.execute("DROP INDEX IF EXISTS ix_useful_links_ai_guidance")
    op.execute("DROP INDEX IF EXISTS ix_downloads_category")
    op.execute("DROP INDEX IF EXISTS ix_downloads_active")
    op.execute("DROP INDEX IF EXISTS ix_downloads_ai_guidance")

    # Remove user sessions indexes
    op.drop_index('ix_user_sessions_active', 'user_sessions')
    op.drop_index('ix_user_sessions_token', 'user_sessions')

    # Remove chat messages indexes
    op.execute("DROP INDEX IF EXISTS ix_messages_session_created")
    op.execute("DROP INDEX IF EXISTS ix_messages_role")