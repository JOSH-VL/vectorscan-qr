# Pendientes para la fase 2 — NO implementar ahora

Derivado del análisis de los formatos oficiales del MSPAS que usa la oficinista del
Centro de Salud. Para el Trabajo Final del **9 de noviembre de 2025**. Nada de esto se
tocó en el seed del piloto y **nada de esto toca el clasificador de riesgo por vivienda**,
que sostiene el 96.7 % de concordancia ya reportado.

## Cambios de modelo (requieren migración, pedir autorización)

1. **Tabla hija `DepositoInspeccion`** con los 9 tipos del Formulario A-1:
   pilas, toneles, llantas, floreros, cubetas, árbol y plantas, pozos y similares,
   tanques, otros. Campos: inspeccionados y positivos por tipo.
2. **Campo `clase_trabajo`** en Inspección: ENC (encuesta), VERIF (verificación),
   ACCIÓN, TRATAMIENTO, FUM (fumigación).
3. **Campos propios** en Vivienda para manzana y número de casa (hoy embebidos en
   `direccion`).

## Reportes (fase 2)

4. **Tres índices entomológicos** por zona y periodo:
   - Índice de Casas = casas positivas ÷ casas inspeccionadas × 100
   - Índice de Breteau = recipientes positivos ÷ casas inspeccionadas × 100
   - Índice de Recipientes = recipientes positivos ÷ recipientes inspeccionados × 100
   - Estratificación por Índice de Casas: <10 BAJO, 10–25 MEDIANO, ≥25 ALTO.
     Cortes deducidos de la hoja de estratificación 2026; **confirmar con la oficinista**
     antes de la defensa.
5. **Exportación en layout oficial**: hoja con estructura del Formulario A-1 y hoja con
   el consolidado mensual de Vigilancia y Control del Dengue.

## Carga de datos reales

6. **Comando `importar_formatos`**, separado del seed. Debe:
   - Negarse a correr si `DEBUG=True` (es solo de producción).
   - Negarse a correr si detecta registros creados por `seed_piloto`; primero hay que
     limpiarlos.
   - Leer los Excel desde una ruta por argumento, nunca versionada en Git.
   - Validar antes de insertar y reportar las filas rechazadas sin abortar el lote.
   - Ser idempotente por correlativo y fecha.

   Importa solo vigilancia entomológica (Formulario A-1, consolidado de Vigilancia y
   Control del Dengue). **No importa fichas epidemiológicas ni formato MHT** (datos
   sensibles de pacientes y de otro programa; Decreto 57-2008).

## Fuera de alcance (decidido y documentado)

- Control de insecticidas y medicamentos (gasto e insumos).
- Formato de control MHT (malaria, con datos de pacientes).
- Fichas epidemiológicas (datos sensibles; ni en anexos).
- Análisis de sala situacional en PowerPoint (producto derivado).
- Formulario A-5 de muestras larvarias (laboratorio de entomología).

---

## Notas del seed_piloto sobre límites de los modelos actuales

Observaciones al sembrar con los modelos tal como están hoy (anotadas aquí, **no
implementadas**, según la REGLA DURA del brief):

- **Casas/habitantes por zona del Distrito No. 7**: el brief trae cifras oficiales por
  barrio (El Centro 422/1,463; La Llovizna 367/1,123; El Campo 285/872; El Jardín
  204/1,020; Camilo Alvarado 174/520; La Linterna 109/533), pero `Vivienda.zona` es
  texto libre y **no existe un modelo de Zona** donde guardarlas. Se omitieron. Un
  catálogo `Zona` (nombre, casas, habitantes) sería el lugar natural en fase 2.
- **Fechas `auto_now_add`**: `fecha_inspeccion`, `fecha_registro` y `fecha_cambio` son
  `auto_now_add`, así que ignoran cualquier fecha al crear. El seed las ajusta después
  con `QuerySet.update()` para poder escalonar el historial. Es correcto para datos
  demo; si en el futuro se quisieran fechas históricas desde las vistas, habría que
  repensar esos campos.
- **Marca de idempotencia**: no hay un campo "origen/demo" en los modelos. El seed
  identifica sus registros por los usuarios que crea (viviendas registradas por
  `tecnico1`/`tecnico2`). Un campo booleano `es_demo` evitaría depender de eso.
