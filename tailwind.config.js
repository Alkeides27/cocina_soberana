/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        primario: '#7D6608',       // Dorado oliva (tierra venezolana)
        secundario: '#B7950B',     // Mostaza (papelón)
        acento: '#5499C7',         // Azul calmo (confianza)
        fondo: '#FEFCF3',          // Crema cálida
        texto: '#2C3E50',          // Carbón suave
        exito: '#27AE60',
        advertencia: '#E67E22',
        error: '#C0392B',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
