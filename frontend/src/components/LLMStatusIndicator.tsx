import React, { useState, useEffect, useImperativeHandle, forwardRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { useLLMStatusRefresh } from '../hooks/useLLMStatusRefresh';

interface LLMStatus {
  current_provider: string;
  provider_name: string;
  is_healthy: boolean;
  status: string;
}

export interface LLMStatusIndicatorRef {
  forceRefresh: () => Promise<void>;
}

export const LLMStatusIndicator = forwardRef<LLMStatusIndicatorRef>((props, ref) => {
  const { user } = useAuth();
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const { setGlobalRefresh } = useLLMStatusRefresh();

  const fetchLLMStatus = useCallback(async () => {
    // Não incluir user?.is_admin nas dependências para evitar loops
    // A verificação é feita no useEffect que chama esta função
    try {
      const response = await api.get('/rag/llm/status');
      setLlmStatus(response.data);
    } catch (error) {
      console.error('Erro ao buscar status do LLM:', error);
      setLlmStatus({
        current_provider: 'error',
        provider_name: 'Error',
        is_healthy: false,
        status: 'error'
      });
    } finally {
      setLoading(false);
    }
  }, []); // Sem dependências para manter a função estável

  useEffect(() => {
    // Só executa se é admin
    if (!user?.is_admin) {
      setLoading(false);
      return;
    }

    fetchLLMStatus();

    // Atualizar status a cada 5 minutos (menos overhead)
    const interval = setInterval(fetchLLMStatus, 300000);

    return () => clearInterval(interval);
  }, [user?.is_admin]); // Removido fetchLLMStatus das dependências

  // Registrar função de refresh global
  useEffect(() => {
    if (user?.is_admin) {
      setGlobalRefresh(fetchLLMStatus);
      return () => setGlobalRefresh(null);
    }
  }, [setGlobalRefresh, fetchLLMStatus, user?.is_admin]);

  // Expor método para forçar atualização
  useImperativeHandle(ref, () => ({
    forceRefresh: fetchLLMStatus
  }), []); // Sem dependências pois fetchLLMStatus é estável

  // Só mostra para administradores
  if (!user?.is_admin) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center ml-4">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
        <span className="ml-2 text-xs text-muted-foreground animate-pulse">...</span>
      </div>
    );
  }

  if (!llmStatus) {
    return null;
  }

  return (
    <div className="flex items-center ml-4 px-2 py-1 rounded-lg bg-muted/50 border border-border/50">
      {/* Status indicator dot */}
      <div 
        className={`w-2 h-2 rounded-full mr-2 ${
          llmStatus.is_healthy 
            ? 'bg-green-500' 
            : 'bg-red-500'
        }`}
        style={{ 
          backgroundColor: llmStatus.is_healthy ? '#10b981' : '#ef4444'
        }}
      ></div>
      
      {/* Provider name */}
      <span
        className="text-xs font-medium text-foreground"
        title={`LLM Provider: ${llmStatus.provider_name} (${llmStatus.current_provider})`}
      >
        {llmStatus.provider_name}
      </span>
      
      {/* Health status */}
      {!llmStatus.is_healthy && (
        <span className="ml-1 text-xs text-red-500" title="Provider com problemas">
          ⚠
        </span>
      )}
    </div>
  );
});

LLMStatusIndicator.displayName = 'LLMStatusIndicator';