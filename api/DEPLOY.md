
# DEPLOY.md

## Objetivo

Desplegar Verifiko sin romper producción por desalineación entre código y base de datos.

## Regla obligatoria

**Primero migración, después deploy.**

Nunca desplegar código que espere cambios de esquema si la base de datos de producción no fue migrada antes.

---

## Cuándo seguir este documento

Usar este flujo siempre que el cambio afecte cualquiera de estos puntos:

- modelos SQLAlchemy
- mappers de persistencia
- migraciones Alembic
- tablas, columnas, índices o constraints
- DTOs/campos persistidos que dependan del esquema
- queries que lean nuevas columnas

---

## Flujo seguro de despliegue

### 1. Validación local previa

Desde `api/`:

```bash
source .venv/bin/activate
python -m alembic upgrade head
pytest -q