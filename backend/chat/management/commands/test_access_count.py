"""
Comando para testar e analisar o sistema de contagem de acesso de documentos
Permite simular diferentes cenários e validar a precisão das métricas
"""

import json
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Avg
from documents.models import Document
from chat.access_count_config import AccessCountConfig


class Command(BaseCommand):
    help = 'Testa e analisa o sistema de contagem de acesso de documentos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--simulate',
            action='store_true',
            help='Simula cenários de busca sem modificar dados',
        )
        
        parser.add_argument(
            '--strategy',
            type=str,
            default='top_n',
            choices=['top_n', 'single_best', 'threshold_only'],
            help='Estratégia de seleção a testar',
        )
        
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.6,
            help='Threshold mínimo de relevância',
        )
        
        parser.add_argument(
            '--max-docs',
            type=int,
            default=3,
            help='Máximo de documentos para estratégia top_n',
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Mostra estatísticas atuais de acesso',
        )
        
        parser.add_argument(
            '--reset-counts',
            action='store_true',
            help='CUIDADO: Zera todos os contadores de acesso',
        )
    
    def handle(self, *args, **options):
        """Executa o comando"""
        if options['stats']:
            self._show_access_stats()
            
        if options['reset_counts']:
            self._reset_access_counts()
            
        if options['simulate']:
            self._simulate_scenarios(
                strategy=options['strategy'],
                threshold=options['threshold'],
                max_docs=options['max_docs']
            )
    
    def _show_access_stats(self):
        """Mostra estatísticas atuais de acesso aos documentos"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 ESTATÍSTICAS ATUAIS DE ACESSO AOS DOCUMENTOS")
        self.stdout.write("="*60)
        
        # Stats gerais
        total_docs = Document.objects.filter(is_active=True).count()
        total_accesses = Document.objects.filter(is_active=True).aggregate(
            total=Sum('access_count')
        )['total'] or 0
        
        avg_access = Document.objects.filter(is_active=True).aggregate(
            avg=Avg('access_count')
        )['avg'] or 0
        
        self.stdout.write(f"📈 Total de documentos ativos: {total_docs}")
        self.stdout.write(f"🎯 Total de acessos registrados: {total_accesses}")
        self.stdout.write(f"📊 Média de acessos por documento: {avg_access:.2f}")
        
        # Top 10 documentos mais acessados
        self.stdout.write("\n🏆 TOP 10 DOCUMENTOS MAIS ACESSADOS:")
        top_docs = Document.objects.filter(is_active=True).order_by('-access_count')[:10]
        
        for i, doc in enumerate(top_docs, 1):
            title = doc.title[:50] + "..." if len(doc.title) > 50 else doc.title
            self.stdout.write(f"  {i:2d}. {title} ({doc.access_count} acessos)")
        
        # Distribuição de acessos
        self.stdout.write("\n📊 DISTRIBUIÇÃO DE ACESSOS:")
        ranges = [
            (0, 0, "Nunca acessados"),
            (1, 5, "1-5 acessos"),
            (6, 10, "6-10 acessos"),
            (11, 20, "11-20 acessos"),
            (21, float('inf'), "21+ acessos")
        ]
        
        for min_val, max_val, label in ranges:
            if max_val == float('inf'):
                count = Document.objects.filter(
                    is_active=True,
                    access_count__gte=min_val
                ).count()
            else:
                count = Document.objects.filter(
                    is_active=True,
                    access_count__gte=min_val,
                    access_count__lte=max_val
                ).count()
            
            percentage = (count / total_docs * 100) if total_docs > 0 else 0
            self.stdout.write(f"  {label}: {count} documentos ({percentage:.1f}%)")
    
    def _reset_access_counts(self):
        """Zera todos os contadores de acesso - USE COM CUIDADO!"""
        confirm = input("\n⚠️  ATENÇÃO: Isso irá zerar TODOS os contadores de acesso!\n"
                       "Digite 'CONFIRMO' para continuar: ")
        
        if confirm == 'CONFIRMO':
            updated = Document.objects.filter(is_active=True).update(access_count=0)
            self.stdout.write(
                self.style.WARNING(f"🗑️  Zerados contadores de {updated} documentos")
            )
        else:
            self.stdout.write("❌ Operação cancelada")
    
    def _simulate_scenarios(self, strategy: str, threshold: float, max_docs: int):
        """Simula diferentes cenários de busca"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("🧪 SIMULAÇÃO DE CENÁRIOS DE CONTAGEM")
        self.stdout.write("="*60)
        
        # Configurar para teste
        config = AccessCountConfig()
        config.SELECTION_STRATEGY = strategy
        config.MIN_SCORE_THRESHOLD = threshold
        config.MAX_DOCUMENTS = max_docs
        
        self.stdout.write(f"⚙️  Estratégia: {strategy}")
        self.stdout.write(f"🎯 Threshold: {threshold}")
        self.stdout.write(f"📊 Max docs: {max_docs}")
        
        # Cenários de teste
        scenarios = [
            {
                'name': 'Query Precisa - "crédito consignado"',
                'results': [
                    {'document_id': 1, 'combined_score': 0.95, 'title': 'Crédito Consignado.docx'},
                    {'document_id': 2, 'combined_score': 0.75, 'title': 'Manual de Benefícios.pdf'},
                    {'document_id': 3, 'combined_score': 0.45, 'title': 'Política de Veículos.docx'},
                    {'document_id': 4, 'combined_score': 0.35, 'title': 'Regulamento Geral.pdf'},
                ]
            },
            {
                'name': 'Query Ampla - "políticas da empresa"',
                'results': [
                    {'document_id': 5, 'combined_score': 0.80, 'title': 'Código de Ética.pdf'},
                    {'document_id': 6, 'combined_score': 0.75, 'title': 'Manual do Funcionário.docx'},
                    {'document_id': 7, 'combined_score': 0.70, 'title': 'Política de RH.pdf'},
                    {'document_id': 8, 'combined_score': 0.55, 'title': 'Normas de Segurança.docx'},
                    {'document_id': 9, 'combined_score': 0.40, 'title': 'Política de TI.pdf'},
                ]
            },
            {
                'name': 'Query Vaga - "ajuda"',
                'results': [
                    {'document_id': 10, 'combined_score': 0.50, 'title': 'FAQ Geral.pdf'},
                    {'document_id': 11, 'combined_score': 0.45, 'title': 'Manual de Apoio.docx'},
                    {'document_id': 12, 'combined_score': 0.40, 'title': 'Contatos Úteis.pdf'},
                ]
            }
        ]
        
        for scenario in scenarios:
            self.stdout.write(f"\n🎯 CENÁRIO: {scenario['name']}")
            self.stdout.write("-" * 40)
            
            # Simular seleção
            selected_docs = self._simulate_selection(scenario['results'], config)
            
            self.stdout.write(f"📋 Resultados totais: {len(scenario['results'])}")
            self.stdout.write(f"✅ Documentos selecionados: {len(selected_docs)}")
            
            for doc in selected_docs:
                score = doc['combined_score']
                title = doc['title']
                self.stdout.write(f"  📄 {title} (score: {score:.3f})")
            
            # Mostrar documentos rejeitados
            all_doc_ids = {r['document_id'] for r in scenario['results']}
            selected_doc_ids = {r['document_id'] for r in selected_docs}
            rejected_doc_ids = all_doc_ids - selected_doc_ids
            
            if rejected_doc_ids:
                self.stdout.write("❌ Documentos rejeitados:")
                for result in scenario['results']:
                    if result['document_id'] in rejected_doc_ids:
                        reason = self._get_rejection_reason(result, config)
                        score = result['combined_score']
                        title = result['title']
                        self.stdout.write(f"  🚫 {title} (score: {score:.3f}) - {reason}")
    
    def _simulate_selection(self, results: list, config: AccessCountConfig) -> list:
        """Simula a seleção de documentos baseada na configuração"""
        # Agrupar por document_id (pegar melhor score)
        document_scores = {}
        for result in results:
            doc_id = result['document_id']
            score = config.get_score_from_result(result)
            
            if doc_id not in document_scores or score > document_scores[doc_id]['score']:
                document_scores[doc_id] = {
                    'score': score,
                    'result': result
                }
        
        # Ordenar por score
        sorted_docs = sorted(document_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Aplicar critérios de seleção
        selected = []
        for rank, (doc_id, data) in enumerate(sorted_docs):
            if config.should_increment_document(data['score'], rank):
                selected.append(data['result'])
        
        return selected
    
    def _get_rejection_reason(self, result: dict, config: AccessCountConfig) -> str:
        """Determina por que um documento foi rejeitado"""
        score = config.get_score_from_result(result)
        
        if score < config.MIN_SCORE_THRESHOLD:
            return f"Score abaixo do threshold ({config.MIN_SCORE_THRESHOLD})"
        
        if config.SELECTION_STRATEGY == 'single_best':
            return "Estratégia 'single_best' - apenas o melhor"
        elif config.SELECTION_STRATEGY == 'top_n':
            return f"Fora do top {config.MAX_DOCUMENTS}"
        
        return "Critério desconhecido"