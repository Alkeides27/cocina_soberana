// Registro del Service Worker para soporte PWA offline-first
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('Service Worker registrado con éxito. Scope:', registration.scope);
      })
      .catch(error => {
        console.error('Fallo en el registro del Service Worker:', error);
      });
  });
}
