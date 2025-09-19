/**
 * Custom hook for language management
 */
import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  SUPPORTED_LANGUAGES, 
  Language, 
  DEFAULT_LANGUAGE, 
  getLanguageByCode, 
  isValidLanguage, 
  normalizeLanguageCode 
} from '../languages';

interface UseLanguageReturn {
  currentLanguage: Language;
  availableLanguages: Language[];
  changeLanguage: (languageCode: string) => Promise<boolean>;
  isChangingLanguage: boolean;
  saveUserPreference: (languageCode: string) => Promise<boolean>;
}

export const useLanguage = (): UseLanguageReturn => {
  const { i18n } = useTranslation();
  const [isChangingLanguage, setIsChangingLanguage] = useState(false);
  
  // Get current language object
  const getCurrentLanguage = useCallback((): Language => {
    const currentCode = normalizeLanguageCode(i18n.language);
    return getLanguageByCode(currentCode) || getLanguageByCode(DEFAULT_LANGUAGE)!;
  }, [i18n.language]);
  
  const [currentLanguage, setCurrentLanguage] = useState<Language>(getCurrentLanguage());
  
  // Update current language when i18n language changes
  useEffect(() => {
    setCurrentLanguage(getCurrentLanguage());
  }, [getCurrentLanguage]);
  
  /**
   * Change the application language
   */
  const changeLanguage = useCallback(async (languageCode: string): Promise<boolean> => {
    try {
      setIsChangingLanguage(true);
      
      // Validate language code
      if (!isValidLanguage(languageCode)) {
        console.error(`Invalid language code: ${languageCode}`);
        return false;
      }
      
      const normalizedCode = normalizeLanguageCode(languageCode);
      
      // Change i18next language
      await i18n.changeLanguage(normalizedCode);
      
      // Update local state
      const newLanguage = getLanguageByCode(normalizedCode);
      if (newLanguage) {
        setCurrentLanguage(newLanguage);
      }
      
      // Save to localStorage (i18next will handle this automatically)
      localStorage.setItem('knight-language', normalizedCode);
      
      console.log('Language changed successfully to:', normalizedCode);
      return true;
      
    } catch (error) {
      console.error('Failed to change language:', error);
      return false;
    } finally {
      setIsChangingLanguage(false);
    }
  }, [i18n]);
  
  /**
   * Save user language preference to backend
   */
  const saveUserPreference = useCallback(async (languageCode: string): Promise<boolean> => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('sessionToken') || ''}`,
        },
        body: JSON.stringify({ language: languageCode })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log('User language preference saved:', languageCode);
          return true;
        }
      }
      
      console.warn('Failed to save user language preference');
      return false;
      
    } catch (error) {
      console.error('Error saving user language preference:', error);
      return false;
    }
  }, []);
  
  
  return {
    currentLanguage,
    availableLanguages: SUPPORTED_LANGUAGES,
    changeLanguage,
    isChangingLanguage,
    saveUserPreference
  };
};