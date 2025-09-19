import React, { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * AuthCallback Component
 *
 * This component handles the Azure AD authentication callback.
 * It prevents React Router from interfering with MSAL's redirect processing.
 *
 * The component will:
 * 1. Show a loading state while MSAL processes the authorization code
 * 2. Wait for authentication to complete
 * 3. Redirect to /chat once authenticated
 */
export const AuthCallback: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    console.log('🔄 AuthCallback: Processing Azure AD callback...');
    console.log('🌐 Current URL:', window.location.href);

    // Log URL parameters for debugging
    const urlParams = new URLSearchParams(window.location.search);
    const urlHash = window.location.hash;

    if (urlParams.has('code')) {
      console.log('✅ Authorization code found in URL');
    }
    if (urlParams.has('state')) {
      console.log('✅ State parameter found in URL');
    }
    if (urlParams.has('error')) {
      console.error('❌ Error in callback:', urlParams.get('error'));
      console.error('❌ Error description:', urlParams.get('error_description'));
    }

    // Check hash fragment as well (some configs use fragment response)
    if (urlHash) {
      console.log('🔍 Hash fragment found:', urlHash.substring(0, 50) + '...');
    }
  }, []);

  // If authenticated, redirect to chat
  if (isAuthenticated && !isLoading) {
    console.log('✅ AuthCallback: Authenticated, redirecting to /chat');
    return <Navigate to="/chat" replace />;
  }

  // Show loading state while processing
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8 bg-background relative overflow-hidden">
      {/* Noise effect overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='500'%3E%3Cfilter id='noise' x='0' y='0'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeBlend mode='screen'/%3E%3C/filter%3E%3Crect width='500' height='500' filter='url(%23noise)' opacity='0.8'/%3E%3C/svg%3E")`,
          mixBlendMode: 'soft-light',
          opacity: 0.3
        }}
      />

      {/* Simple smooth vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center top, transparent 30%, rgba(0, 0, 0, 0.25) 60%, rgba(0, 0, 0, 0.5) 90%, rgba(0, 0, 0, 0.7) 100%)'
        }}
      />

      {/* Loading content */}
      <div className="text-center relative z-10">
        <div className="mb-8">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-knight-gold mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-white mb-2">Processando autenticação</h2>
          <p className="text-gray-400">
            Aguarde enquanto validamos suas credenciais com o Azure AD...
          </p>
        </div>

        <div className="text-xs text-gray-500">
          <p>Isso pode levar alguns segundos</p>
          {window.location.search.includes('code') && (
            <p className="mt-2 text-green-400">✓ Código de autorização recebido</p>
          )}
        </div>
      </div>
    </div>
  );
};