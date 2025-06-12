import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Navigate } from 'react-router-dom';
import { Shield, Moon, Sun } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading, error } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleLogin = async () => {
    try {
      await login();
    } catch (err) {
      console.error('Login error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-knight-primary to-knight-secondary flex items-center justify-center px-4 sm:px-6 lg:px-8">
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
        aria-label="Toggle theme"
      >
        {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
      </button>

      <div className="max-w-md w-full space-y-8">
        {/* Logo and Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-white rounded-full flex items-center justify-center mb-6">
            <Shield className="h-8 w-8 text-knight-primary" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">
            🏰 Knight Agent
          </h1>
          <p className="text-xl text-blue-100 mb-8">
            Assistente IA Corporativo
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
              Bem-vindo de volta
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Faça login com sua conta Microsoft para continuar
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Login Button */}
          <button
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center px-4 py-3 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-knight-primary hover:bg-knight-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-knight-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Conectando...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.64 12.204c0-1.39-.118-2.724-.338-4.008H12.24v7.581h6.416c-.275 1.49-1.11 2.751-2.364 3.595v2.994h3.834c2.24-2.064 3.534-5.1 3.534-8.662z"/>
                  <path d="M12.24 24c3.195 0 5.87-1.062 7.826-2.874l-3.834-2.994c-1.058.714-2.412 1.134-3.992 1.134-3.07 0-5.67-2.076-6.596-4.866H1.758v3.09C3.708 21.348 7.563 24 12.24 24z"/>
                  <path d="M5.644 14.4c-.24-.714-.378-1.476-.378-2.4s.138-1.686.378-2.4V6.51H1.758C.642 8.718 0 10.296 0 12s.642 3.282 1.758 5.49l3.886-3.09z"/>
                  <path d="M12.24 4.734c1.734 0 3.294.594 4.518 1.764l3.39-3.39C18.105 1.19 15.43 0 12.24 0 7.563 0 3.708 2.652 1.758 6.51l3.886 3.09c.926-2.79 3.526-4.866 6.596-4.866z"/>
                </svg>
                Entrar com Microsoft
              </>
            )}
          </button>

          {/* Info */}
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Ao fazer login, você concorda com os termos de uso da empresa.
              <br />
              Para suporte, entre em contato com o RH.
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
          <div className="text-center text-white/80">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Shield size={16} />
            </div>
            <p className="text-sm">Seguro</p>
          </div>
          <div className="text-center text-white/80">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <span className="text-sm font-bold">IA</span>
            </div>
            <p className="text-sm">Inteligente</p>
          </div>
          <div className="text-center text-white/80">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <span className="text-sm">⚡</span>
            </div>
            <p className="text-sm">Rápido</p>
          </div>
        </div>
      </div>
    </div>
  );
};