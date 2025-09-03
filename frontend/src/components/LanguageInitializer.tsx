/**
 * Component to initialize language based on user's preferred language setting
 */
import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n/hooks/useLanguage';

export const LanguageInitializer = () => {
  const { user, isAuthenticated } = useAuth();
  const { changeLanguage } = useLanguage();

  useEffect(() => {
    if (isAuthenticated && user) {
      // Use user's preferred language or default to English
      const languageToUse = user.preferred_language || 'en-US';
      
      console.log('🌐 LanguageInitializer: Setting language to:', languageToUse);
      
      changeLanguage(languageToUse);
    }
  }, [isAuthenticated, user, changeLanguage]);

  // This component doesn't render anything
  return null;
};