import React, { createContext, useContext, useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { PublicClientApplication, Configuration } from '@azure/msal-browser';
import api from '../services/api';

// MSAL instance will be initialized after fetching config from backend
let msalInstance: PublicClientApplication | null = null;
let authConfig: any = null;

// Fetch authentication config from backend
const fetchAuthConfig = async () => {
  try {
    const response = await api.get('/auth/config');
    authConfig = response.data;
    return authConfig;
  } catch (error) {
    console.error('❌ Failed to fetch auth config:', error);
    // Fallback to environment variables if backend is not available
    return {
      azure_ad: {
        client_id: process.env.REACT_APP_AZURE_CLIENT_ID || '',
        tenant_id: process.env.REACT_APP_AZURE_TENANT_ID || '',
        authority: `https://login.microsoftonline.com/${process.env.REACT_APP_AZURE_TENANT_ID || ''}`,
        redirect_uri: window.location.origin
      }
    };
  }
};

// Initialize MSAL with config from backend
let msalInitialized = false;
let msalInitializationPromise: Promise<void> | null = null;

const initializeMsal = async () => {
  if (msalInitializationPromise) {
    return msalInitializationPromise;
  }

  if (!msalInitialized) {
    msalInitializationPromise = (async () => {
      // Fetch config if not already fetched
      if (!authConfig) {
        authConfig = await fetchAuthConfig();
      }

      // Create MSAL configuration
      const msalConfig: Configuration = {
        auth: {
          clientId: authConfig.azure_ad.client_id,
          authority: authConfig.azure_ad.authority,
          redirectUri: window.location.origin,
          postLogoutRedirectUri: window.location.origin,
          navigateToLoginRequestUrl: true,
        },
        cache: {
          cacheLocation: 'localStorage',
          storeAuthStateInCookie: true,
        }
      };

      console.log('🔧 Inicializando MSAL com configuração do backend...');
      console.log('🔍 Client ID:', authConfig.azure_ad.client_id);
      console.log('🔍 Tenant ID:', authConfig.azure_ad.tenant_id);
      console.log('🔍 Authority:', authConfig.azure_ad.authority);

      // Create and initialize MSAL instance
      msalInstance = new PublicClientApplication(msalConfig);
      await msalInstance.initialize();

      msalInitialized = true;
      console.log('🚀 MSAL inicializado com sucesso');
    })();

    return msalInitializationPromise;
  } else {
    console.log('✅ MSAL já está inicializado');
    return Promise.resolve();
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
  is_admin?: boolean;
  preferred_language?: string;
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

// HttpOnly cookies são gerenciados automaticamente pelo navegador

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialized = useRef(false);

  const fetchUserProfile = useCallback(async () => {
    console.log('🔍 Buscando perfil do usuário...');
    try {
      const profileResponse = await api.get('/auth/me');
      setUser({
        id: profileResponse.data.id,
        email: profileResponse.data.email,
        name: profileResponse.data.preferred_name || profileResponse.data.display_name || profileResponse.data.first_name || 'Usuário',
        preferred_name: profileResponse.data.preferred_name,
        profile_picture: profileResponse.data.profile_picture,
        department: profileResponse.data.department,
        job_title: profileResponse.data.job_title,
        is_admin: profileResponse.data.is_admin || false,
        preferred_language: profileResponse.data.preferred_language,
      });
      console.log('✅ Perfil carregado com sucesso');
    } catch (err) {
      console.log('❌ Não autenticado ou token inválido');
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
      console.log('📍 Current URL:', window.location.href);
      console.log('🔗 Redirect URI configurado:', window.location.origin);
      isInitialized.current = true;

      try {
        // Initialize MSAL first (will fetch config if needed)
        await initializeMsal();

        if (!msalInstance) {
          throw new Error('MSAL instance not initialized');
        }

        // Handle redirect response from Microsoft
        console.log('🔍 Verificando retorno do redirect...');

        // Verificar se há um código de autorização na URL (indicando retorno do Azure AD)
        const urlParams = new URLSearchParams(window.location.search);
        const urlHash = window.location.hash;
        const hasAuthCode = urlParams.has('code') || urlHash.includes('code=');
        const hasError = urlParams.has('error') || urlHash.includes('error=');
        const hasState = urlParams.has('state') || urlHash.includes('state=');

        console.log('🔐 URL tem código de autorização?', hasAuthCode);
        console.log('📝 URL tem state?', hasState);
        console.log('❌ URL tem erro?', hasError);
        console.log('🌐 URL completa:', window.location.href);

        if (hasError) {
          const error = urlParams.get('error') || new URLSearchParams(urlHash.replace('#', '')).get('error');
          const errorDescription = urlParams.get('error_description') || new URLSearchParams(urlHash.replace('#', '')).get('error_description');
          console.error('❌ Erro de autenticação:', error, errorDescription);
          setError(`Erro de autenticação: ${error} - ${errorDescription}`);
          setIsLoading(false);
          return;
        }

        try {
          // IMPORTANTE: handleRedirectPromise deve ser chamado sempre, mesmo sem código na URL
          const redirectResponse = await msalInstance!.handleRedirectPromise();
          console.log('📋 Redirect response:', redirectResponse);

          // Verificar se há contas logadas
          const accounts = msalInstance!.getAllAccounts();
          console.log('👥 Contas encontradas:', accounts);

          if (redirectResponse && redirectResponse.accessToken) {
            console.log('📥 Processando retorno do redirect Microsoft...');
            console.log('🔑 Access Token recebido:', redirectResponse.accessToken.substring(0, 20) + '...');
            console.log('🔍 Access Token length:', redirectResponse.accessToken.length);
            console.log('🔍 Access Token segments:', redirectResponse.accessToken.split('.').length);

            // Check if ID token is available (SECURE authentication method)
            let backendResponse;
            if (redirectResponse.idToken) {
              console.log('🔐 ID Token disponível - usando método SEGURO');
              console.log('🔑 ID Token recebido:', redirectResponse.idToken.substring(0, 20) + '...');
              console.log('🔍 ID Token length:', redirectResponse.idToken.length);
              console.log('🔍 ID Token segments:', redirectResponse.idToken.split('.').length);

              // Use the SECURE ID token endpoint
              backendResponse = await api.post('/auth/microsoft/id-token', {
                id_token: redirectResponse.idToken,
                access_token: redirectResponse.accessToken
              });
              console.log('✅ Autenticação SEGURA com ID Token realizada');
            } else {
              console.log('⚠️ ID Token não disponível - usando método de fallback');

              // Primeiro, vamos debugar o token para entender o que estamos recebendo
              try {
                const debugResponse = await api.post('/auth/debug-token', {
                  access_token: redirectResponse.accessToken
                });
                console.log('🔍 DEBUG - Token info:', debugResponse.data);
              } catch (debugError) {
                console.error('Debug endpoint error:', debugError);
              }

              // Fallback to access token only (less secure)
              backendResponse = await api.post('/auth/microsoft/token', {
                access_token: redirectResponse.accessToken
              });
              console.log('⚠️ Usando método de fallback (menos seguro)');
            }

            console.log('✅ Resposta do backend recebida, cookie JWT definido automaticamente');

            // Tokens agora são gerenciados via HttpOnly cookies pelo backend
            // Não salvamos mais no localStorage por segurança
            console.log('🔐 Usando HttpOnly cookies para tokens (mais seguro)');

            setUser({
              id: backendResponse.data.user.id,
              email: backendResponse.data.user.email,
              name: backendResponse.data.user.preferred_name || backendResponse.data.user.display_name || backendResponse.data.user.first_name || 'Usuário',
              preferred_name: backendResponse.data.user.preferred_name,
              profile_picture: backendResponse.data.user.profile_picture,
              department: backendResponse.data.user.department,
              job_title: backendResponse.data.user.job_title,
              is_admin: backendResponse.data.user.is_admin || false,
              preferred_language: backendResponse.data.user.preferred_language,
            });

            // Limpar URL após processar o código e redirecionar para página principal
            window.history.replaceState({}, document.title, '/');

            console.log('✅ Login via redirect completo!');
            setIsLoading(false);
            return;
        }

        // Se houver uma conta mas não há redirectResponse, tentar obter token silenciosamente
        if (accounts.length > 0 && !hasAuthCode) {
          console.log('🔄 Tentando obter token silenciosamente...');
          console.log('👤 Conta ativa:', accounts[0].username);

          // Set active account first
          msalInstance!.setActiveAccount(accounts[0]);

          const silentRequest = {
            scopes: ['User.Read', 'User.ReadBasic.All', 'openid', 'profile', 'email'],
            account: accounts[0],
            forceRefresh: false, // Try cached token first
          };

          try {
            const silentResponse = await msalInstance!.acquireTokenSilent(silentRequest);
            if (silentResponse && silentResponse.accessToken) {
              console.log('📥 Token obtido silenciosamente, processando...');
              console.log('🔍 Silent Access Token length:', silentResponse.accessToken.length);
              console.log('🔍 Silent Access Token segments:', silentResponse.accessToken.split('.').length);

              // Check if ID token is available in silent response (SECURE authentication method)
              let backendResponse;
              if (silentResponse.idToken) {
                console.log('🔐 ID Token disponível no silent login - usando método SEGURO');
                console.log('🔍 Silent ID Token length:', silentResponse.idToken.length);
                console.log('🔍 Silent ID Token segments:', silentResponse.idToken.split('.').length);

                // Use the SECURE ID token endpoint
                backendResponse = await api.post('/auth/microsoft/id-token', {
                  id_token: silentResponse.idToken,
                  access_token: silentResponse.accessToken
                });
                console.log('✅ Silent login SEGURO com ID Token realizado');
              } else {
                console.log('⚠️ ID Token não disponível no silent login - usando método de fallback');

                // Debug do token silencioso também
                try {
                  const debugResponse = await api.post('/auth/debug-token', {
                    access_token: silentResponse.accessToken
                  });
                  console.log('🔍 DEBUG - Silent token info:', debugResponse.data);
                } catch (debugError) {
                  console.error('Debug endpoint error (silent):', debugError);
                }

                // Fallback to access token only (less secure)
                backendResponse = await api.post('/auth/microsoft/token', {
                  access_token: silentResponse.accessToken
                });
                console.log('⚠️ Silent login usando método de fallback (menos seguro)');
              }

              // Tokens agora são gerenciados via HttpOnly cookies pelo backend
              // Não salvamos mais no localStorage por segurança
              console.log('🔐 Usando HttpOnly cookies para tokens (silent login - mais seguro)');

              setUser({
                id: backendResponse.data.user.id,
                email: backendResponse.data.user.email,
                name: backendResponse.data.user.preferred_name || backendResponse.data.user.display_name || backendResponse.data.user.first_name || 'Usuário',
                preferred_name: backendResponse.data.user.preferred_name,
                profile_picture: backendResponse.data.user.profile_picture,
                department: backendResponse.data.user.department,
                job_title: backendResponse.data.user.job_title,
                is_admin: backendResponse.data.user.is_admin || false,
                preferred_language: backendResponse.data.user.preferred_language,
              });

              // Limpar URL se houver parâmetros de auth
              if (window.location.search || window.location.hash) {
                window.history.replaceState({}, document.title, window.location.pathname);
              }

              console.log('✅ Login silencioso completo!');
              setIsLoading(false);
              return;
            }
          } catch (silentError) {
            console.log('⚠️ Token silencioso falhou:', silentError);
            console.log('🔄 Usuário precisa fazer login manualmente');
          }
        }

        // Se temos código de autorização mas handleRedirectPromise retornou null, pode ser um problema de timing
        if (hasAuthCode && !redirectResponse) {
          console.log('⚠️ Código de autorização presente mas redirect response é null');
          console.log('🔄 Tentando processar redirect novamente...');

          // Wait a bit and try again
          await new Promise(resolve => setTimeout(resolve, 1000));

          try {
            const retryResponse = await msalInstance!.handleRedirectPromise();
            if (retryResponse && retryResponse.accessToken) {
              console.log('📥 Retry bem-sucedido, processando token...');

              // Process the token (same as above)
              const backendResponse = await api.post('/auth/microsoft/token', {
                access_token: retryResponse.accessToken
              });

              setUser({
                id: backendResponse.data.user.id,
                email: backendResponse.data.user.email,
                name: backendResponse.data.user.preferred_name || backendResponse.data.user.display_name || backendResponse.data.user.first_name || 'Usuário',
                preferred_name: backendResponse.data.user.preferred_name,
                profile_picture: backendResponse.data.user.profile_picture,
                department: backendResponse.data.user.department,
                job_title: backendResponse.data.user.job_title,
                is_admin: backendResponse.data.user.is_admin || false,
                preferred_language: backendResponse.data.user.preferred_language,
              });

              window.history.replaceState({}, document.title, '/');
              console.log('✅ Login via retry completo!');
              setIsLoading(false);
              return;
            }
          } catch (retryError) {
            console.error('❌ Retry também falhou:', retryError);
          }
        }
        } catch (redirectError) {
          console.error('❌ Erro ao processar redirect:', redirectError);
        }

        // Check for existing session via HTTP-only cookie
        console.log('🔍 Verificando autenticação via cookie...');
        try {
          await fetchUserProfile();
          console.log('✅ Usuário autenticado via cookie');
        } catch (err) {
          console.log('🔒 Usuário não autenticado');
        }
        
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
    console.log('🔗 Redirect URI para login:', window.location.origin);

    try {
      setIsLoading(true);
      setError(null);

      // Garantir que MSAL está inicializado
      if (!msalInstance) {
        throw new Error('MSAL não está inicializado. Tente novamente.');
      }

      // Garantir que está inicializado
      await initializeMsal();

      const loginRequest = {
        scopes: ['User.Read', 'User.ReadBasic.All', 'openid', 'profile', 'email'],
        prompt: 'select_account',
        redirectUri: window.location.origin,
        state: Math.random().toString(36).substring(7), // Add state for CSRF protection
        extraScopesToConsent: ['openid', 'profile', 'email'], // Ensure these scopes are consented
      };

      console.log('📤 Configuração de login:', loginRequest);

      // Usar redirect em vez de popup para evitar problemas de COOP
      await msalInstance!.loginRedirect(loginRequest);
      // A página será redirecionada - o código não continua daqui
      console.log('🔄 Redirecionando para Microsoft login...');
    } catch (err: any) {
      console.error('Login failed:', err);
      setError('Falha no login. Tente novamente.');
      setIsLoading(false);
    }
  }, []);


  const logout = useCallback(async () => {
    console.log('👋 Iniciando logout...');
    try {
      setIsLoading(true);
      setUser(null);

      // Tokens HttpOnly são limpos automaticamente pelo backend
      // Não precisamos mais limpar localStorage
      console.log('🗑️ Logout: cookies serão limpos pelo backend');

      // Logout do backend (irá limpar cookies HttpOnly automaticamente)
      try {
        await api.post('/auth/logout');
        console.log('✅ Logout do backend realizado');
      } catch (err) {
        console.error('Backend logout error:', err);
      }

      // Fazer logout do MSAL
      if (msalInstance) {
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          try {
            await msalInstance.clearCache();
            msalInstance.setActiveAccount(null);
          } catch (error) {
            console.error('Error clearing MSAL cache:', error);
          }
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