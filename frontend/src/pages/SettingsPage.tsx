import React from 'react';
import { MainLayout } from '../components/MainLayout';
import { UserAvatar } from '../components/UserAvatar';
import { useAuth } from '../context/AuthContext';
import { User, Bell, Shield, Palette } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <MainLayout>
      <div className="h-full overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Configurações
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Gerencie suas preferências e configurações do sistema
            </p>
          </div>

          {/* Profile Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-center mb-4">
              <User className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-2" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Perfil do Usuário
              </h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <UserAvatar user={user || {}} size="lg" />
                <div>
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white">
                    {user?.name || 'Usuário'}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Foto sincronizada do Microsoft 365
                  </p>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Nome</label>
                <p className="text-gray-900 dark:text-white">{user?.name || 'Não informado'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
                <p className="text-gray-900 dark:text-white">{user?.email}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Departamento</label>
                <p className="text-gray-900 dark:text-white">{user?.department || 'Não informado'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Cargo</label>
                <p className="text-gray-900 dark:text-white">{user?.job_title || 'Não informado'}</p>
              </div>
            </div>
          </div>

          {/* Notifications Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-center mb-4">
              <Bell className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-2" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Notificações
              </h3>
            </div>
            <div className="space-y-3">
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" defaultChecked />
                <span className="text-gray-700 dark:text-gray-300">Notificações de novas mensagens</span>
              </label>
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" defaultChecked />
                <span className="text-gray-700 dark:text-gray-300">Notificações de documentos processados</span>
              </label>
              <label className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span className="text-gray-700 dark:text-gray-300">Notificações por email</span>
              </label>
            </div>
          </div>

          {/* Appearance Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-center mb-4">
              <Palette className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-2" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Aparência
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              Use o botão de tema no menu lateral para alternar entre modo claro e escuro.
            </p>
          </div>

          {/* Privacy Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center mb-4">
              <Shield className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-2" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Privacidade e Segurança
              </h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Sessão</label>
                <p className="text-gray-600 dark:text-gray-400 text-sm">
                  Sua sessão expira automaticamente após 1 hora de inatividade
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Histórico de Conversas</label>
                <p className="text-gray-600 dark:text-gray-400 text-sm">
                  Suas conversas são armazenadas de forma segura e são acessíveis apenas por você
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};