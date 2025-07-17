import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { Moon, Sun } from 'lucide-react';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative inline-flex h-14 w-7 flex-col items-center justify-between rounded-full bg-gradient-to-b from-sky-400 to-blue-500 dark:from-indigo-600 dark:to-purple-600 p-1 transition-all duration-500 hover:shadow-lg focus:outline-none"
      aria-label="Toggle theme"
    >
      <span className="sr-only">Toggle theme</span>
      
      {/* Sun icon - positioned at top */}
      <span className="z-10 flex h-5 w-5 items-center justify-center">
        <Sun className={`h-4 w-4 transition-all duration-500 ease-in-out ${
          theme === 'light' 
            ? 'text-yellow-400 opacity-100 scale-100 rotate-0' 
            : 'text-gray-300 opacity-0 scale-75 rotate-180'
        }`} />
      </span>
      
      {/* Moon icon - positioned at bottom */}
      <span className="z-10 flex h-5 w-5 items-center justify-center">
        <Moon className={`h-4 w-4 transition-all duration-500 ease-in-out ${
          theme === 'dark' 
            ? 'text-white opacity-100 scale-100 rotate-0' 
            : 'text-gray-300 opacity-0 scale-75 -rotate-90'
        }`} />
      </span>
      
      {/* Toggle ball that covers the opposite icon */}
      <span
        className={`absolute left-1 h-5 w-5 transform rounded-full shadow-md transition-all duration-500 ease-in-out ${
          theme === 'light' 
            ? 'top-[1.75rem] bg-white' 
            : 'top-1 bg-gray-800'
        }`}
        style={{
          boxShadow: theme === 'dark' 
            ? '0 2px 6px rgba(0, 0, 0, 0.4), inset 0 1px 1px rgba(255, 255, 255, 0.1)' 
            : '0 2px 6px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.8)'
        }}
      />
    </button>
  );
};