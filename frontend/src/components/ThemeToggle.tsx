import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { Moon, Sun } from 'lucide-react';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative inline-flex flex-col items-center justify-between rounded-full bg-gradient-to-b from-gray-600 to-gray-400 dark:from-yellow-500 dark:to-amber-600 transition-all duration-500 hover:shadow-lg focus:outline-none"
      style={{
        height: '56px',
        width: '28px',
        padding: '4px'
      }}
      aria-label="Toggle theme"
    >
      <span className="sr-only">Toggle theme</span>
      
      {/* Sun icon - positioned at top */}
      <span className="relative z-10 flex h-5 w-5 items-center justify-center">
        <Sun className={`h-4 w-4 transition-all duration-500 ease-in-out ${
          theme === 'dark' 
            ? 'text-gray-800 opacity-100 scale-100 rotate-0' 
            : 'text-gray-400 opacity-50 scale-75 rotate-180'
        }`} />
      </span>
      
      {/* Moon icon - positioned at bottom */}
      <span className="relative z-10 flex h-5 w-5 items-center justify-center">
        <Moon className={`h-4 w-4 transition-all duration-500 ease-in-out ${
          theme === 'light' 
            ? 'text-gray-200 opacity-100 scale-100 rotate-0' 
            : 'text-amber-300 opacity-50 scale-75 -rotate-90'
        }`} />
      </span>
      
      {/* Toggle ball that covers the active icon */}
      <div
        className="absolute rounded-full z-50"
        style={{
          width: '20px',
          height: '20px',
          left: '4px',
          top: theme === 'light' ? '4px' : '32px',
          backgroundColor: theme === 'light' ? '#ffffff' : '#1f2937',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
          transition: 'top 500ms ease-in-out'
        }}
      />
    </button>
  );
};