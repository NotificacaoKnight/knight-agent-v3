import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ThemeToggle } from './ThemeToggle';
import {
  Bot,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  MessageSquare,
  ChevronRight,
  ChevronLeft,
  Plus
} from 'lucide-react';

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ElementType;
  path: string;
}

interface ChatHistory {
  id: string;
  title: string;
  timestamp: Date;
  preview: string;
}

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Menu items
  const menuItems: SidebarItem[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare, path: '/chat' },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    { id: 'settings', label: 'Configurações', icon: Settings, path: '/settings' },
  ];

  // Mock chat history - será substituído por dados reais
  const chatHistory: ChatHistory[] = [
    {
      id: '1',
      title: 'Políticas de RH',
      timestamp: new Date(Date.now() - 3600000),
      preview: 'Quais são as políticas de trabalho remoto?'
    },
    {
      id: '2',
      title: 'Relatório de Vendas',
      timestamp: new Date(Date.now() - 7200000),
      preview: 'Preciso do relatório de vendas do último trimestre'
    },
    {
      id: '3',
      title: 'Suporte TI',
      timestamp: new Date(Date.now() - 86400000),
      preview: 'Como resetar minha senha do sistema?'
    },
  ];

  const handleMenuClick = (path: string) => {
    navigate(path);
    setMobileMenuOpen(false);
  };

  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 60) return 'agora';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}min atrás`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h atrás`;
    return `${Math.floor(hours / 24)}d atrás`;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Left Sidebar - Menu */}
      <div
        className={`${
          leftSidebarOpen ? 'w-16' : 'w-0'
        } bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="h-16 flex items-center justify-center border-b border-gray-200 dark:border-gray-700">
            <Bot className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>

          {/* Menu Items */}
          <nav className="flex-1 py-4">
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <button
                  key={item.id}
                  onClick={() => handleMenuClick(item.path)}
                  className={`w-full p-3 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors relative group ${
                    isActive ? 'bg-gray-100 dark:bg-gray-700' : ''
                  }`}
                  title={item.label}
                >
                  <item.icon
                    className={`h-5 w-5 ${
                      isActive
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-600 dark:text-gray-400'
                    }`}
                  />
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 dark:bg-blue-400" />
                  )}
                  <span className="absolute left-16 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    {item.label}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Bottom Actions */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-2">
            <div className="w-full p-3 flex items-center justify-center">
              <ThemeToggle />
            </div>
            <button
              onClick={logout}
              className="w-full p-3 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Sair"
            >
              <LogOut className="h-5 w-5 text-red-600 dark:text-red-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Chat History Sidebar */}
      <div className="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex-shrink-0 hidden md:block">
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
            <h2 className="font-semibold text-gray-900 dark:text-white">Conversas</h2>
            <button
              onClick={() => navigate('/chat')}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Nova conversa"
            >
              <Plus className="h-4 w-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto">
            {chatHistory.map((chat) => (
              <button
                key={chat.id}
                onClick={() => navigate(`/chat/${chat.id}`)}
                className="w-full p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors border-b border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-start justify-between mb-1">
                  <h3 className="font-medium text-sm text-gray-900 dark:text-white truncate flex-1">
                    {chat.title}
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                    {formatTimeAgo(chat.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                  {chat.preview}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4">
          <div className="flex items-center">
            {/* Mobile menu toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors md:hidden"
            >
              <Menu className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </button>
            
            {/* Left sidebar toggle */}
            <button
              onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors hidden md:flex"
            >
              {leftSidebarOpen ? (
                <ChevronLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <ChevronRight className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              )}
            </button>

            <h1 className="ml-4 text-xl font-semibold text-gray-900 dark:text-white">
              Knight Agent
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {user?.name || user?.email}
            </span>
            
            {/* Right sidebar toggle */}
            <button
              onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <Menu className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>

      {/* Right Sidebar - Collapsible */}
      <div
        className={`${
          rightSidebarOpen ? 'w-64' : 'w-0'
        } bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        <div className="h-full p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">Informações</h3>
            <button
              onClick={() => setRightSidebarOpen(false)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              <X className="h-4 w-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
          
          {/* Placeholder content for right sidebar */}
          <div className="space-y-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                Documentos Recentes
              </h4>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Nenhum documento carregado
              </p>
            </div>
            
            <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                Estatísticas
              </h4>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Conversas hoje: 0
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed left-0 top-0 bottom-0 w-64 bg-white dark:bg-gray-800 shadow-lg">
            <div className="h-full flex flex-col">
              <div className="h-16 px-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center">
                  <Bot className="h-6 w-6 text-blue-600 dark:text-blue-400 mr-2" />
                  <span className="font-semibold text-gray-900 dark:text-white">Knight Agent</span>
                </div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </button>
              </div>

              <nav className="flex-1 p-4">
                {menuItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleMenuClick(item.path)}
                      className={`w-full p-3 flex items-center hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors mb-2 ${
                        isActive ? 'bg-gray-100 dark:bg-gray-700' : ''
                      }`}
                    >
                      <item.icon
                        className={`h-5 w-5 mr-3 ${
                          isActive
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-gray-600 dark:text-gray-400'
                        }`}
                      />
                      <span className={`${
                        isActive
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-900 dark:text-white'
                      }`}>
                        {item.label}
                      </span>
                    </button>
                  );
                })}
              </nav>

              <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                <button
                  onClick={logout}
                  className="w-full p-3 flex items-center hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-red-600 dark:text-red-400"
                >
                  <LogOut className="h-5 w-5 mr-3" />
                  <span>Sair</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};