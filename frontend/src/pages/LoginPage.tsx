import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Navigate } from 'react-router-dom';
import { Shield, Moon, Sun, Sparkles, Zap, Lock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { cn } from '../lib/utils';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading, error } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  const handleLogin = async () => {
    try {
      await login();
    } catch (err) {
      console.error('Login error:', err);
    }
  };

  const features = [
    {
      icon: Shield,
      title: 'Seguro',
      description: 'Autenticação Microsoft Azure AD',
      color: 'text-primary'
    },
    {
      icon: Sparkles,
      title: 'Inteligente',
      description: 'IA avançada para suas consultas',
      color: 'text-accent'
    },
    {
      icon: Zap,
      title: 'Rápido',
      description: 'Respostas em segundos',
      color: 'text-accent'
    }
  ];


  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-8 relative overflow-hidden">
      {/* Clean background without overlays */}
      
      {/* Theme toggle */}
      <Button
        onClick={toggleTheme}
        className="absolute top-4 right-4 sm:top-6 sm:right-6 z-10"
        variant="outline"
        size="icon"
        aria-label={theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'}
      >
        {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </Button>

      <div className="w-full max-w-lg relative z-10">
        {/* Brand Header */}
        <header className="text-center mb-8" role="banner">
          <div className="mx-auto h-16 w-16 sm:h-20 sm:w-20 bg-accent rounded-2xl flex items-center justify-center mb-4 sm:mb-6 shadow-lg">
            <Shield className="h-8 w-8 sm:h-10 sm:w-10 text-accent-foreground" strokeWidth={2.5} aria-hidden="true" />
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl sm:text-4xl font-bold text-foreground">
              Knight Agent
            </h1>
            <p className="text-base sm:text-lg text-muted-foreground font-medium">
              Seu assistente IA corporativo
            </p>
            <Badge variant="secondary" className="text-xs inline-flex items-center">
              <Lock className="h-3 w-3 mr-1" aria-hidden="true" />
              Ambiente Seguro
            </Badge>
          </div>
        </header>

        {/* Login Card */}
        <Card className="border shadow-2xl bg-card" role="main">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl sm:text-2xl text-card-foreground">
              Bem-vindo de volta
            </CardTitle>
            <CardDescription className="text-sm sm:text-base text-muted-foreground">
              Entre com sua conta Microsoft para acessar o sistema
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Error Alert */}
            {error && (
              <Alert variant="destructive" className="border-red-200 dark:border-red-800/50" role="alert" aria-live="polite">
                <AlertDescription className="text-sm">
                  <strong>Erro de autenticação:</strong> {error}
                  {error.includes('network') && (
                    <div className="mt-2 text-xs">
                      Verifique sua conexão com a internet e tente novamente.
                    </div>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* Login Button */}
            <Button
              onClick={handleLogin}
              disabled={isLoading}
              size="lg"
              className={cn(
                "w-full h-12 text-base font-semibold",
                "bg-primary hover:bg-primary-hover",
                "text-primary-foreground",
                "shadow-lg shadow-primary/25",
                "transition-all duration-200 ease-in-out",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none"
              )}
              aria-label={isLoading ? 'Conectando à conta Microsoft' : 'Entrar com conta Microsoft'}
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-3" />
                  Conectando...
                </>
              ) : (
                <div className="flex items-center justify-center">
                  <svg className="w-5 h-5 mr-3" viewBox="0 0 21 21" fill="none">
                    <rect x="0" y="0" width="10" height="10" fill="#F25022"/>
                    <rect x="11" y="0" width="10" height="10" fill="#00A4EF"/>
                    <rect x="0" y="11" width="10" height="10" fill="#7FBA00"/>
                    <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
                  </svg>
                  Entrar com Microsoft
                </div>
              )}
            </Button>

            {/* Features Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-3 pt-4" role="region" aria-label="Recursos do sistema">
              {features.map((feature, index) => (
                <div key={index} className="text-center group">
                  <div className={cn(
                    "w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2",
                    "bg-muted group-hover:bg-muted/80",
                    "transition-colors duration-200"
                  )}>
                    <feature.icon className={cn("h-5 w-5", feature.color)} strokeWidth={2} aria-hidden="true" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-card-foreground">
                      {feature.title}
                    </p>
                    <p className="text-xs text-muted-foreground leading-tight">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>

          <CardFooter className="pt-0">
            <div className="w-full text-center space-y-2">
              <p className="text-xs text-muted-foreground">
                Ao fazer login, você concorda com os termos de uso da empresa
              </p>
              <p className="text-xs text-muted-foreground/80">
                Para suporte técnico, entre em contato com o RH
              </p>
            </div>
          </CardFooter>
        </Card>

        {/* Version Badge */}
        <footer className="text-center mt-6" role="contentinfo">
          <Badge variant="outline" className="text-xs">
            Knight Agent v2.0 - Sistema RAG Agêntico
          </Badge>
        </footer>
      </div>
    </div>
  );
};