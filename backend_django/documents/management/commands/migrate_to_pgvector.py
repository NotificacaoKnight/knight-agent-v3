"""
Management command to migrate embeddings from FAISS/JSON to pgvector
"""
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from documents.models import DocumentChunk
from rag.pgvector_service import PgVectorSearchService, PgVectorIndexManager
import numpy as np
import json
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Migrate embeddings from FAISS/JSON to pgvector'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', 
            type=int, 
            default=1000,
            help='Number of chunks to process in each batch'
        )
        parser.add_argument(
            '--verify', 
            action='store_true',
            help='Verify migration by comparing search results'
        )
        parser.add_argument(
            '--create-index',
            action='store_true',
            help='Create optimal index after migration'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        
        self.stdout.write(self.style.WARNING("Starting FAISS to pgvector migration..."))
        
        # First, check if we have any existing embeddings in JSON format
        chunks_with_json = DocumentChunk.objects.filter(
            embedding_json__isnull=False
        ).count()
        
        # Check if we have chunks without any embeddings
        chunks_without_embeddings = DocumentChunk.objects.filter(
            embedding__isnull=True,
            embedding_json__isnull=True
        ).count()
        
        self.stdout.write(f"Found {chunks_with_json} chunks with JSON embeddings")
        self.stdout.write(f"Found {chunks_without_embeddings} chunks without any embeddings")
        
        if chunks_with_json == 0:
            self.stdout.write(self.style.WARNING(
                "No JSON embeddings found. Checking for existing FAISS index..."
            ))
            
            # Try to load embeddings from FAISS index
            self._migrate_from_faiss_index(batch_size)
        else:
            # Migrate from JSON embeddings
            self._migrate_from_json(batch_size)
        
        if options['create_index']:
            self._create_index()
        
        if options['verify']:
            self._verify_migration()
        
        self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))
    
    def _migrate_from_json(self, batch_size):
        """Migrate embeddings from JSON field to pgvector field"""
        chunks_to_migrate = DocumentChunk.objects.filter(
            embedding_json__isnull=False,
            embedding__isnull=True
        )
        
        total_chunks = chunks_to_migrate.count()
        
        if total_chunks == 0:
            self.stdout.write("No chunks to migrate from JSON")
            return
        
        migrated = 0
        
        # Use tqdm for progress bar if available
        try:
            from tqdm import tqdm
            iterator = tqdm(
                range(0, total_chunks, batch_size),
                desc="Migrating chunks",
                total=total_chunks // batch_size + 1
            )
        except ImportError:
            iterator = range(0, total_chunks, batch_size)
        
        for start in iterator:
            with transaction.atomic():
                batch = list(chunks_to_migrate[start:start + batch_size])
                updates = []
                
                for chunk in batch:
                    if chunk.embedding_json:
                        # Convert JSON list to vector
                        try:
                            if isinstance(chunk.embedding_json, str):
                                embedding_data = json.loads(chunk.embedding_json)
                            else:
                                embedding_data = chunk.embedding_json
                            
                            chunk.embedding = embedding_data
                            updates.append(chunk)
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error processing chunk {chunk.id}: {e}")
                            )
                
                if updates:
                    DocumentChunk.objects.bulk_update(
                        updates, ['embedding'], batch_size=batch_size
                    )
                    migrated += len(updates)
                    
                    if migrated % 5000 == 0:
                        self.stdout.write(f"Migrated {migrated}/{total_chunks} chunks")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully migrated {migrated} chunks from JSON")
        )
    
    def _migrate_from_faiss_index(self, batch_size):
        """Attempt to migrate embeddings from existing FAISS index"""
        try:
            from rag.services import VectorSearchService
            
            vector_service = VectorSearchService()
            
            # Check if FAISS index exists and is loaded
            if not hasattr(vector_service, 'vector_store') or vector_service.vector_store is None:
                self.stdout.write("No FAISS index found")
                return
            
            # Get all chunks that need embeddings
            chunks_to_embed = DocumentChunk.objects.filter(
                embedding__isnull=True
            ).select_related('document')
            
            total_chunks = chunks_to_embed.count()
            
            if total_chunks == 0:
                self.stdout.write("No chunks need embeddings")
                return
            
            self.stdout.write(f"Found {total_chunks} chunks that need embeddings")
            
            # Check if we have embeddings in the FAISS document_chunks mapping
            if hasattr(vector_service, 'document_chunks'):
                migrated = 0
                
                for chunk in chunks_to_embed:
                    chunk_key = f"{chunk.document_id}_{chunk.chunk_index}"
                    
                    if chunk_key in vector_service.document_chunks:
                        chunk_data = vector_service.document_chunks[chunk_key]
                        
                        if 'embedding' in chunk_data:
                            # Save embedding to pgvector field
                            chunk.embedding = chunk_data['embedding']
                            # Also save to JSON for backup
                            chunk.embedding_json = chunk_data['embedding']
                            chunk.save(update_fields=['embedding', 'embedding_json'])
                            migrated += 1
                            
                            if migrated % 100 == 0:
                                self.stdout.write(f"Migrated {migrated} chunks from FAISS")
                
                self.stdout.write(
                    self.style.SUCCESS(f"Migrated {migrated} chunks from FAISS index")
                )
            else:
                self.stdout.write("No document chunks mapping found in FAISS service")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error migrating from FAISS: {e}")
            )
    
    def _create_index(self):
        """Create optimal pgvector index"""
        self.stdout.write("Creating optimal pgvector index...")
        
        try:
            index_manager = PgVectorIndexManager()
            index_manager.create_optimal_index()
            self.stdout.write(
                self.style.SUCCESS("Index created successfully")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to create index: {e}")
            )
    
    def _verify_migration(self):
        """Verify migration by testing search functionality"""
        self.stdout.write("Verifying migration...")
        
        try:
            # Test with pgvector service
            pgvector_service = PgVectorSearchService()
            
            # Get statistics
            stats = pgvector_service.get_stats()
            self.stdout.write(f"Statistics: {stats}")
            
            # Test search
            test_queries = [
                "exemplo de teste",
                "documento importante",
                "informação relevante"
            ]
            
            for query in test_queries:
                results = pgvector_service.search(query, k=3)
                self.stdout.write(f"Query: '{query}' - Found {len(results)} results")
                
                if results:
                    self.stdout.write(f"  Top result score: {results[0]['score']:.4f}")
            
            self.stdout.write(
                self.style.SUCCESS("Verification completed successfully")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Verification failed: {e}")
            )