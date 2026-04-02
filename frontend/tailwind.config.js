/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Khaki Green palette - Trigger brand colors
        khaki: {
          50: '#F4F6EF',
          100: '#E5E9DA',
          200: '#CCD4B8',
          300: '#A8B494',
          400: '#8F9E7A',
          500: '#78866B',   // Main khaki
          600: '#6B7B3B',   // Primary accent
          700: '#5A6438',
          800: '#4A5230',
          900: '#3D4423',
          950: '#252A16',
        },
        // Semantic colors using khaki
        primary: '#6B7B3B',
        'primary-light': '#8F9E7A',
        'primary-dark': '#4A5230',
        // Keep these for trade status colors
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
        // Neutral grays
        surface: '#FAFBF7',
        'surface-dark': '#F0F2EB',
      },
      backgroundColor: {
        'app': '#FAFBF7',
      },
    },
  },
  plugins: [],
}
