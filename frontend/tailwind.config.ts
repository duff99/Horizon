import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'monospace',
        ],
      },
      colors: {
        canvas: 'hsl(var(--canvas))',
        panel: 'hsl(var(--panel))',
        'panel-2': 'hsl(var(--panel-2))',
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar))',
          fg: 'hsl(var(--sidebar-fg))',
          'fg-active': 'hsl(var(--sidebar-fg-active))',
          hover: 'hsl(var(--sidebar-hover))',
        },
        ink: 'hsl(var(--ink))',
        'ink-2': 'hsl(var(--ink-2))',
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-fg))',
        },
        line: 'hsl(var(--line))',
        'line-soft': 'hsl(var(--line-soft))',
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-fg))',
          soft: 'hsl(var(--accent-soft))',
          'soft-fg': 'hsl(var(--accent-soft-fg))',
        },
        credit: 'hsl(var(--credit))',
        debit: 'hsl(var(--debit))',
        warn: 'hsl(var(--warn))',
        info: 'hsl(var(--info))',
        border: 'hsl(var(--line))',
        input: 'hsl(var(--line))',
        ring: 'hsl(var(--accent))',
        background: 'hsl(var(--canvas))',
        foreground: 'hsl(var(--ink))',
        primary: {
          DEFAULT: 'hsl(var(--ink))',
          foreground: 'hsl(var(--panel))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--panel-2))',
          foreground: 'hsl(var(--ink))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--debit))',
          foreground: 'hsl(var(--panel))',
        },
      },
      borderRadius: {
        sm: '4px',
        md: '7px',
        lg: '10px',
        xl: '14px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.04)',
        'card-hover': '0 4px 12px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
} satisfies Config;
