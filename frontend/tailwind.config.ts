import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--bg)',
        surface: 'var(--surface)',
        foreground: 'var(--text)',
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-foreground)',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted-hsl) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground-hsl) / <alpha-value>)',
        },
        border: 'var(--border)',
        ring: 'var(--ring)',
        success: {
          DEFAULT: 'var(--success)',
          foreground: 'var(--surface)',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          foreground: 'var(--surface)',
        },
        destructive: {
          DEFAULT: 'var(--destructive)',
          foreground: 'var(--card)',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent-hsl) / <alpha-value>)',
          foreground: 'hsl(var(--accent-foreground-hsl) / <alpha-value>)',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover-hsl) / <alpha-value>)',
          foreground: 'hsl(var(--popover-foreground-hsl) / <alpha-value>)',
        },
        card: {
          DEFAULT: 'var(--card)',
          foreground: 'var(--text)',
        },
        glass: 'var(--glass)',
      },
      borderRadius: {
        '2xl': 'var(--r-2xl)',
        xl: 'var(--r-xl)',
        lg: 'var(--r-md)',
        md: 'calc(var(--r-md) - 4px)',
        sm: 'var(--r-sm)',
      },
      boxShadow: {
        'level-1': 'var(--shadow-1)',
        'level-2': 'var(--shadow-2)',
        'level-3': 'var(--shadow-3)',
        'ring-primary': '0 0 0 1px color-mix(in srgb, var(--primary) 35%, transparent)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '50%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.18s ease-out',
        'scale-in': 'scale-in 0.18s ease-out',
        'slide-up': 'slide-up 0.18s ease-out',
        'slide-down': 'slide-down 0.18s ease-out',
        shimmer: 'shimmer 1.4s ease-in-out infinite',
      },
      fontSize: {
        'display-2xl': ['clamp(2.25rem, 2.6vw + 1.8rem, 3.4rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        'display-xl': ['clamp(2rem, 2.1vw + 1.7rem, 2.9rem)', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'display-lg': ['clamp(1.75rem, 1.9vw + 1.5rem, 2.4rem)', { lineHeight: '1.15', letterSpacing: '-0.015em' }],
        headline: ['clamp(1.4rem, 1.2vw + 1.2rem, 1.85rem)', { lineHeight: '1.2', letterSpacing: '-0.012em' }],
        title: ['clamp(1.15rem, 0.9vw + 1rem, 1.35rem)', { lineHeight: '1.25', letterSpacing: '-0.01em' }],
        body: ['clamp(0.95rem, 0.3vw + 0.9rem, 1.05rem)', { lineHeight: '1.45' }],
        caption: ['clamp(0.75rem, 0.22vw + 0.7rem, 0.82rem)', { lineHeight: '1.35', letterSpacing: '0.02em' }],
      },
      screens: {
        xs: '360px',
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
  ],
}

export default config