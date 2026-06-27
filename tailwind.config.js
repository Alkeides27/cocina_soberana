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
        primario: '#8C3A16',       // Terracota / Cacao puro
        secundario: '#D4A316',     // Oro Maíz / Papelón
        acento: '#2E6F40',         // Verde Cultivo / Ají dulce
        fondo: '#FFFDF9',          // Blanco crema
        texto: '#221A17',          // Café oscuro
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
