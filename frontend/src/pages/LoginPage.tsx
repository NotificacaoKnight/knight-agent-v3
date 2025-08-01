import React, { useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Navigate } from 'react-router-dom';
import { Shield, Moon, Sun, Sparkles, Lock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { cn } from '../lib/utils';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading, error } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  // State for gradient effect
  const [mousePosition, setMousePosition] = useState({ x: 160, y: 24 }); // Center of 320px x 48px button
  const [isHovering, setIsHovering] = useState(false);
  




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

  // Handle mouse movement for gradient effect
  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setMousePosition({ x, y });
    if (!isHovering) {
      setIsHovering(true);
    }
  };

  const handleMouseEnter = () => {
    setIsHovering(true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    // Reset position will be handled by the gradient style
  };


  // Create gradient style based on mouse position
  const gradientStyle = {
    opacity: isHovering ? 1 : 0,
    background: isHovering 
      ? `radial-gradient(circle 500px at ${mousePosition.x}px ${mousePosition.y}px, 
          rgba(255, 235, 59, 0.8) 0%, 
          rgba(255, 193, 7, 0.6) 15%, 
          rgba(255, 166, 0, 0.4) 30%, 
          rgba(255, 152, 0, 0.3) 45%, 
          rgba(255, 138, 0, 0.2) 60%, 
          transparent 75%)`
      : `radial-gradient(circle 500px at 50% 50%, 
          rgba(255, 235, 59, 0.8) 0%, 
          rgba(255, 193, 7, 0.6) 15%, 
          rgba(255, 166, 0, 0.4) 30%, 
          rgba(255, 152, 0, 0.3) 45%, 
          rgba(255, 138, 0, 0.2) 60%, 
          transparent 75%)`
  };

  const features = [
    {
      icon: Shield,
      title: 'Seguro',
      description: 'Autenticação Microsoft',
      color: 'text-white'
    },
    {
      icon: Sparkles,
      title: 'Inteligente',
      description: 'Integração com IA',
      color: 'text-white'
    }
  ];


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
      
      {/* Theme toggle with enhanced glassmorphism */}
      <Button
        onClick={toggleTheme}
        className="absolute top-4 right-4 sm:top-6 sm:right-6 z-10 rounded-2xl"
        style={{
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}
        variant="outline"
        size="icon"
        aria-label={theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'}
      >
        {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </Button>

      <div className="w-full max-w-lg relative z-10">
        {/* Brand Header with mascot photo */}
        <header className="text-center mb-8" role="banner">
          <div 
            className="mx-auto h-20 w-20 sm:h-24 sm:w-24 rounded-full flex items-center justify-center mb-6 shadow-lg shadow-primary/20 dark:shadow-primary/40 p-px"
            style={{
              background: `
                linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%),
                rgba(255, 255, 255, 0.06)
              `,
              backdropFilter: 'blur(20px) saturate(180%)',
              WebkitBackdropFilter: 'blur(20px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              boxShadow: `
                0 8px 25px rgba(0, 0, 0, 0.15),
                inset 0 1px 2px rgba(255, 255, 255, 0.4),
                inset 0 -1px 2px rgba(0, 0, 0, 0.05),
                inset 1px 1px 4px rgba(255, 255, 255, 0.15)
              `
            }}
          >
            <div className="w-full h-full rounded-full overflow-hidden bg-white/10 backdrop-blur-sm border border-white/20">
              <img 
                src="/knight-profile-semfundo.png" 
                alt="Knight Assistant Mascot" 
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          <div className="space-y-4">
            <h1 className="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-foreground to-foreground-secondary bg-clip-text text-transparent leading-relaxed pb-2">
              Knight
            </h1>
          </div>
        </header>

        {/* Login card container */}
        <div className="relative">
          
          {/* Login Card with enhanced glassmorphism */}
          <div 
            className="relative overflow-hidden rounded-3xl p-8 max-w-md mx-auto border"
            style={{
              background: `
                linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.03) 100%),
                rgba(255, 255, 255, 0.04)
              `,
              backdropFilter: 'blur(25px) saturate(180%)',
              WebkitBackdropFilter: 'blur(25px) saturate(180%)',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              borderWidth: '1px',
              borderStyle: 'solid',
              boxShadow: `
                0 8px 32px rgba(0, 0, 0, 0.25),
                0 20px 60px rgba(0, 0, 0, 0.12),
                inset 0 1px 0 rgba(255, 255, 255, 0.25),
                inset 0 -1px 0 rgba(255, 255, 255, 0.12),
                0 0 0 1px rgba(255, 255, 255, 0.1)
              `
            }}
            role="main"
          >
          {/* Bottom reflection for glassmorphism depth */}
          <div 
            className="absolute bottom-0 left-0 right-0 h-1/2 rounded-b-3xl pointer-events-none"
            style={{
              background: `linear-gradient(to bottom, 
                transparent 0%, 
                rgba(0, 0, 0, 0.08) 60%, 
                rgba(0, 0, 0, 0.2) 100%)`,
            }}
          />
          
          <div className="relative z-10">
            <div className="text-center pb-6 mb-6">
              <h2 className="text-xl sm:text-2xl font-semibold text-card-foreground mb-2">
                Bem-vindo
              </h2>
              <p className="text-sm sm:text-base text-muted-foreground">
                Entre com sua conta Microsoft
              </p>
            </div>

            <div className="space-y-6">
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

            {/* Login Button - White with mouse-following yellow gradient and refined outerglow */}
            <Button
              ref={buttonRef}
              onClick={handleLogin}
              onMouseMove={handleMouseMove}
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
              disabled={isLoading}
              size="lg"
              className={cn(
                "w-80 h-12 text-base font-semibold rounded-2xl mx-auto block",
                "text-card-foreground hover:text-gray-800",
                "shadow-lg hover:shadow-yellow-400/25 hover:shadow-2xl hover:scale-[1.02]",
                "hover:border-yellow-400",
                "transition-all duration-400 ease-out",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                "focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:outline-none",
                "overflow-hidden relative"
              )}
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.3)'
              }}
              aria-label={isLoading ? 'Conectando à conta Microsoft' : 'Entrar com conta Microsoft'}
            >
              {/* Mouse-following gradient overlay */}
              <div 
                className="absolute inset-0 pointer-events-none transition-opacity duration-300"
                style={gradientStyle}
              />
              {/* Button content with relative z-index to stay above gradient */}
              <div className="relative z-10 flex items-center justify-center">
                {isLoading ? (
                  <>
                    <div className="h-4 w-4 border-2 border-gray-600/30 border-t-gray-600 rounded-full animate-spin mr-3" />
                    Conectando...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5 mr-3" viewBox="0 0 21 21" fill="none">
                      <rect x="0" y="0" width="10" height="10" fill="#F25022"/>
                      <rect x="11" y="0" width="10" height="10" fill="#00A4EF"/>
                      <rect x="0" y="11" width="10" height="10" fill="#7FBA00"/>
                      <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
                    </svg>
                    Entrar
                  </>
                )}
              </div>
            </Button>

            {/* Features Grid - Updated for 2 columns */}
            <div className="grid grid-cols-2 gap-6 pt-4" role="region" aria-label="Recursos do sistema">
              {features.map((feature, index) => (
                <div key={index} className="text-center group cursor-default">
                  <div className={cn(
                    "w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3",
                    "backdrop-blur-md bg-white/15 border border-white/20"
                  )}
                  style={{
                    backdropFilter: 'blur(12px)',
                    WebkitBackdropFilter: 'blur(12px)'
                  }}>
                    <feature.icon className={cn("h-6 w-6", feature.color)} strokeWidth={2} aria-hidden="true" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-card-foreground">
                      {feature.title}
                    </p>
                    <p className="text-xs text-muted-foreground leading-tight">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

            <div className="pt-6 mt-6 border-t border-white/10">
              <div className="w-full text-center space-y-2">
                {/* <p className="text-xs text-muted-foreground">
                  Ao fazer login, você concorda com os termos de uso da empresa
                </p> */}
                <p className="text-xs text-muted-foreground/80">
                  Para suporte técnico, entre em contato com o TI
                </p>
              </div>
            </div>
          </div>
          </div>
        </div>

        {/* Version Badges with glassmorphism */}
        <footer className="text-center mt-6" role="contentinfo">
          <div className="flex justify-center items-center gap-3">
            <Badge 
              variant="outline" 
              className="text-xs rounded-full px-4 py-2"
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
                border: '1px solid rgba(255, 255, 255, 0.15)'
              }}
            >
              <Lock className="h-3 w-3 mr-1" aria-hidden="true" />
              Ambiente Seguro
            </Badge>
            
            <Badge 
              variant="outline" 
              className="text-xs rounded-full px-4 py-2"
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
                border: '1px solid rgba(255, 255, 255, 0.15)'
              }}
            >
              Ver 1.0 - Agentic RAG
            </Badge>
          </div>
        </footer>
      </div>
    </div>
  );
};