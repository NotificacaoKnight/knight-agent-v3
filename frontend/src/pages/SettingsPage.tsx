import React, { useState } from 'react';
import { MainLayout } from '../components/MainLayout';
import { UserAvatar } from '../components/UserAvatar';
import { LLMManagement } from '../components/LLMManagement';
import { LanguageSelector } from '../components/LanguageSelector';
import AdminManagement from '../components/AdminManagement';
import { useAuth } from '../context/AuthContext';
import { User, Bell, Shield, Palette, Bot, Globe } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { useTranslation } from 'react-i18next';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  
  // Estados para controlar as notificações
  const [newMessageNotifications, setNewMessageNotifications] = useState(true);
  const [documentNotifications, setDocumentNotifications] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(false);

  return (
    <MainLayout title={t('common.settings', 'Settings')} subtitle={t('settings.preferences', 'System Preferences')}>
      <div className="h-full overflow-y-auto custom-scrollbar">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-8">

          {/* Profile Section */}
          <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border mb-6">
            <div className="flex items-center mb-4">
              <User className="h-5 w-5 text-accent mr-2" />
              <h3 className="text-lg font-semibold text-foreground">
                {t('settings.user_profile', 'User Profile')}
              </h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <UserAvatar user={user || {}} size="lg" />
                <div>
                  <h4 className="text-lg font-medium text-foreground">
                    {user?.name || 'Usuário'}
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    {t('settings.photo_synced_microsoft')}
                  </p>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.name')}</label>
                <p className="text-foreground">{user?.name || t('settings.not_informed')}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.email')}</label>
                <p className="text-foreground">{user?.email}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.department')}</label>
                <p className="text-foreground">{user?.department || t('settings.not_informed')}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.job_title')}</label>
                <p className="text-foreground">{user?.job_title || t('settings.not_informed')}</p>
              </div>
            </div>
          </Card>

          {/* Language & Localization Section */}
          <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border mb-6">
            <div className="flex items-center mb-4">
              <Globe className="h-5 w-5 text-accent mr-2" />
              <h3 className="text-lg font-semibold text-foreground">
                {t('settings.language_preferences', 'Language Preferences')}
              </h3>
            </div>
            <div className="space-y-4">
              <div className="max-w-md">
                <LanguageSelector variant="default" />
                <p className="text-sm text-muted-foreground mt-2">
                  {t('settings.select_language', 'Select your preferred language for the interface')}
                </p>
              </div>
            </div>
          </Card>

          {/* Notifications Section */}
          <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border mb-6">
            <div className="flex items-center mb-4">
              <Bell className="h-5 w-5 text-accent mr-2" />
              <h3 className="text-lg font-semibold text-foreground">
                {t('settings.notifications')}
              </h3>
            </div>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <Checkbox 
                  id="new-messages"
                  checked={newMessageNotifications}
                  onCheckedChange={(checked) => setNewMessageNotifications(checked === true)}
                />
                <label 
                  htmlFor="new-messages" 
                  className="text-sm font-medium text-foreground cursor-pointer"
                >
                  {t('settings.notifications_new_messages')}
                </label>
              </div>
              
              <div className="flex items-center space-x-3">
                <Checkbox 
                  id="document-processed"
                  checked={documentNotifications}
                  onCheckedChange={(checked) => setDocumentNotifications(checked === true)}
                />
                <label 
                  htmlFor="document-processed" 
                  className="text-sm font-medium text-foreground cursor-pointer"
                >
                  {t('settings.notifications_documents_processed')}
                </label>
              </div>
              
              <div className="flex items-center space-x-3">
                <Checkbox 
                  id="email-notifications"
                  checked={emailNotifications}
                  onCheckedChange={(checked) => setEmailNotifications(checked === true)}
                />
                <label 
                  htmlFor="email-notifications" 
                  className="text-sm font-medium text-foreground cursor-pointer"
                >
                  {t('settings.notifications_email')}
                </label>
              </div>
            </div>
          </Card>

          {/* Appearance Section */}
          <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border mb-6">
            <div className="flex items-center mb-4">
              <Palette className="h-5 w-5 text-accent mr-2" />
              <h3 className="text-lg font-semibold text-foreground">
                {t('settings.appearance')}
              </h3>
            </div>
            <p className="text-muted-foreground">
              {t('settings.theme_toggle_hint')}
            </p>
          </Card>

          {/* LLM Management Section - Admin only */}
          {user?.is_admin && (
            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border mb-6">
              <div className="flex items-center mb-4">
                <Bot className="h-5 w-5 text-accent mr-2" />
                <h3 className="text-lg font-semibold text-foreground">
                  {t('settings.ai_settings')}
                </h3>
                <span className="ml-2 bg-accent text-accent-foreground text-xs px-2 py-1 rounded-full">
                  {t('settings.admin_badge')}
                </span>
              </div>
              <LLMManagement />
            </Card>
          )}

          {/* Admin Management Section - Admin only */}
          {user?.is_admin && (
            <div className="mb-6">
              <AdminManagement />
            </div>
          )}

          {/* Privacy Section */}
          <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border">
            <div className="flex items-center mb-4">
              <Shield className="h-5 w-5 text-accent mr-2" />
              <h3 className="text-lg font-semibold text-foreground">
                {t('settings.privacy_security')}
              </h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.session')}</label>
                <p className="text-muted-foreground text-sm">
                  {t('settings.session_expiry_info')}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">{t('settings.conversation_history')}</label>
                <p className="text-muted-foreground text-sm">
                  {t('settings.conversation_storage_info')}
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
};