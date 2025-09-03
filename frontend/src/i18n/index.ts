/**
 * i18n configuration for Knight Agent frontend
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
// import HttpBackend from 'i18next-http-backend'; // Not needed - using local resources

import { DEFAULT_LANGUAGE, normalizeLanguageCode } from './languages';

// Import local fallback resources
import enUS from './locales/en-US';
import ptBR from './locales/pt-BR';
import esES from './locales/es-ES';
import svSE from './locales/sv-SE';

const fallbackResources = {
  'en-US': enUS,
  'pt-BR': ptBR,
  'es-ES': esES,
  'sv-SE': svSE
};

i18n
  // .use(HttpBackend) // Disabled: Load translations from API
  .use(LanguageDetector) // Detect user language
  .use(initReactI18next) // Pass the i18n instance to react-i18next
  .init({
    // Fallback language
    fallbackLng: DEFAULT_LANGUAGE,
    
    // Debug mode (disable in production)
    debug: process.env.NODE_ENV === 'development',
    
    // Language detection options
    detection: {
      order: [
        'localStorage',
        'navigator',
        'htmlTag'
      ],
      caches: ['localStorage'],
      lookupLocalStorage: 'knight-language'
    },
    
    // Whitelist of supported languages
    supportedLngs: ['en-US', 'pt-BR', 'es-ES', 'sv-SE', 'en', 'pt', 'es', 'sv'],
    nonExplicitSupportedLngs: false, // Disable to avoid language code normalization issues
    
    // Single namespace configuration (simplified)
    defaultNS: 'translation',
    
    // Backend configuration disabled - using local resources only
    
    // Interpolation options
    interpolation: {
      escapeValue: false, // React already does escaping
      formatSeparator: ','
    },
    
    // React options
    react: {
      useSuspense: false, // Set to false to avoid loading issues
      bindI18n: 'languageChanged',
      bindI18nStore: '',
      transEmptyNodeValue: '',
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'em']
    },
    
    // Local resources
    resources: fallbackResources,
    
    // Language initialization - let i18next handle detection
    lng: undefined, // Let language detector handle initial language
  });

// Language change event handler
i18n.on('languageChanged', (lng: string) => {
  const normalizedLng = normalizeLanguageCode(lng);
  
  // Only save normalized language codes to localStorage
  if (normalizedLng !== lng) {
    localStorage.setItem('knight-language', normalizedLng);
  }
  
  // Set HTML lang attribute
  document.documentElement.lang = normalizedLng;
  
  // Update document title direction for RTL languages (future)
  document.documentElement.dir = 'ltr'; // All current languages are LTR
  
  console.log('🌐 Language changed to:', normalizedLng);
});

// Error handler
i18n.on('failedLoading', (lng: string, ns: string, msg: string) => {
  console.warn(`Failed to load translations for ${lng}/${ns}:`, msg);
});

// Initialize language after i18next is ready
i18n.on('initialized', () => {
  // Set initial language based on stored preference or browser language
  const storedLanguage = localStorage.getItem('knight-language');
  const initialLanguage = normalizeLanguageCode(storedLanguage || navigator.language || DEFAULT_LANGUAGE);
  
  console.log('🌐 Setting initial language:', initialLanguage);
  i18n.changeLanguage(initialLanguage);
});

export default i18n;