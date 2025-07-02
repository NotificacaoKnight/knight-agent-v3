import React, { createContext, useContext, useEffect, useState } from 'react';
import { PublicClientApplication } from '@azure/msal-browser';
import api from '../services/api';

// MSAL configuration
const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_AZURE_CLIENT_ID || 'your-client-id',
    authority: `https://login.microsoftonline.com/${process.env.REACT_APP_AZURE_TENANT_ID || 'your-tenant-id'}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
};

const msalInstance = new PublicClientApplication(msalConfig);

interface User {
  id: string;
  email: string;
  name: string;
  preferred_name?: string;
  profile_picture?: string;
  department?: string;
  job_title?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  loginDev: () => Promise<void>;
  logout: () => void;
  error: string | null;
  isDevMode: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDevMode, setIsDevMode] = useState(false);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Check if user just logged out
        const justLoggedOut = localStorage.getItem('justLoggedOut');
        if (justLoggedOut) {
          localStorage.removeItem('justLoggedOut');
          setIsLoading(false);
          return;
        }
        
        // Check if dev mode is enabled first
        const response = await api.get('/auth/dev/check/');
        setIsDevMode(response.data.dev_mode);
        
        // Check for existing session
        const sessionToken = localStorage.getItem('sessionToken');
        if (sessionToken) {
          try {
            const profileResponse = await api.get('/auth/profile/');
            setUser({
              id: profileResponse.data.id,
              email: profileResponse.data.email,
              name: profileResponse.data.preferred_name || profileResponse.data.first_name,
              preferred_name: profileResponse.data.preferred_name,
              department: profileResponse.data.department,
              job_title: profileResponse.data.job_title,
            });
          } catch (err) {
            // Token inválido, remover
            localStorage.removeItem('sessionToken');
          }
        }
        
        // Try to initialize MSAL, but don't fail if it doesn't work
        try {
          await msalInstance.initialize();
          
          // NÃO verificar automaticamente se há contas MSAL
          // Isso evita login automático após logout
          // O usuário deve clicar no botão de login
        } catch (msalError) {
          console.warn('MSAL initialization failed, but dev mode is still available:', msalError);
          // Don't set error here, let dev mode work
        }
      } catch (err) {
        console.error('Auth initialization failed:', err);
        setError('Falha na inicialização da autenticação');
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const loginRequest = {
        scopes: ['User.Read'],
        prompt: 'select_account',
      };

      const response = await msalInstance.loginPopup(loginRequest);
      
      if (response.account) {
        // Enviar token ao backend para criar sessão
        const backendResponse = await api.post('/auth/microsoft/token/', {
          access_token: response.accessToken
        });
        
        // Salvar token da sessão
        localStorage.setItem('sessionToken', backendResponse.data.session_token);
        
        setUser({
          id: backendResponse.data.user.id,
          email: backendResponse.data.user.email,
          name: backendResponse.data.user.preferred_name || backendResponse.data.user.first_name,
          preferred_name: backendResponse.data.user.preferred_name,
          department: backendResponse.data.user.department,
          job_title: backendResponse.data.user.job_title,
        });
      }
    } catch (err: any) {
      console.error('Login failed:', err);
      setError('Falha no login. Tente novamente.');
    } finally {
      setIsLoading(false);
    }
  };

  const loginDev = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await api.post('/auth/dev/login/', {});
      
      // Save session token
      localStorage.setItem('sessionToken', response.data.session_token);
      
      setUser({
        id: response.data.user.id,
        email: response.data.user.email,
        name: response.data.user.preferred_name || response.data.user.first_name,
        preferred_name: response.data.user.preferred_name,
        department: response.data.user.department,
        job_title: response.data.user.job_title,
      });
    } catch (err: any) {
      console.error('Dev login failed:', err);
      setError(err.response?.data?.error || 'Falha no login de desenvolvedor');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Marcar que o usuário fez logout e está em processo de logout
      localStorage.setItem('justLoggedOut', 'true');
      setIsLoading(true); // Mostrar loading durante logout
      
      // Limpar dados locais imediatamente
      localStorage.removeItem('sessionToken');
      setUser(null);
      
      // Logout do backend em background (não esperar)
      const sessionToken = localStorage.getItem('sessionToken');
      if (sessionToken) {
        api.post('/auth/logout/', {}).catch(err => 
          console.error('Backend logout error:', err)
        );
      }
      
      // Se não for dev mode, fazer logout do MSAL
      if (!isDevMode) {
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          try {
            // Limpar cache localmente
            await msalInstance.clearCache();
            
            // Remover todas as contas localmente
            for (const account of accounts) {
              msalInstance.setActiveAccount(null);
            }
          } catch (error) {
            console.error('Error clearing MSAL cache:', error);
          }
        }
      }
      
      // Sempre redirecionar para login após limpar tudo
      setTimeout(() => {
        window.location.replace('/login');
      }, 100); // Pequeno delay para garantir que tudo foi limpo
    } catch (err) {
      console.error('Logout error:', err);
      // Em caso de erro, limpar tudo e redirecionar
      localStorage.removeItem('sessionToken');
      setUser(null);
      window.location.href = '/login';
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    loginDev,
    logout,
    error,
    isDevMode,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};