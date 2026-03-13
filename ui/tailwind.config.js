/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Syne', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        background: 'hsl(var(--background))',
        surface:    'hsl(var(--surface))',
        border:     'hsl(var(--border))',
        accent:     'hsl(var(--accent))',
        'accent-dim': 'hsl(var(--accent-dim))',
        muted:      'hsl(var(--muted))',
        'muted-fg': 'hsl(var(--muted-fg))',
        foreground: 'hsl(var(--foreground))',
        success:    'hsl(var(--success))',
        warning:    'hsl(var(--warning))',
        danger:     'hsl(var(--danger))',
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '10px',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
        'slide-in': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        }
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease forwards',
        'pulse-dot': 'pulse-dot 1.5s ease-in-out infinite',
        'slide-in': 'slide-in 0.25s ease forwards',
      },
    },
  },
  plugins: [],
}
