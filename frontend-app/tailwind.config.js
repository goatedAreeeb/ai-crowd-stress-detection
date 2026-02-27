/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: '#0a0a0f',
                darker: '#050508',
                neon: {
                    green: '#00ff88',
                    yellow: '#ffcc00',
                    red: '#ff3333',
                },
                glass: 'rgba(255, 255, 255, 0.05)',
            },
            fontFamily: {
                inter: ['Inter', 'sans-serif'],
            },
            animation: {
                'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'fade-in': 'fadeIn 0.5s ease-out forwards',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                }
            }
        },
    },
    plugins: [],
}
