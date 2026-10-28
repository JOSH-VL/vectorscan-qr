# VectorScan QR

Sistema Django para el programa de control de enfermedades transmitidas por vectores
(ETV) del Centro de Salud de San Felipe, Retalhuleu: registro de viviendas con código
QR, inspecciones domiciliarias, clasificación de riesgo por reglas, trazabilidad y
reportes exportables.

## Levantar el entorno (Docker)

```bash
docker compose up --build          # db + web en http://localhost:8000

# Migraciones (usuarios/trazabilidad/reportes no traen migraciones versionadas)
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Roles base + superusuario admin
docker compose exec web python seed.py
```

## Datos de demostración para capturas (Capítulo VI)

El comando `seed_piloto` siembra datos **ficticios** para las 16 capturas del documento
académico. Solo corre con `DEBUG=True` (entorno demo) y es idempotente: cada corrida
limpia lo que sembró antes y vuelve a sembrar, sin tocar datos creados a mano bajo
`admin`.

```bash
docker compose exec web python manage.py seed_piloto
```

Siembra:

- 5 usuarios (4 del piloto + 1 inactivo para evidenciar la eliminación lógica).
- Los 6 barrios del casco urbano de San Felipe.
- 40 viviendas con QR (30 inspeccionadas, 10 sin visita).
- Inspecciones cuyo riesgo calcula el propio clasificador: **8 alto, 12 medio, 10 bajo**.
- Auditoría de los tres módulos (usuarios, viviendas, inspecciones).

**Credenciales** (todas con la misma contraseña `vectorscan2026`):

| Usuario | Rol | Nombre |
|---|---|---|
| `admin` | Administrador | Josué Valiente |
| `oficinista` | Oficinista | Liz Mejía Quiroa |
| `tecnico1` | Técnico de campo | Porfirio López Valiente |
| `tecnico2` | Técnico de campo | Elder Barrios Gómez |
| `tecnico_inactivo` | Técnico (inactivo) | Mynor Say Coché |

> La guía de capturas está en [`CAPTURAS_CAPITULO_VI.md`](CAPTURAS_CAPITULO_VI.md).

> `seed_piloto` (ficticio, `DEBUG=True`) e `importar_formatos` (real, `DEBUG=False`)
> **nunca se mezclan**. Ver [`PENDIENTES_FASE2.md`](PENDIENTES_FASE2.md).
