/**
 * Configuration for supported languages in the frontend
 */

export interface Language {
  code: string;
  name: string;
  flag: string;
  isDefault?: boolean;
}

export const SUPPORTED_LANGUAGES: Language[] = [
  {
    code: 'pt-BR',
    name: 'Português (Brasil)',
    flag: '🇧🇷'
  },
  {
    code: 'en-US',
    name: 'English (United States)',
    flag: '🇺🇸',
    isDefault: true
  },
  {
    code: 'es-ES',
    name: 'Español (España)',
    flag: '🇪🇸'
  },
  {
    code: 'sv-SE',
    name: 'Svenska (Sverige)',
    flag: '🇸🇪'
  }
];

export const DEFAULT_LANGUAGE = 'en-US';

export const getLanguageByCode = (code: string): Language | undefined => {
  return SUPPORTED_LANGUAGES.find(lang => lang.code === code);
};

export const isValidLanguage = (code: string): boolean => {
  return SUPPORTED_LANGUAGES.some(lang => lang.code === code);
};

// Map i18next language codes to our format
export const LANGUAGE_CODE_MAP: Record<string, string> = {
  'pt-BR': 'pt-BR',
  'pt': 'pt-BR',
  'en-US': 'en-US',
  'en': 'en-US',
  'es-ES': 'es-ES',
  'es': 'es-ES',
  'sv-SE': 'sv-SE',
  'sv': 'sv-SE'
};

export const normalizeLanguageCode = (code: string): string => {
  return LANGUAGE_CODE_MAP[code] || DEFAULT_LANGUAGE;
};