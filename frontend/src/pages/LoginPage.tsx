import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Navigate } from 'react-router-dom';
import { Shield, Moon, Sun } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, loginDev, isAuthenticated, isLoading, error, isDevMode } = useAuth();
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

  const handleDevLogin = async () => {
    try {
      await loginDev();
    } catch (err) {
      console.error('Dev login error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center px-4 sm:px:6 lg:px-8">
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 p-2 rounded-lg bg-gray-700/10 hover:bg-gray-700/20 dark:bg-gray-300/10 dark:hover:bg-gray-300/20 text-gray-700 dark:text-gray-300 transition-colors"
        aria-label="Toggle theme"
      >
        {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
      </button>

      <div className="max-w-md w-full space-y-8">
        {/* Logo and Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-yellow-600 rounded-full flex items-center justify-center mb-6">
            <Shield className="h-8 w-8 text-gray-800" />
          </div>
          <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            Knight
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
            Seu cavaleiro IA
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
              Bem-vindo de volta
            </h2>
            <p className="text-gray-600 dark:text-gray-300">
              Faça login com sua conta Microsoft para continuar
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-800 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Login Button */}
          <button
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center px-4 py-3 border border-transparent rounded-lg shadow-sm text-base font-medium text-gray-800 bg-yellow-600 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-800 mr-2"></div>
                Conectando...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" viewBox="0 0 21 21" fill="none">
                  <rect x="0" y="0" width="10" height="10" fill="#F25022"/>
                  <rect x="11" y="0" width="10" height="10" fill="#00A4EF"/>
                  <rect x="0" y="11" width="10" height="10" fill="#7FBA00"/>
                  <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
                </svg>
                Entrar com Microsoft
              </>
            )}
          </button>

          {/* Developer Mode Button */}
          {isDevMode && (
            <div className="mt-4">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">ou</span>
                </div>
              </div>
              
              <button
                onClick={handleDevLogin}
                disabled={isLoading}
                className="mt-4 w-full flex items-center justify-center px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-base font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-700 dark:border-gray-300 mr-2"></div>
                    Conectando...
                  </>
                ) : (
                  <>
                    <span className="mr-2">👨‍💻</span>
                    Modo Desenvolvedor
                  </>
                )}
              </button>
              
              <p className="mt-2 text-xs text-center text-gray-500 dark:text-gray-400">
                Apenas para desenvolvimento e testes
              </p>
            </div>
          )}

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
          <div className="text-center text-gray-600 dark:text-gray-400">
            <div className="w-8 h-8 bg-yellow-600/20 dark:bg-yellow-600/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Shield size={16} className="text-yellow-600 dark:text-yellow-500" />
            </div>
            <p className="text-sm">Seguro</p>
          </div>
          <div className="text-center text-gray-600 dark:text-gray-400">
            <div className="w-8 h-8 bg-yellow-600/20 dark:bg-yellow-600/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <span className="text-sm font-bold text-yellow-600 dark:text-yellow-500">IA</span>
            </div>
            <p className="text-sm">Inteligente</p>
          </div>
          <div className="text-center text-gray-600 dark:text-gray-400">
            <div className="w-8 h-8 bg-yellow-600/20 dark:bg-yellow-600/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <span className="text-sm text-yellow-600 dark:text-yellow-500">⚡</span>
            </div>
            <p className="text-sm">Rápido</p>
          </div>
        </div>
      </div>
    </div>
  );
};