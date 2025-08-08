import React from 'react';
import { Badge } from './ui/badge';
import { Trophy, Medal, Award } from 'lucide-react';

interface Document {
  id: number;
  access_count: number;
  title: string;
}

interface PopularityRankingBadgeProps {
  document: Document;
  allDocuments: Document[];
}

export const PopularityRankingBadge: React.FC<PopularityRankingBadgeProps> = ({
  document,
  allDocuments
}) => {
  // Calcular ranking baseado no access_count
  const calculateRanking = () => {
    if (!allDocuments || allDocuments.length === 0) {
      return { rank: null, accessCount: document.access_count };
    }

    // Ordenar documentos por access_count (decrescente)
    const sortedDocs = allDocuments
      .filter(doc => doc.access_count > 0)
      .sort((a, b) => b.access_count - a.access_count);

    if (document.access_count === 0 || sortedDocs.length === 0) {
      return { rank: null, accessCount: document.access_count };
    }

    // Encontrar posição considerando empates
    let rank = 1;
    let currentAccessCount = sortedDocs[0]?.access_count;
    
    for (let i = 0; i < sortedDocs.length; i++) {
      const doc = sortedDocs[i];
      
      if (doc.access_count < currentAccessCount) {
        rank = i + 1;
        currentAccessCount = doc.access_count;
      }
      
      if (doc.id === document.id) {
        return { rank, accessCount: document.access_count };
      }
    }

    return { rank: null, accessCount: document.access_count };
  };

  const { rank, accessCount } = calculateRanking();

  // Se não tem acessos
  if (!accessCount || accessCount === 0) {
    return (
      <div className="flex justify-start">
        <Badge 
          variant="ranking-none"
          title="Este documento ainda não foi acessado"
          aria-label="Documento sem acessos"
        >
          Sem acessos
        </Badge>
      </div>
    );
  }

  // Se não está no ranking (não deveria acontecer, mas por segurança)
  if (!rank) {
    return (
      <div className="flex justify-start">
        <Badge 
          variant="ranking-regular"
          title={`${accessCount} acessos`}
          aria-label={`${accessCount} acessos`}
        >
          {accessCount} acesso{accessCount !== 1 ? 's' : ''}
        </Badge>
      </div>
    );
  }

  // Determinar variant e ícone baseado no ranking
  const getRankingVariant = () => {
    switch (rank) {
      case 1:
        return {
          variant: 'ranking-gold' as const,
          icon: <Trophy className="h-3 w-3 mr-1" aria-hidden="true" />,
          title: `🥇 Primeiro lugar com ${accessCount} acessos`
        };
      case 2:
        return {
          variant: 'ranking-silver' as const,
          icon: <Medal className="h-3 w-3 mr-1" aria-hidden="true" />,
          title: `🥈 Segundo lugar com ${accessCount} acessos`
        };
      case 3:
        return {
          variant: 'ranking-bronze' as const,
          icon: <Award className="h-3 w-3 mr-1" aria-hidden="true" />,
          title: `🥉 Terceiro lugar com ${accessCount} acessos`
        };
      case 4:
      case 5:
      case 6:
      case 7:
      case 8:
      case 9:
      case 10:
        return {
          variant: 'ranking-top' as const,
          icon: null,
          title: `${rank}º lugar com ${accessCount} acessos`
        };
      default:
        return {
          variant: 'ranking-regular' as const,
          icon: null,
          title: `${accessCount} acessos`
        };
    }
  };

  const { variant, icon, title } = getRankingVariant();

  // Renderizar badge com ranking
  if (rank <= 10) {
    return (
      <div className="flex justify-start">
        <Badge 
          variant={variant}
          title={title}
          aria-label={title}
          className="flex items-center whitespace-nowrap"
        >
          {icon}
          #{rank}&nbsp;&nbsp;&nbsp;—&nbsp;&nbsp;&nbsp;{accessCount} acesso{accessCount !== 1 ? 's' : ''}
        </Badge>
      </div>
    );
  }

  // Para documentos fora do top 10, mostrar apenas contagem
  return (
    <div className="flex justify-start">
      <Badge 
        variant="ranking-regular"
        title={`${accessCount} acessos`}
        aria-label={`${accessCount} acessos`}
      >
        {accessCount} acesso{accessCount !== 1 ? 's' : ''}
      </Badge>
    </div>
  );
};

export default PopularityRankingBadge;