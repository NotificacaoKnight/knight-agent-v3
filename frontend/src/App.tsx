import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { Toaster as SonnerToaster } from './components/ui/sonner';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ChatProvider } from './context/ChatContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { DocumentsPage } from './pages/DocumentsPage';
import BardPage from './pages/BardPage';
import WizardPage from './pages/WizardPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  // Initial title setup
  useEffect(() => {
    document.title = 'Knight - Assistente IA';
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <ChatProvider>
            <Router>
            <div className="min-h-screen bg-background">
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/logout" element={<Navigate to="/login" replace />} />
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <DashboardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/chat"
                  element={
                    <ProtectedRoute>
                      <ChatPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/chat/:sessionId"
                  element={
                    <ProtectedRoute>
                      <ChatPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <SettingsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/documents"
                  element={
                    <ProtectedRoute requireAdmin>
                      <DocumentsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bard"
                  element={
                    <ProtectedRoute>
                      <BardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/wizard"
                  element={
                    <ProtectedRoute>
                      <WizardPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="*" element={<Navigate to="/chat" replace />} />
              </Routes>
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  className: 'dark:bg-gray-800 dark:text-white',
                }}
              />
              <SonnerToaster richColors position="top-right" />
            </div>
            </Router>
          </ChatProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;