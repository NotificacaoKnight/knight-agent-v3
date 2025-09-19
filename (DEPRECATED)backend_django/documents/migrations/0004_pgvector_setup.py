"""
Custom migration for pgvector setup
"""
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0003_documentchunk_embedding_json_and_more'),
    ]

    operations = [
        # Install pgvector extension
        VectorExtension(),
        
        # Create optimized index for vector similarity search
        migrations.RunSQL(
            sql="""
            -- Create HNSW index for cosine similarity
            CREATE INDEX IF NOT EXISTS documentchunk_embedding_hnsw_idx 
            ON documents_documentchunk 
            USING hnsw (embedding vector_cosine_ops) 
            WITH (m = 16, ef_construction = 64)
            WHERE embedding IS NOT NULL;
            
            -- Create GIN index for full-text search on content (Portuguese)
            CREATE INDEX IF NOT EXISTS documentchunk_content_gin_idx 
            ON documents_documentchunk 
            USING gin (to_tsvector('portuguese', content));
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS documentchunk_embedding_hnsw_idx;
            DROP INDEX IF EXISTS documentchunk_content_gin_idx;
            """
        ),
    ]