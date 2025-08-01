/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: "rgb(var(--border))",
        input: "rgb(var(--input))",
        ring: "rgb(var(--ring))",
        background: "rgb(var(--background))",
        foreground: "rgb(var(--foreground))",
        primary: {
          DEFAULT: "rgb(var(--primary))",
          foreground: "rgb(var(--primary-foreground))",
          hover: "rgb(var(--primary-hover))",
          focus: "rgb(var(--primary-focus))",
        },
        secondary: {
          DEFAULT: "rgb(var(--secondary))",
          foreground: "rgb(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "rgb(var(--destructive))",
          foreground: "rgb(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "rgb(var(--muted))",
          foreground: "rgb(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "rgb(var(--accent))",
          foreground: "rgb(var(--accent-foreground))",
          hover: "rgb(var(--accent-hover))",
          focus: "rgb(var(--accent-focus))",
        },
        card: {
          DEFAULT: "rgb(var(--card))",
          foreground: "rgb(var(--card-foreground))",
        },
        knight: {
          // Dark theme colors
          'dark-bg': '#2A2A2A',
          'dark-bg-secondary': '#303030',
          'dark-accent': '#FFA600',
          'dark-accent-hover': '#FFB833',
          'dark-accent-focus': '#FFC966',
          'dark-text': '#FFFFFF',
          'dark-text-secondary': '#B0B0B0',
          'dark-text-tertiary': '#808080',
          'dark-border': '#404040',
          
          // Light theme colors
          'light-bg': '#EBE6DF',
          'light-bg-secondary': '#F9F7F3',
          'light-accent': '#2A2A2A',
          'light-accent-hover': '#1A1A1A',
          'light-accent-focus': '#0A0A0A',
          'light-text': '#2A2A2A',
          'light-text-secondary': '#5A5A5A',
          'light-text-tertiary': '#808080',
          'light-border': '#D0C7BA',
          
          // Legacy support (mantém cores antigas para compatibilidade)
          primary: '#2A2A2A',
          secondary: '#FFA600',
          accent: '#FFA600',
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'grid-slate-200': `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' width='32' height='32' fill='none' stroke='rgb(148 163 184 / 0.05)'%3e%3cpath d='m0 .5h32m-32 32v-32'/%3e%3c/svg%3e")`,
        'grid-slate-700/25': `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' width='32' height='32' fill='none' stroke='rgb(51 65 85 / 0.1)'%3e%3cpath d='m0 .5h32m-32 32v-32'/%3e%3c/svg%3e")`,
      },
    },
  },
  plugins: [],
}