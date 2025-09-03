/**
 * Language Selector Component
 * Allows users to switch between supported languages
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronDown, Globe } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { useLanguage } from '../i18n/hooks/useLanguage';
import { Language } from '../i18n/languages';

interface LanguageSelectorProps {
  variant?: 'default' | 'compact';
  showFlag?: boolean;
  showText?: boolean;
  className?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  variant = 'default',
  showFlag = true,
  showText = true,
  className = ''
}) => {
  const { t } = useTranslation();
  const { 
    currentLanguage, 
    availableLanguages, 
    changeLanguage, 
    isChangingLanguage,
    saveUserPreference 
  } = useLanguage();
  
  const [isOpen, setIsOpen] = useState(false);

  const handleLanguageChange = async (language: Language) => {
    try {
      // Change the language
      const success = await changeLanguage(language.code);
      
      if (success) {
        // Save user preference to backend (async, don't wait)
        saveUserPreference(language.code).catch(error => {
          console.warn('Could not save language preference to backend:', error);
        });
        
        setIsOpen(false);
      } else {
        console.error('Failed to change language');
      }
    } catch (error) {
      console.error('Error changing language:', error);
    }
  };

  const renderLanguageText = (language: Language) => {
    if (variant === 'compact') {
      return language.code.split('-')[0].toUpperCase(); // PT, EN, ES, SV
    }
    return showText ? language.name : language.code;
  };

  const renderCurrentLanguage = () => (
    <div className="flex items-center gap-2">
      {showFlag && <span className="text-lg">{currentLanguage.flag}</span>}
      <span className="font-medium">
        {renderLanguageText(currentLanguage)}
      </span>
      <ChevronDown className="h-4 w-4 transition-transform duration-200" />
    </div>
  );

  const renderLanguageItem = (language: Language) => (
    <div className="flex items-center gap-3">
      {showFlag && <span className="text-lg">{language.flag}</span>}
      <div className="flex-1">
        <div className="font-medium">{language.name}</div>
        {variant === 'default' && (
          <div className="text-sm text-muted-foreground">{language.code}</div>
        )}
      </div>
      {currentLanguage.code === language.code && (
        <Check className="h-4 w-4 text-primary" />
      )}
    </div>
  );

  if (variant === 'compact') {
    return (
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={`h-8 px-2 border ${className}`}
            disabled={isChangingLanguage}
            title={t('common.change_language', 'Change Language')}
          >
            {isChangingLanguage ? (
              <div className="animate-spin">
                <Globe className="h-4 w-4" />
              </div>
            ) : (
              renderCurrentLanguage()
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-48 bg-background/95 backdrop-blur-md border-border/20 shadow-xl">
          {availableLanguages.map((language) => (
            <DropdownMenuItem
              key={language.code}
              onClick={() => handleLanguageChange(language)}
              className="cursor-pointer hover:bg-accent/10 text-foreground"
            >
              {renderLanguageItem(language)}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="text-sm font-medium text-foreground">
        {t('common.language', 'Language')}
      </label>
      
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            className="w-full justify-between"
            disabled={isChangingLanguage}
          >
            {isChangingLanguage ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin">
                  <Globe className="h-4 w-4" />
                </div>
                <span>{t('common.loading', 'Loading...')}</span>
              </div>
            ) : (
              renderCurrentLanguage()
            )}
          </Button>
        </DropdownMenuTrigger>
        
        <DropdownMenuContent className="w-full min-w-[250px] bg-background/95 backdrop-blur-md border-border/20 shadow-xl">
          {availableLanguages.map((language) => (
            <DropdownMenuItem
              key={language.code}
              onClick={() => handleLanguageChange(language)}
              className="cursor-pointer p-3 hover:bg-accent/10 text-foreground"
            >
              {renderLanguageItem(language)}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};

export default LanguageSelector;