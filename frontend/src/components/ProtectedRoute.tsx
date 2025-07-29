import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requireAdmin = false }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  // Se está em processo de logout, não fazer redirect
  const isLoggingOut = localStorage.getItem('justLoggedOut');
  
  if (isLoading || isLoggingOut) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-knight-primary mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">
            {isLoggingOut ? 'Saindo...' : 'Carregando...'}
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Verificar se requer admin e o usuário não é admin
  if (requireAdmin && user && !user.is_admin) {
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
};