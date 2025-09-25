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
      // Check if there's a recent local language choice
      const localLanguage = localStorage.getItem('knight-language');
      const localTimestamp = localStorage.getItem('knight-language-timestamp');

      // If local choice exists and was made in the last 5 minutes, respect it
      if (localLanguage && localTimestamp) {
        const timeDiff = Date.now() - parseInt(localTimestamp);
        if (timeDiff < 5 * 60 * 1000) { // 5 minutes
          console.log('🌐 LanguageInitializer: Respecting recent local language choice:', localLanguage);
          return; // Don't override recent local choice
        } else {
          console.log('🌐 LanguageInitializer: Local language choice expired, using backend preference');
        }
      }

      // Otherwise use user's backend preference
      const languageToUse = user.preferred_language || 'en-US';
      console.log('🌐 LanguageInitializer: Setting language from backend preference:', languageToUse);

      changeLanguage(languageToUse);
    }
  }, [isAuthenticated, user, changeLanguage]);

  // This component doesn't render anything
  return null;
};