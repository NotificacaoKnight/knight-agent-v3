import React, { createContext, useContext, useEffect, useState } from 'react';
import { PublicClientApplication } from '@azure/msal-browser';

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

  useEffect(() => {
    const initializeMsal = async () => {
      try {
        await msalInstance.initialize();
        
        // Check if user is already logged in
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          // User is already logged in
          const account = accounts[0];
          setUser({
            id: account.localAccountId,
            email: account.username,
            name: account.name || account.username,
          });
        }
      } catch (err) {
        console.error('MSAL initialization failed:', err);
        setError('Falha na inicialização da autenticação');
      } finally {
        setIsLoading(false);
      }
    };

    initializeMsal();
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
        setUser({
          id: response.account.localAccountId,
          email: response.account.username,
          name: response.account.name || response.account.username,
        });
      }
    } catch (err: any) {
      console.error('Login failed:', err);
      setError('Falha no login. Tente novamente.');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    msalInstance.logoutPopup({
      postLogoutRedirectUri: window.location.origin,
    });
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    error,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};