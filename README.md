# Cocina Soberana

Cocina Soberana es una Progressive Web App (PWA) offline-first diseñada para familias venezolanas que necesitan planificar comidas saludables ajustadas a su presupuesto real.

## Stack Técnico

- **Backend**: Django 6.0 (con soporte moderno de `STORAGES` y middleware Whitenoise)
- **Base de Datos**: PostgreSQL
- **Frontend**: HTMX + Tailwind CSS (v4 standalone)
- **PWA**: Service Worker local con caché Network-first/Cache-first, y manifiesto W3C
- **Despliegue**: Render

## Equipo Nodo Cocina Soberana
- Alcides Mata — Coordinación
- Albert Hernández
- Yannis Iturriago Martínez
- Sergio Enmanuel Hernández
- Hector Manuel Rodríguez
- Daniel Suárez

---

## Instrucciones de Instalación Local

### Requisitos Previos
- Python 3.12+
- PostgreSQL activo y base de datos `cocina_soberana` creada.

### Pasos de Configuración

1. **Clonar el repositorio**:
   ```bash
   git clone <repo-url>
   cd cocina_soberana
   ```

2. **Crear y activar el entorno virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Linux/Mac
   # .venv\Scripts\activate   # En Windows
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el archivo de entorno**:
   Crea un archivo `.env` en la raíz del proyecto basándote en `.env.example`:
   ```ini
   SECRET_KEY=tu_clave_secreta_local
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=postgres://usuario:contraseña@localhost:5432/cocina_soberana
   ```

5. **Aplicar migraciones y sembrar base de datos**:
   ```bash
   python manage.py migrate
   python manage.py seed_catalogo --no-input
   ```

6. **Crear un superusuario para el panel de administración**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Iniciar el servidor de desarrollo**:
   ```bash
   python manage.py runserver
   ```
   Accede a `http://127.0.0.1:8000/`.

---

## Despliegue en Render

El despliegue está automatizado usando Infrastructure-as-Code a través de `render.yaml`.

### Pasos para el Despliegue

1. Conecta tu cuenta de GitHub a [Render](https://render.com/).
2. Haz clic en **New** -> **Blueprint**.
3. Selecciona el repositorio de `cocina_soberana`.
4. Render leerá el archivo `render.yaml` y configurará automáticamente la base de datos PostgreSQL y el servicio Web.
5. **Configuración de Variables de Entorno en el Dashboard**:
   - Una vez creado el servicio Web, copia la URL que te asigna Render (por ejemplo, `cocina-soberana.onrender.com`).
   - Ve a la pestaña **Environment** en el panel de control del servicio web de Render.
   - Modifica la variable `ALLOWED_HOSTS` asignándole tu subdominio asignado de Render (ej. `cocina-soberana.onrender.com`).
6. Guarda los cambios. Render reconstruirá e iniciará tu aplicación con el subdominio configurado correctamente.
