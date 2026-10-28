# Guía de capturas — Capítulo VI (VectorScan QR)

Antes de empezar: `docker compose up` y `docker compose exec web python manage.py seed_piloto`.
Sitio en `http://localhost:8000`. Contraseña de todos los usuarios: `vectorscan2026`.

Las figuras **7, 8 y 9 se toman desde el teléfono** (flujo de campo con cámara). El
resto desde el navegador de escritorio. Para las móviles, abrí el sitio desde el celular
en la IP de tu máquina en la red local (ej. `http://192.168.x.x:8000`), no `localhost`.

| # | Figura | Entrar como | URL | Notas |
|---|---|---|---|---|
| 1 | Login | — (deslogueado) | `/usuarios/login/` | Pantalla de inicio de sesión. |
| 2 | Panel de usuarios | `admin` | `/usuarios/` | Lista los 4 activos (el inactivo no sale: eso es el soft-delete). |
| 3 | Crear usuario | `admin` | `/usuarios/crear/` | Formulario de alta con selección de rol. |
| 4 | Viviendas con filtros | `oficinista` | `/viviendas/` | Usá la búsqueda y el filtro de zona/estado. |
| 5 | Detalle de vivienda con QR | `oficinista` | `/viviendas/<id>/` | Tomá una de **La Llovizna** o **El Campo**. |
| 6 | Vista de impresión del QR | `oficinista` | `/viviendas/<id>/qr/imprimir/` | Mismo `<id>` de la figura 5. |
| 7 | Escaneo de QR (móvil) | `tecnico1` | `/inspecciones/escanear/` | **Desde el teléfono.** Escaneá el QR impreso/pantalla. |
| 8 | Formulario de inspección (móvil) | `tecnico1` | `/inspecciones/nueva/<vivienda_id>/` | **Desde el teléfono.** Llená hallazgos. |
| 9 | Resultado con riesgo automático (móvil) | `tecnico1` | `/inspecciones/<id>/` | **Desde el teléfono.** Muestra el nivel calculado. |
| 10 | Panel de trazabilidad | `admin` | `/trazabilidad/` | Métricas; "viviendas sin visita reciente" = 10. |
| 11 | Historial longitudinal | `admin` | `/trazabilidad/vivienda/<id>/` | Usá una de las **5 viviendas con 3 inspecciones** (ver abajo). |
| 12 | Seguimiento prioritario | `admin` | `/trazabilidad/seguimiento/` | 3 urgentes (>7 días) + 5 dentro de 7 días. |
| 13 | Registro de auditoría | `admin` | `/trazabilidad/auditoria/` | Movimiento de los 3 módulos; incluye el DELETE_LOGICO del inactivo. |
| 14 | Panel de reportes | `oficinista` | `/reportes/` | Tarjetas de totales por riesgo. |
| 15 | Reporte de inspecciones con filtros | `oficinista` | `/reportes/inspecciones/` | Probá filtro por zona y por riesgo. |
| 16 | Excel exportado | `oficinista` | `/reportes/exportar/excel/` | Descarga el `.xlsx`; abrilo para la captura. |

## Cómo identificar las viviendas clave

Las figuras 5, 6, 8, 9 y 11 piden un `<id>` concreto. La forma rápida de ubicarlos:

```bash
# Las 5 viviendas longitudinales (3 inspecciones) para la Figura 11:
docker compose exec web python manage.py shell -c "
from apps.viviendas.models import Vivienda
from django.db.models import Count
qs = Vivienda.objects.annotate(n=Count('inspecciones')).filter(n=3)
for v in qs: print(v.id, v.codigo_qr, v.zona, v.direccion)
"

# Viviendas de alto riesgo (para figuras de detalle/QR en zonas críticas):
docker compose exec web python manage.py shell -c "
from apps.viviendas.models import Vivienda
for v in Vivienda.objects.filter(zona__in=['Barrio La Llovizna','Barrio El Campo']):
    u = v.inspecciones.filter(estado='Activo').first()
    if u and u.nivel_riesgo=='Alto': print(v.id, v.codigo_qr, v.zona)
"
```

> Para las figuras 7–9, imprimí (Figura 6) o mostrá en pantalla el QR de una vivienda y
> escaneálo con el teléfono logueado como `tecnico1`. Así la inspección queda atribuida a
> un técnico real y aparece luego en productividad y auditoría.
