import React, { createContext, useContext, useEffect, useState, useRef, useCallback, useMemo } from 'react';
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

// Inicializar MSAL uma única vez no módulo
let msalInitialized = false;
const initializeMsal = async () => {
  if (!msalInitialized) {
    console.log('🔧 Inicializando MSAL...', {
      clientId: msalConfig.auth.clientId,
      authority: msalConfig.auth.authority
    });
    await msalInstance.initialize();
    msalInitialized = true;
    console.log('🚀 MSAL inicializado globalmente');
  } else {
    console.log('✅ MSAL já está inicializado');
  }
};

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
  logout: () => void;
  error: string | null;
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
  const isInitialized = useRef(false);

  const fetchUserProfile = useCallback(async () => {
    console.log('🔍 Buscando perfil do usuário...');
    try {
      const profileResponse = await api.get('/auth/profile/');
      setUser({
        id: profileResponse.data.id,
        email: profileResponse.data.email,
        name: profileResponse.data.preferred_name || profileResponse.data.first_name,
        preferred_name: profileResponse.data.preferred_name,
        profile_picture: profileResponse.data.profile_picture,
        department: profileResponse.data.department,
        job_title: profileResponse.data.job_title,
      });
      console.log('✅ Perfil carregado com sucesso');
    } catch (err) {
      console.log('❌ Token inválido, removendo...');
      localStorage.removeItem('sessionToken');
      throw err;
    }
  }, []);

  useEffect(() => {
    // Prevenir execução múltipla (StrictMode protection)
    if (isInitialized.current) {
      console.log('⚠️ AuthContext já foi inicializado, ignorando...');
      return;
    }
    
    const initializeAuth = async () => {
      console.log('🚀 Inicializando AuthContext...');
      isInitialized.current = true;
      
      try {
        // Check if user just logged out
        const justLoggedOut = localStorage.getItem('justLoggedOut');
        if (justLoggedOut) {
          console.log('👋 Usuário acabou de fazer logout');
          localStorage.removeItem('justLoggedOut');
          setIsLoading(false);
          return;
        }
        
        // Check for existing session
        const sessionToken = localStorage.getItem('sessionToken');
        if (sessionToken) {
          console.log('🔑 Token encontrado, carregando perfil...');
          await fetchUserProfile();
        } else {
          console.log('🔒 Nenhum token encontrado');
        }
        
        // Initialize MSAL
        await initializeMsal();
        
      } catch (err) {
        console.error('Auth initialization failed:', err);
        setError('Falha na inicialização da autenticação');
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [fetchUserProfile]); // Incluir fetchUserProfile na dependência

  const login = useCallback(async () => {
    console.log('🔐 Iniciando login...');
    try {
      setIsLoading(true);
      setError(null);

      // Garantir que MSAL está inicializado
      if (!msalInstance.getConfiguration().auth.clientId || msalInstance.getConfiguration().auth.clientId === 'your-client-id') {
        throw new Error('MSAL não está configurado corretamente');
      }

      // Garantir que está inicializado
      await initializeMsal();

      const loginRequest = {
        scopes: ['User.Read', 'User.ReadBasic.All'],
        prompt: 'select_account',
      };

      const response = await msalInstance.loginPopup(loginRequest);
      
      if (response.account) {
        console.log('✅ Login MSAL bem-sucedido, enviando para backend...');
        
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
          profile_picture: backendResponse.data.user.profile_picture,
          department: backendResponse.data.user.department,
          job_title: backendResponse.data.user.job_title,
        });
        
        console.log('✅ Login completo!');
      }
    } catch (err: any) {
      console.error('Login failed:', err);
      setError('Falha no login. Tente novamente.');
    } finally {
      setIsLoading(false);
    }
  }, []);


  const logout = useCallback(async () => {
    console.log('👋 Iniciando logout...');
    try {
      // Obter token antes de remover
      const sessionToken = localStorage.getItem('sessionToken');
      
      // Marcar que o usuário fez logout
      localStorage.setItem('justLoggedOut', 'true');
      setIsLoading(true);
      
      // Limpar dados locais imediatamente
      localStorage.removeItem('sessionToken');
      setUser(null);
      
      // Logout do backend em background (não esperar)
      if (sessionToken) {
        api.post('/auth/logout/', {}).catch(err => 
          console.error('Backend logout error:', err)
        );
      }
      
      // Fazer logout do MSAL
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        try {
          await msalInstance.clearCache();
          msalInstance.setActiveAccount(null);
        } catch (error) {
          console.error('Error clearing MSAL cache:', error);
        }
      }
      
      // Reset do flag de inicialização para permitir novo login
      isInitialized.current = false;
      
      // Redirecionar para login
      setTimeout(() => {
        window.location.replace('/login');
      }, 100);
    } catch (err) {
      console.error('Logout error:', err);
      localStorage.removeItem('sessionToken');
      setUser(null);
      isInitialized.current = false;
      window.location.href = '/login';
    }
  }, []);

  const value: AuthContextType = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    error,
  }), [user, isLoading, login, logout, error]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};