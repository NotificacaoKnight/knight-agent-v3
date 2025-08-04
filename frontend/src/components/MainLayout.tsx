import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ThemeToggle } from './ThemeToggle';
import { UserAvatar } from './UserAvatar';
import {
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  MessageSquare,
  Plus,
  FileText,
  History,
  ChevronLeft,
  ChevronRight
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
  const [leftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [chatHistorySidebarOpen, setChatHistorySidebarOpen] = useState(false);

  // Auto expand/collapse chat history sidebar based on route
  useEffect(() => {
    const isChatRoute = location.pathname.startsWith('/chat');
    setChatHistorySidebarOpen(isChatRoute);
  }, [location.pathname]);

  // Menu items
  // Menu items dinâmico baseado no status de admin
  const menuItems: SidebarItem[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare, path: '/chat' },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    ...(user?.is_admin ? [{ id: 'documents', label: 'Documentos', icon: FileText, path: '/documents' }] : []),
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
    <div className="h-screen bg-background flex overflow-hidden">
      {/* Left Sidebar - Menu */}
      <div
        className={`${
          leftSidebarOpen ? 'w-16' : 'w-0'
        } sidebar-left transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        <div className="h-full flex flex-col">
          {/* Menu Items */}
          <nav className="pt-8 px-2">
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <div key={item.id} className="mb-8 relative">
                  {/* Indicador curvo na extremidade esquerda */}
                  {isActive && (
                    <div 
                      className="absolute -left-2 top-1/2 transform -translate-y-1/2"
                      style={{
                        animation: 'slideInFromLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards'
                      }}
                    >
                      <svg width="7" height="47" viewBox="0 0 7 47" fill="none">
                        <path 
                          d="M6.4 23.8983C6.4 17.5 0 18.322 0 0V47C0 31.4661 6.4 30.2966 6.4 23.8983Z" 
                          fill="#D09320"
                        />
                      </svg>
                    </div>
                  )}
                  <button
                    onClick={() => handleMenuClick(item.path)}
                    className={`w-8 h-8 flex items-center justify-center rounded-lg relative group mx-auto transition-all duration-300 ${
                      isActive 
                        ? 'shadow-lg' 
                        : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    style={{
                      backgroundColor: isActive ? '#E09D1E' : undefined,
                      animation: isActive ? 'fadeToActive 0.4s ease-out' : undefined
                    }}
                    title={item.label}
                  >
                    <item.icon
                      className={`h-4 w-4 ${
                        isActive
                          ? 'text-white'
                          : 'group-hover:text-white'
                      }`}
                      style={{
                        color: isActive ? 'white' : '#E09D1E'
                      }}
                    />
                    <span className="absolute left-16 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                      {item.label}
                    </span>
                  </button>
                </div>
              );
            })}
          </nav>

          {/* Spacer para empurrar botões para baixo */}
          <div className="flex-1" />

          {/* Bottom Actions */}
          <div className="pb-8">
            {/* User Profile - foto quadrada com cantos arredondados */}
            <div className="px-2 mb-8">
              <button
                onClick={() => navigate('/settings')}
                className="mx-auto block focus:outline-none"
                title={user?.name || user?.email || 'Perfil'}
              >
                <div className="w-8 h-8 rounded-lg overflow-hidden">
                  <UserAvatar user={user || {}} size="sm" className="!rounded-lg w-full h-full" />
                </div>
              </button>
            </div>
            
            {/* Logout */}
            <div className="px-2 mb-8">
              <button
                onClick={logout}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-gray-700 hover:bg-red-600 transition-all group mx-auto"
                title="Sair"
                onMouseEnter={(e) => {
                  const icon = e.currentTarget.querySelector('svg');
                  if (icon) icon.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  const icon = e.currentTarget.querySelector('svg');
                  if (icon) icon.style.color = '#E09D1E';
                }}
              >
                <LogOut 
                  className="h-4 w-4 transition-colors" 
                  style={{ 
                    color: '#E09D1E',
                    transition: 'color 0.3s ease'
                  }}
                />
              </button>
            </div>
            
            {/* Divisória */}
            <div className="mx-3 border-t border-gray-400 dark:border-gray-700 mb-8"></div>
            
            {/* Theme Toggle - sem fundo quadrado */}
            <div className="px-2">
              <div className="w-8 h-8 flex items-center justify-center mx-auto">
                <ThemeToggle />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chat History Sidebar */}
      <div className={`${
        chatHistorySidebarOpen ? 'w-64' : 'w-0'
      } sidebar-right border-r border-border flex-shrink-0 hidden md:block transition-all duration-300 overflow-hidden`}>
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-border">
            <div className="flex items-center">
              <History className="h-4 w-4 text-muted-foreground mr-2" />
              <h2 className="font-semibold text-foreground">Conversas</h2>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => navigate('/chat')}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                title="Nova conversa"
              >
                <Plus className="h-4 w-4 text-muted-foreground" />
              </button>
              <button
                onClick={() => setChatHistorySidebarOpen(false)}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                title="Ocultar histórico"
              >
                <ChevronLeft className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto">
            {chatHistory.map((chat) => (
              <button
                key={chat.id}
                onClick={() => navigate(`/chat/${chat.id}`)}
                className="w-full p-4 text-left hover:bg-muted transition-colors border-b border-border"
              >
                <div className="flex items-start justify-between mb-1">
                  <h3 className="font-medium text-sm text-foreground truncate flex-1">
                    {chat.title}
                  </h3>
                  <span className="text-xs text-muted-foreground ml-2">
                    {formatTimeAgo(chat.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground truncate">
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
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-4">
          <div className="flex items-center">
            {/* Chat History Toggle (show when collapsed) */}
            {!chatHistorySidebarOpen && (
              <button
                onClick={() => setChatHistorySidebarOpen(true)}
                className="hidden md:flex p-2 rounded-lg hover:bg-muted transition-colors items-center mr-2"
                title="Mostrar histórico"
              >
                <History className="h-4 w-4 text-muted-foreground mr-1" />
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
              </button>
            )}
            
            {/* Mobile menu toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg hover:bg-muted transition-colors md:hidden"
            >
              <Menu className="h-5 w-5 text-muted-foreground" />
            </button>

            <h1 className="ml-4 text-xl font-semibold text-foreground">
              Knight
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            
            {/* Right sidebar toggle */}
            <button
              onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <Menu className="h-5 w-5 text-muted-foreground" />
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
        } bg-card border-l border-border transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        <div className="h-full p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-foreground">Informações</h3>
            <button
              onClick={() => setRightSidebarOpen(false)}
              className="p-1 hover:bg-muted rounded transition-colors"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
          
          {/* Placeholder content for right sidebar */}
          <div className="space-y-4">
            <div className="p-3 bg-muted rounded-lg">
              <h4 className="text-sm font-medium text-foreground mb-2">
                Documentos Recentes
              </h4>
              <p className="text-xs text-muted-foreground">
                Nenhum documento carregado
              </p>
            </div>
            
            <div className="p-3 bg-muted rounded-lg">
              <h4 className="text-sm font-medium text-foreground mb-2">
                Estatísticas
              </h4>
              <p className="text-xs text-muted-foreground">
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
          <div className="fixed left-0 top-0 bottom-0 w-64 bg-card shadow-lg">
            <div className="h-full flex flex-col sidebar-left">
              <div className="h-16 px-4 flex items-center justify-between border-b border-border">
                <span className="font-semibold text-foreground">Knight</span>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 hover:bg-muted rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>

              <nav className="pt-8 px-4">
                {menuItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <div key={item.id} className="mb-8 relative">
                      {/* Indicador curvo na extremidade esquerda */}
                      {isActive && (
                        <div 
                          className="absolute -left-4 top-1/2 transform -translate-y-1/2"
                          style={{
                            animation: 'slideInFromLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards'
                          }}
                        >
                          <svg width="7" height="47" viewBox="0 0 7 47" fill="none">
                            <path 
                              d="M6.4 23.8983C6.4 17.5 0 18.322 0 0V47C0 31.4661 6.4 30.2966 6.4 23.8983Z" 
                              fill="#D09320"
                            />
                          </svg>
                        </div>
                      )}
                      <button
                        onClick={() => handleMenuClick(item.path)}
                        className={`w-full h-10 flex items-center px-3 rounded-lg transition-all duration-300 ${
                          isActive 
                            ? 'shadow-lg' 
                            : 'bg-muted hover:bg-muted/80'
                        }`}
                        style={{
                          backgroundColor: isActive ? '#E09D1E' : undefined,
                          animation: isActive ? 'fadeToActive 0.4s ease-out' : undefined
                        }}
                      >
                        <item.icon
                          className={`h-5 w-5 mr-3 ${
                            isActive
                              ? 'text-white'
                              : ''
                          }`}
                          style={{
                            color: isActive ? 'white' : '#E09D1E'
                          }}
                        />
                        <span className={`font-medium text-sm ${
                          isActive
                            ? 'text-white'
                            : 'text-foreground'
                        }`}>
                          {item.label}
                        </span>
                      </button>
                    </div>
                  );
                })}
              </nav>

              {/* Spacer para empurrar botões para baixo */}
              <div className="flex-1" />

              <div className="border-t border-border p-4">
                {/* User Profile - foto quadrada com cantos arredondados */}
                <div className="w-full h-10 flex items-center px-3 mb-8">
                  <button
                    onClick={() => {
                      navigate('/settings');
                      setMobileMenuOpen(false);
                    }}
                    className="mr-3 focus:outline-none"
                  >
                    <div className="w-10 h-10 rounded-lg overflow-hidden">
                      <UserAvatar user={user || {}} size="sm" className="!rounded-lg w-full h-full" />
                    </div>
                  </button>
                  <span className="font-medium text-foreground text-sm">Perfil</span>
                </div>
                
                {/* Logout */}
                <button
                  onClick={logout}
                  className="w-full h-10 flex items-center px-3 rounded-lg bg-muted hover:bg-destructive transition-all mb-8 group"
                  onMouseEnter={(e) => {
                    const icon = e.currentTarget.querySelector('svg');
                    if (icon) icon.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    const icon = e.currentTarget.querySelector('svg');
                    if (icon) icon.style.color = '#E09D1E';
                  }}
                >
                  <LogOut 
                    className="h-5 w-5 mr-3 transition-colors" 
                    style={{ 
                      color: '#E09D1E',
                      transition: 'color 0.3s ease'
                    }}
                  />
                  <span className="font-medium text-muted-foreground text-sm group-hover:text-white transition-colors">Sair</span>
                </button>
                
                {/* Divisória */}
                <div className="border-t border-border mb-8"></div>
                
                {/* Theme Toggle - sem fundo quadrado */}
                <div className="w-full h-10 flex items-center px-3">
                  <div className="mr-3">
                    <ThemeToggle />
                  </div>
                  <span className="font-medium text-muted-foreground text-sm">Tema</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};