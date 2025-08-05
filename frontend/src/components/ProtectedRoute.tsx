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
      <div className="min-h-screen flex items-center justify-center px-4 py-8 bg-background relative overflow-hidden">
        {/* Noise effect overlay - same as login */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='500'%3E%3Cfilter id='noise' x='0' y='0'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeBlend mode='screen'/%3E%3C/filter%3E%3Crect width='500' height='500' filter='url(%23noise)' opacity='0.8'/%3E%3C/svg%3E")`,
            mixBlendMode: 'soft-light',
            opacity: 0.3
          }}
        />
        
        {/* Simple smooth vignette - same as login */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at center top, transparent 30%, rgba(0, 0, 0, 0.25) 60%, rgba(0, 0, 0, 0.5) 90%, rgba(0, 0, 0, 0.7) 100%)'
          }}
        />
        
        {/* Loading content */}
        <div className="text-center relative z-10">
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