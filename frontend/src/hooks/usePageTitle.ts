import { useEffect, useRef } from 'react';

export const usePageTitle = (title: string = 'Knight - Assistente IA') => {
  const isInitializedRef = useRef(false);
  const originalTitleRef = useRef<string>('');

  useEffect(() => {
    // Initialize only once, even in StrictMode
    if (!isInitializedRef.current) {
      originalTitleRef.current = document.title;
      isInitializedRef.current = true;
    }
    
    // Set title only if it's different
    if (document.title !== title) {
      document.title = title;
    }

    // Cleanup: restore original title on unmount
    return () => {
      if (isInitializedRef.current && originalTitleRef.current) {
        document.title = originalTitleRef.current;
      }
    };
  }, [title]);
};