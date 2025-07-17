import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '../components/MainLayout';
import { MessageSquare, FileText, Download } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const handleNewChat = () => {
    navigate('/chat');
  };

  const handleDocuments = () => {
    // TODO: Implementar página de documentos
    console.log('Navegando para documentos...');
  };

  const handleDownloads = () => {
    // TODO: Implementar página de downloads
    console.log('Navegando para downloads...');
  };

  return (
    <MainLayout>
      <div className="h-full overflow-y-auto">
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Dashboard
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Visão geral do sistema Knight Agent
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div 
              onClick={handleNewChat}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  <MessageSquare className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Novo Chat
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Converse com o Knight Agent
                  </p>
                </div>
              </div>
            </div>

            <div 
              onClick={handleDocuments}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center">
                <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
                  <FileText className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Documentos
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Consultar políticas e manuais
                  </p>
                </div>
              </div>
            </div>

            <div 
              onClick={handleDownloads}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                  <Download className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Downloads
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Arquivos temporários
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Statistics */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Estatísticas do Sistema
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">0</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Documentos Indexados</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">0</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Conversas Realizadas</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">0</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Downloads Ativos</div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Atividade Recente
            </h3>
            <div className="space-y-3">
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <MessageSquare className="h-4 w-4 mr-2" />
                <span>Nenhuma conversa recente</span>
              </div>
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <FileText className="h-4 w-4 mr-2" />
                <span>Nenhum documento processado recentemente</span>
              </div>
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <Download className="h-4 w-4 mr-2" />
                <span>Nenhum download recente</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </MainLayout>
  );
};