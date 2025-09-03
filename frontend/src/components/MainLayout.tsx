import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ThemeToggle } from './ThemeToggle';
import { UserAvatar } from './UserAvatar';
import { chatApi } from '../services/api';
import { useChatContext } from '../context/ChatContext';
import { toast as sonnerToast } from 'sonner';
import { emitChatSessionDeleted } from '../utils/events';
import { DeleteChatModal } from './DeleteChatModal';
import { KnightIcon } from './KnightIcon';
import { LLMStatusIndicator, LLMStatusIndicatorRef } from './LLMStatusIndicator';
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
  ChevronRight,
  Trash2,
  Bell,
  VenetianMask,
  Wand
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
  title?: string;
  subtitle?: string;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, title, subtitle }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { chatSessions, refreshChatSessions, isProcessingMessage, setIsProcessingMessage } = useChatContext();
  const [leftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [chatHistorySidebarOpen, setChatHistorySidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const llmStatusRef = useRef<LLMStatusIndicatorRef>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<{id: string, title: string} | null>(null);

  // Auto expand/collapse sidebars based on route
  useEffect(() => {
    const isChatRoute = location.pathname.startsWith('/chat');
    setChatHistorySidebarOpen(isChatRoute);
    setRightSidebarOpen(isChatRoute);
  }, [location.pathname]);

  // Load chat sessions only once when entering chat area
  useEffect(() => {
    const loadChatSessions = async () => {
      if (location.pathname.startsWith('/chat') && user && chatSessions.length === 0) {
        setLoading(true);
        try {
          await refreshChatSessions();
        } catch (error) {
          console.error('Erro ao carregar sessões de chat:', error);
        } finally {
          setLoading(false);
        }
      }
    };

    if (!loading) {
      loadChatSessions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, user]);

  const confirmDeleteSession = async (sessionId: string) => {
    setDeletingSessionId(sessionId);
    
    try {
      await chatApi.deleteSession(sessionId);
      await refreshChatSessions();
      
      // Emit event first
      emitChatSessionDeleted(sessionId);
      
      // If we're currently viewing the deleted session, navigate to chat home
      const currentSessionId = location.pathname.split('/chat/')[1];
      if (currentSessionId === sessionId) {
        navigate('/chat');
      }
      
      sonnerToast.success('Conversa excluída com sucesso', {
        description: 'A conversa foi removida permanentemente',
        icon: '✅'
      });
    } catch (error) {
      console.error('Erro ao excluir sessão:', error);
      sonnerToast.error('Erro ao excluir conversa', {
        description: 'Tente novamente em alguns momentos',
        icon: '❌'
      });
    } finally {
      setDeletingSessionId(null);
    }
  };

  const openDeleteModal = (sessionId: string, sessionTitle: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent navigation when clicking delete button
    setSessionToDelete({id: sessionId, title: sessionTitle});
    setDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    setDeleteModalOpen(false);
    setSessionToDelete(null);
  };

  // Menu items
  // Menu items dinâmico baseado no status de admin
  const menuItems: SidebarItem[] = [
    { id: 'chat', label: '⚔️ Knight - Chat', icon: MessageSquare, path: '/chat' },
    { id: 'bard', label: '🎭 Bard - Relatórios', icon: VenetianMask, path: '/bard' },
    { id: 'wizard', label: '🧙 Wizard - Capacitações', icon: Wand, path: '/wizard' },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, path: '/dashboard' },
    ...(user?.is_admin ? [{ id: 'documents', label: 'Documentos', icon: FileText, path: '/documents' }] : []),
    { id: 'settings', label: 'Configurações', icon: Settings, path: '/settings' },
  ];

  // Convert chat sessions to chat history format
  const chatHistory: ChatHistory[] = chatSessions.map(session => ({
    id: session.id,
    title: session.title || `Chat ${session.id}`,
    timestamp: new Date(session.last_message_at || session.created_at),
    preview: `${session.message_count} mensagens`
  }));

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
        } menu-background border-r border-border transition-all duration-[900ms] ease-out overflow-hidden flex-shrink-0`}
        style={{
          transitionTimingFunction: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
          transitionProperty: 'width, background-color'
        }}
      >
        <div className="h-full flex flex-col">
          {/* Menu Items */}
          <nav className="pt-5 px-2">
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
                          className="menu-indicator"
                          d="M6.4 23.8983C6.4 17.5 0 18.322 0 0V47C0 31.4661 6.4 30.2966 6.4 23.8983Z"
                        />
                      </svg>
                    </div>
                  )}
                  <button
                    onClick={() => handleMenuClick(item.path)}
                    className={`w-8 h-8 flex items-center justify-center rounded-lg relative group mx-auto transition-all duration-300 ${
                      isActive 
                        ? 'shadow-lg' 
                        : 'menu-button'
                    }`}
                    style={{
                      backgroundColor: isActive ? 'rgb(var(--menu-indicator))' : undefined
                    }}
                    title={item.label}
                  >
                    <item.icon
                      className={`h-4 w-4 ${
                        isActive
                          ? 'text-white'
                          : 'menu-icon'
                      }`}
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
                className="w-8 h-8 flex items-center justify-center rounded-lg menu-button hover:bg-red-600 transition-all group mx-auto"
                title="Sair"
                onMouseEnter={(e) => {
                  const icon = e.currentTarget.querySelector('svg');
                  if (icon) icon.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  const icon = e.currentTarget.querySelector('svg');
                  if (icon) icon.style.color = '';
                }}
              >
                <LogOut 
                  className="h-4 w-4 menu-icon transition-colors"
                />
              </button>
            </div>
            
            {/* Divisória */}
            <div className="border-t border-border mb-8"></div>
            
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
      <div 
        className={`${
          chatHistorySidebarOpen ? 'w-64' : 'w-0'
        } sidebar-right border-r border-border flex-shrink-0 hidden md:block transition-all duration-[900ms] ease-out overflow-hidden`}
        style={{
          transitionTimingFunction: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
          transitionProperty: 'width, background-color'
        }}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-border">
            <h2 className="font-semibold text-foreground">Histórico</h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  console.log('🔴 Nova conversa clicked!', {
                    isProcessingMessage,
                    currentPath: location.pathname,
                    timestamp: new Date().toISOString()
                  });
                  setIsProcessingMessage(false);
                  console.log('🟢 About to navigate to /chat', 'Current path:', location.pathname);
                  
                  // Force reset by navigating to a temporary route then back
                  if (location.pathname === '/chat' || location.pathname.startsWith('/chat/')) {
                    console.log('🔄 Already on chat route, forcing reset...');
                    // Navigate to root temporarily, then immediately back to chat to force reset
                    navigate('/', { replace: true });
                    setTimeout(() => {
                      navigate('/chat', { replace: true });
                    }, 10);
                  } else {
                    navigate('/chat', { replace: true });
                    console.log('🟡 Navigate call completed');
                  }
                }}
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
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {loading ? (
              <div className="p-4 text-center">
                <span className="text-sm text-muted-foreground">Carregando conversas...</span>
              </div>
            ) : chatHistory.length === 0 ? (
              <div className="p-4 text-center">
                <span className="text-sm text-muted-foreground">Nenhuma conversa encontrada</span>
              </div>
            ) : (
              chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  className={`relative group transition-colors border-b border-border ${
                    isProcessingMessage ? 'opacity-50' : ''
                  }`}
                >
                  <button
                    onClick={() => {
                      if (!isProcessingMessage) {
                        navigate(`/chat/${chat.id}`);
                      }
                    }}
                    disabled={isProcessingMessage}
                    className={`w-full p-4 text-left transition-colors ${
                      !isProcessingMessage ? 'hover:bg-muted' : 'cursor-not-allowed'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <h3 className="font-medium text-sm text-foreground truncate flex-1 pr-2">
                        {chat.title}
                      </h3>
                      <span className="text-xs text-muted-foreground ml-2 shrink-0">
                        {formatTimeAgo(chat.timestamp)}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {chat.preview}
                    </p>
                  </button>
                  
                  {/* Delete Button */}
                  <button
                    onClick={(e) => openDeleteModal(chat.id, chat.title, e)}
                    disabled={isProcessingMessage || deletingSessionId === chat.id}
                    className={`absolute bottom-2 right-2 p-1 rounded-md transition-all duration-200 ${
                      isProcessingMessage || deletingSessionId === chat.id
                        ? 'opacity-50 cursor-not-allowed'
                        : 'opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400'
                    }`}
                    title="Excluir conversa"
                  >
                    {deletingSessionId === chat.id ? (
                      <div className="w-3 h-3 border border-red-500 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Trash2 className="w-3 h-3" />
                    )}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="h-16 bg-background border-b border-border flex items-center justify-between px-4">
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

            <div className="ml-4 flex items-center space-x-3">
              {/* Mostrar logo apenas no chat */}
              {location.pathname.startsWith('/chat') ? (
                <>
                  <KnightIcon className="h-10 w-10 text-foreground" />
                  <h1 className="text-xl font-semibold text-foreground">
                    Knight
                  </h1>
                </>
              ) : (
                /* Mostrar título e subtítulo nas outras páginas */
                <div className="flex items-center">
                  <h1 className="text-xl font-semibold text-foreground">
                    {title || 'Knight'}
                  </h1>
                  {subtitle && (
                    <>
                      <span className="mx-3 text-muted-foreground">|</span>
                      <span className="text-lg text-muted-foreground">
                        {subtitle}
                      </span>
                    </>
                  )}
                </div>
              )}
              
              {/* LLM Status Indicator - Apenas para admins */}
              <LLMStatusIndicator ref={llmStatusRef} />
            </div>
          </div>

          <div className="flex items-center space-x-4">
            
            {/* Right sidebar toggle */}
            <button
              onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <Bell className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-hidden bg-background">
          {children}
        </div>
      </div>

      {/* Right Sidebar - Collapsible */}
      <div
        className={`${
          rightSidebarOpen ? 'w-64' : 'w-0'
        } sidebar-right border-l border-border transition-all duration-[900ms] ease-out overflow-hidden flex-shrink-0`}
        style={{
          transitionTimingFunction: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
          transitionProperty: 'width, background-color'
        }}
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
            <div className="h-full flex flex-col menu-background">
              <div className="h-16 px-4 flex items-center justify-between border-b border-border">
                <div className="flex items-center space-x-2">
                  <KnightIcon className="h-7 w-7 text-foreground" />
                  <span className="font-semibold text-foreground">Knight</span>
                </div>
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
                              className="menu-indicator"
                              d="M6.4 23.8983C6.4 17.5 0 18.322 0 0V47C0 31.4661 6.4 30.2966 6.4 23.8983Z"
                            />
                          </svg>
                        </div>
                      )}
                      <button
                        onClick={() => handleMenuClick(item.path)}
                        className={`w-full h-10 flex items-center px-3 rounded-lg transition-all duration-300 ${
                          isActive 
                            ? 'shadow-lg' 
                            : 'menu-button'
                        }`}
                        style={{
                          backgroundColor: isActive ? 'rgb(var(--menu-indicator))' : undefined
                        }}
                      >
                        <item.icon
                          className={`h-5 w-5 mr-3 ${
                            isActive
                              ? 'text-white'
                              : 'menu-icon'
                          }`}
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
                  className="w-full h-10 flex items-center px-3 rounded-lg menu-button hover:bg-destructive transition-all mb-8 group"
                  onMouseEnter={(e) => {
                    const icon = e.currentTarget.querySelector('svg');
                    if (icon) icon.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    const icon = e.currentTarget.querySelector('svg');
                    if (icon) icon.style.color = '';
                  }}
                >
                  <LogOut 
                    className="h-5 w-5 mr-3 menu-icon transition-colors"
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

      {/* Delete Confirmation Modal */}
      <DeleteChatModal
        isOpen={deleteModalOpen}
        chatTitle={sessionToDelete?.title || ''}
        isDeleting={deletingSessionId === sessionToDelete?.id}
        onConfirm={() => {
          if (sessionToDelete) {
            confirmDeleteSession(sessionToDelete.id);
            closeDeleteModal();
          }
        }}
        onCancel={closeDeleteModal}
      />
    </div>
  );
};