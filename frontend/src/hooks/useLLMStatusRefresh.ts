import { useRef, useCallback } from 'react';

// Hook global para controlar refresh do LLM Status
let globalRefreshCallback: (() => Promise<void>) | null = null;

export const useLLMStatusRefresh = () => {
  const setGlobalRefresh = useCallback((callback: (() => Promise<void>) | null) => {
    globalRefreshCallback = callback;
  }, []);

  const refreshLLMStatus = useCallback(async () => {
    if (globalRefreshCallback) {
      await globalRefreshCallback();
    }
  }, []);

  return {
    setGlobalRefresh,
    refreshLLMStatus
  };
};