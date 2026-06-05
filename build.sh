#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Poblar el catálogo con datos iniciales si no hay recetas creadas (garantiza idempotencia)
python manage.py shell -c "from catalogo.models import Receta; import sys; sys.exit(0 if not Receta.objects.exists() else 1)" && python manage.py seed_catalogo --no-input || true
