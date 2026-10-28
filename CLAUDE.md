# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Nota: todas las respuestas e interacciones en este repositorio se dan en **español**.

## Qué es

VectorScan QR es un sistema Django para un programa de control de enfermedades transmitidas por vectores (ETV). Registra viviendas con un código QR, permite a técnicos de campo escanear el QR y registrar inspecciones domiciliarias, clasifica automáticamente el riesgo de cada vivienda, y genera trazabilidad y reportes exportables.

## Stack y comandos

Django 5.1 + PostgreSQL, servido en Docker. No hay gestor de dependencias JS: el frontend usa Bootstrap 5 por CDN y plantillas Django server-rendered.

```bash
# Levantar todo (db + web) — expone el sitio en http://localhost:8000
docker compose up --build

# Migraciones: OJO, solo existen carpetas migrations/ para viviendas e inspecciones.
# usuarios, trazabilidad y reportes NO tienen migraciones versionadas, así que en un
# entorno limpio hay que generarlas (usuarios es crítico: es el AUTH_USER_MODEL).
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Crear roles (admin/oficinista/tecnico) y el superusuario admin/admin2026
docker compose exec web python seed.py

# Tests (todos los tests.py están vacíos actualmente)
docker compose exec web python manage.py test            # toda la suite
docker compose exec web python manage.py test apps.inspecciones                    # una app
docker compose exec web python manage.py test apps.inspecciones.tests.NombreTest.test_x   # un test

# Cualquier comando de Django se corre dentro del contenedor web
docker compose exec web python manage.py <comando>
```

La configuración (`config/settings.py`) lee `.env` vía `django-environ`. Las credenciales de PostgreSQL están hardcodeadas en `settings.py` y `docker-compose.yml` apuntando al host `db` (el servicio de compose), no a `localhost`.

## Arquitectura

Proyecto Django clásico con apps en `apps/`, registradas en `config/urls.py` por prefijo de URL (`/usuarios/`, `/viviendas/`, `/inspecciones/`, `/trazabilidad/`, `/reportes/`). Las plantillas son globales en `templates/<app>/` y todas extienden `templates/base/layout.html` (sidebar + Bootstrap). La raíz `/` redirige a login.

Flujo de datos central: **Vivienda (QR) → Inspeccion (clasifica riesgo) → Trazabilidad + Reportes (leen)**. `trazabilidad` y `reportes` no definen modelos propios; consultan los de `viviendas`, `inspecciones` y `usuarios`.

### Convenciones transversales (seguir siempre)

Estas tres convenciones se repiten en todos los módulos y son la parte que hay que respetar al tocar o crear código:

1. **Borrado lógico (soft delete).** Nada se elimina físicamente. Cada modelo principal tiene un campo `estado` (`'Activo'`/`'Inactivo'`) y **todas las consultas de lectura filtran `estado='Activo'`**. Desactivar = poner `estado='Inactivo'`.

2. **Históricos manuales de auditoría.** Por cada modelo principal existe un modelo gemelo `*Historico` (`UsuarioHistorico`, `ViviendaHistorico`, `InspeccionHistorico`) que guarda una fila-snapshot en cada cambio. **No es automático**: las vistas deben crear el registro histórico a mano en cada INSERT/UPDATE/DELETE_LOGICO, pasando `usuario_cambio=request.user` y el `tipo_operacion` correcto. Ver el helper `_registrar_historial()` en `apps/inspecciones/views.py` como patrón. El módulo `trazabilidad` existe solo para leer estas tablas. Si agregas una operación de escritura, agrega su registro histórico.

3. **Vistas sin Django Forms.** Las vistas leen `request.POST.get(...)` directamente y usan `django.contrib.messages` para feedback. No hay clases Form/ModelForm. Mantén ese estilo al editar vistas existentes.

### Lógica de negocio embebida en `save()`

Dos piezas clave de lógica viven en el `save()` del modelo, no en las vistas:

- **Código e imagen QR** (`apps/viviendas/models.py`): al crear una `Vivienda`, `save()` genera el `codigo_qr` único con formato `VSQR-XXXXXXXX` y produce el PNG (librería `qrcode`) en `media/qr_codes/`. El contenido codificado en el QR es la cadena `VECTORSCAN|{codigo_qr}|{id}`, que es exactamente lo que el escáner de `inspecciones` espera parsear. `regenerar_qr()` rehace la imagen.

- **Clasificación de riesgo** (`apps/inspecciones/models.py`): `Inspeccion.save()` llama a `clasificar_riesgo()` que aplica reglas de negocio fijas: presencia de larvas → `Alto`; criaderos sin larvas → `Medio`; ninguno → `Bajo` (reglas RN-02/03/04). No modificar sin ajustar estas reglas conscientemente.

> La app `apps/clasificacion/` está vacía y NO está en `INSTALLED_APPS`; la clasificación real ocurre en el `save()` de `Inspeccion`. No asumir que es un módulo funcional.

### Usuarios y roles

`usuarios.Usuario` es el `AUTH_USER_MODEL` (extiende `AbstractUser`) con FK a `Rol` y campo `estado`. Existen tres roles (`admin`, `oficinista`, `tecnico`), pero **las vistas solo usan `@login_required`: no hay control de acceso por rol implementado todavía**. El login propio (`apps/usuarios/views.py`) rechaza usuarios con `estado='Inactivo'`. Al crear funcionalidad sensible por rol, el control hay que añadirlo explícitamente.


## Contexto del proyecto

VectorScan QR es el proyecto de graduación (PG2) de Josué Valiente, UMG. Es una
plataforma web que automatiza el registro y la vigilancia de enfermedades transmitidas
por vectores del Centro de Salud de San Felipe, Retalhuleu, con códigos QR y
trazabilidad.

Stack: Python 3.12, Django 5.1, PostgreSQL 15, Docker Compose, Bootstrap. Clasificación
de riesgo **basada en reglas, no machine learning**. Despliegue previsto en DigitalOcean.

Metodología Scrum en 6 sprints. Los 6 módulos están terminados: usuarios, viviendas con
QR, inspecciones, clasificación de riesgo, trazabilidad y reportes.

## Delimitación del alcance — no negociable

El sistema está delimitado al **casco urbano de San Felipe, Retalhuleu**, que son estos
seis barrios y nada más:

El Centro, La Llovizna, El Campo, El Jardín, Camilo Alvarado, La Linterna.

El programa real del Centro de Salud también trabaja aldeas, caseríos y lotificaciones.
**Esas quedan fuera.** No sembrés, importés ni muestres localidades que no sean esos seis
barrios. Cualquier "ALDEA ..." que aparezca en una pantalla contradice el documento
académico ya entregado.

## Cifras que ya están escritas en el documento

El Capítulo VI está redactado y entregado. Estos números no se pueden cambiar desde el
código; el código se ajusta a ellos:

- 40 viviendas registradas, de las cuales 30 fueron inspeccionadas en el piloto.
- Distribución de riesgo de esas 30: **8 alto, 12 medio, 10 bajo**.
- Participantes del piloto: 2 técnicos de campo y 1 oficinista.
- Concordancia del clasificador contra criterio manual: 96.7 %.

Si un cambio tuyo altera cualquiera de estas cifras, pará y avisá antes de continuar.

## Reglas de trabajo

- **No crear migraciones sin pedir autorización explícita.** Si una tarea parece
  necesitar un cambio de modelo, decilo y esperá respuesta.
- No tocar el clasificador de riesgo por vivienda. Sustenta un resultado ya publicado en
  el documento.
- Antes de escribir código que toque modelos, leer `models.py` y confirmar los nombres
  reales de los campos. No asumir.
- Los códigos QR se generan por el flujo normal del sistema, nunca a mano.

## Datos: demo y producción nunca se mezclan

| Comando | Datos | Corre si |
|---|---|---|
| `seed_piloto` | Ficticios | `DEBUG=True` |
| `importar_formatos` | Reales del Centro de Salud | `DEBUG=False` |

Cada comando debe abortar si se intenta correr en el entorno equivocado.

Ningún archivo con datos reales de personas se versiona en Git, aunque el repositorio
sea privado.

## Formatos del MSPAS: qué entra y qué no

Entra: Formulario A-1 (encuesta y verificación, con los 9 tipos de depósito), censo de
casas por manzana, consolidado mensual de Vigilancia y Control del Dengue, e índices
entomológicos.

Queda fuera, por delimitación ya documentada:

- Control de insecticidas y medicamentos — es gasto e insumos, no vigilancia.
- Formato de control MHT — es malaria, no dengue, y trae datos de pacientes.
- Fichas epidemiológicas — nombre, fecha de nacimiento, teléfono y resultados de
  laboratorio de pacientes reales.
- Análisis de sala situacional en PowerPoint — producto analítico derivado.
- Formulario A-5 de muestras larvarias — laboratorio de entomología.

Los tres primeros no se importan, no se versionan y no aparecen en capturas ni anexos.
En Guatemala el Decreto 57-2008 clasifica el estado de salud como dato sensible,
conocible solo por su titular, y el Centro de Salud es sujeto obligado.

## Índices entomológicos (fase 2)

- Índice de Casas = casas positivas ÷ casas inspeccionadas × 100
- Índice de Breteau = recipientes positivos ÷ casas inspeccionadas × 100
- Índice de Recipientes = recipientes positivos ÷ recipientes inspeccionados × 100

Estratificación por Índice de Casas: menos de 10 BAJO, de 10 a 25 MEDIANO, 25 o más ALTO.

Estos cortes están deducidos de la hoja de estratificación 2026 del Centro de Salud y
están **pendientes de confirmación con la oficinista**. No los presentes como oficiales
hasta que se confirmen.
