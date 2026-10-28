# BRIEF — Seed de datos piloto para capturas del Capítulo VI

**Repo:** `github.com/JOSH-VL/vectorscan-qr`
**Objetivo:** dejar la base con datos realistas para tomar 16 capturas de pantalla hoy.
**Entrega:** mañana. No hay margen para romper nada.

---

## REGLA DURA

**NO crear migraciones. NO modificar `models.py`. NO tocar vistas ni templates.**

Lo único permitido es un management command que inserte datos usando los modelos tal
como están hoy. Si algo del seed no cabe en un campo existente, se mete dentro de un
campo de texto que ya exista (por ejemplo la dirección) o se omite. No se agrega
ningún campo.

Si al leer `models.py` te parece que falta algo importante, **anotalo al final en una
sección de pendientes, pero no lo implementes.** Eso va en la fase 2.

---

## PASO 0 — Leer antes de escribir

1. Leé `models.py` de todas las apps y listá los campos reales de los modelos de
   usuario, vivienda e inspección.
2. Identificá cómo se llama el campo de zona/sector en Vivienda y si es texto libre,
   choices o FK a un catálogo.
3. Identificá los choices reales del nivel de riesgo (alto/medio/bajo) y cómo se
   calculan hoy en el clasificador.
4. Identificá los roles reales de usuario (administrador, oficinista, técnico).

Recién después de eso escribí el comando.

---

## PASO 1 — Crear el comando

`python manage.py seed_piloto`

Debe ser idempotente: si se corre dos veces, limpia lo que sembró antes y vuelve a
sembrar, sin tocar nada que no haya creado él. Usá un prefijo o una marca para poder
identificar sus propios registros.

---

## PASO 2 — Usuarios (4)

Exactamente los del piloto descrito en el capítulo:

| Rol | Nombre | Usuario | Nota |
|---|---|---|---|
| Administrador | Josué Valiente | admin | el que aparece en capturas de administración |
| Oficinista | Liz Mejía Quiroa | oficinista | la que usa reportes y exportación |
| Técnico de campo | Porfirio López Valiente | tecnico1 | |
| Técnico de campo | Elder Barrios Gómez | tecnico2 | |

Contraseña igual para todos, simple, y dejala anotada en la salida del comando.

Para la **Figura 3** (formulario de creación de usuario) conviene que exista al menos
un usuario inactivo, para que el listado muestre la eliminación lógica funcionando.

---

## PASO 3 — Zonas del casco urbano (6)

Estos son los seis barrios reales del casco urbano de San Felipe, Retalhuleu, con sus
números oficiales de casas y habitantes del Distrito No. 7. **Usá solo estos seis. No
sembrés ninguna aldea, caserío ni lotificación**, porque el capítulo delimita el alcance
al casco urbano y cualquier "ALDEA ..." que salga en una captura contradice el documento.

| Zona | Casas | Habitantes |
|---|---|---|
| Barrio El Centro | 422 | 1,463 |
| Barrio La Llovizna | 367 | 1,123 |
| Barrio El Campo | 285 | 872 |
| Barrio El Jardín | 204 | 1,020 |
| Barrio Camilo Alvarado | 174 | 520 |
| Barrio La Linterna | 109 | 533 |

Si el campo de zona en el modelo es texto libre, usá estos nombres tal cual. Si es un
catálogo con FK, sembrá el catálogo. Si tiene campos de casas o habitantes, cargalos; si
no los tiene, no los agregues.

---

## PASO 4 — Viviendas (40)

40 viviendas repartidas entre los seis barrios, con más peso en La Llovizna y El Campo
(son los de mayor riesgo real del municipio).

Sugerencia de reparto: La Llovizna 10, El Campo 9, El Centro 8, El Jardín 6,
Camilo Alvarado 4, La Linterna 3.

Cada vivienda necesita:

- Código QR generado por el flujo normal del sistema, formato `VSQR-XXXXXXXX`.
  **No inventés los códigos a mano**, dejá que los genere el modelo o el servicio que ya
  existe, para que la imagen PNG se cree igual que en producción.
- Dirección realista que incluya manzana y número de casa dentro del propio texto, así
  no hace falta migración. Formato sugerido:
  `3a. Avenida 4-15, Mz. 7 Casa 12, Barrio La Llovizna`
  Usá nomenclatura guatemalteca de calles y avenidas, no direcciones genéricas.
- Responsable de familia con nombre guatemalteco realista pero **ficticio**. No uses
  nombres de personas reales. Apellidos como De León, Tzoc, Ixcoy, Mangandí, Sontay,
  Tiguilá, Chávez, Barrios, Solís, Ramírez funcionan bien para la región.
- Número de habitantes entre 3 y 8.

De las 40, **10 quedan sin inspeccionar.** Son las que alimentan el panel de
"viviendas sin visita reciente" de la Figura 10.

---

## PASO 5 — Inspecciones (lo más delicado)

### Los números no son negociables

El Capítulo VI ya está escrito y tiene estas cifras. El seed las tiene que reproducir
o las capturas van a contradecir las tablas del propio documento:

- **30 viviendas** inspeccionadas en el piloto (las otras 10 quedan sin visita).
- Clasificación final de esas 30: **8 alto, 12 medio, 10 bajo** (Tabla 22).
- Repartidas entre los dos técnicos, aproximadamente mitad y mitad.

### Cómo lograr cada nivel

No asignés el nivel de riesgo a mano. **Sembrá los hallazgos y dejá que el clasificador
que ya existe en el sistema calcule el nivel.** Si el resultado no da 8/12/10, ajustá los
hallazgos hasta que cuadre. Esa es la prueba de que el algoritmo funciona.

Según las reglas del Capítulo V:

- **Alto (8):** presencia de larvas confirmada. Depósitos positivos ≥ 1.
- **Medio (12):** criaderos potenciales sin larvas visibles. Depósitos inspeccionados
  con agua estancada pero positivos = 0.
- **Bajo (10):** ni criaderos ni larvas.

Rellená también depósitos inspeccionados (entre 2 y 9 por vivienda), medidas de control
aplicadas (larvicida, eliminación de criaderos, fumigación programada, educación al
residente) y observaciones en lenguaje de campo real, corto y concreto. Ejemplos:
"Pila sin tapadera con larvas", "Se aplicó abate en 2 toneles", "Se orientó a la
residente sobre lavado de pila".

### Historial longitudinal (Figura 11)

El gráfico de evolución de riesgo necesita viviendas con **varias inspecciones en el
tiempo**. Tomá 5 de las 30 y dales 3 inspecciones cada una, escalonadas hacia atrás
(hace 90, 60 y 30 días aproximadamente), mostrando evolución:

- 2 viviendas que **mejoran**: alto → medio → bajo.
- 2 viviendas que **empeoran**: bajo → medio → alto.
- 1 vivienda que **se mantiene** en alto.

La inspección más reciente de cada una es la que cuenta para el conteo 8/12/10.

### Seguimiento prioritario (Figura 12)

El panel lista viviendas de riesgo alto según los días transcurridos desde la última
inspección, con el protocolo MSPAS de 7 días. Para que la captura muestre algo útil:

- 3 viviendas de riesgo alto con última inspección hace **más de 7 días** (aparecen como
  visita urgente).
- 5 viviendas de riesgo alto con última inspección **dentro de los 7 días**.

### Fechas

Repartí las inspecciones en los últimos 60 días, de lunes a viernes, en horario de
jornada (7:00 a 16:00). Nada de inspecciones de domingo a las 3 de la mañana.

---

## PASO 6 — Auditoría (Figura 13)

El registro de auditoría debe tener movimiento de los tres módulos, no solo
inspecciones. Si el sistema escribe auditoría automáticamente al crear registros, con el
seed ya queda poblado. Si no, generá entradas de creación y modificación de usuarios,
viviendas e inspecciones, atribuidas a los cuatro usuarios y con fechas coherentes con
los registros.

---

## PASO 7 — Verificación antes de entregar el comando

Corré el comando y validá con shell o con queries que:

1. Hay 40 viviendas, 30 con al menos una inspección y 10 sin ninguna.
2. El conteo por nivel de riesgo de la última inspección de cada vivienda es
   exactamente **8 alto, 12 medio, 10 bajo**.
3. Los códigos QR se generaron todos y los PNG existen en disco.
4. El reporte de riesgo por zona muestra La Llovizna y El Campo con la mayor proporción
   de riesgo alto.
5. El reporte de productividad muestra a los dos técnicos con cargas parecidas.
6. La exportación a Excel y a CSV corre sin error y abre bien con acentos.
7. No se creó ninguna migración nueva: `python manage.py makemigrations --check --dry-run`
   debe salir limpio.

Si algo de esto falla, arreglalo en el seed, no en el modelo.

---

## PASO 8 — Entregables

1. El management command.
2. Un bloque corto en el README con cómo correrlo dentro de Docker.
3. La lista de los 4 usuarios con su contraseña.
4. **Una lista ordenada de las 16 capturas a tomar**, en el orden de las figuras del
   capítulo, indicando para cada una qué URL abrir y con qué usuario entrar. Las figuras
   7, 8 y 9 son de dispositivo móvil, así que indicá cuáles tomar desde el teléfono.

El orden de las figuras es:

1. Login
2. Panel de mantenimiento de usuarios
3. Formulario de creación de usuario
4. Listado de viviendas con búsqueda y filtros
5. Detalle de vivienda con QR
6. Vista de impresión del QR
7. Escaneo de QR desde móvil
8. Formulario de inspección
9. Resultado de inspección con riesgo automático
10. Panel de trazabilidad con métricas
11. Historial longitudinal de vivienda
12. Seguimiento prioritario de alto riesgo
13. Registro de auditoría
14. Panel de reportes
15. Reporte de inspecciones con filtros
16. Archivo Excel exportado

---

## PENDIENTES PARA DESPUÉS DE LA ENTREGA — NO HACER AHORA

Anotá esto en un archivo aparte del repo. Es la fase 2, para el Trabajo Final del 9 de
noviembre, derivada del análisis de los formatos oficiales del MSPAS que usa la
oficinista del Centro de Salud.

1. **Tabla hija `DepositoInspeccion`** con los 9 tipos del Formulario A-1:
   pilas, toneles, llantas, floreros, cubetas, árbol y plantas, pozos y similares,
   tanques, otros. Campos: inspeccionados y positivos por tipo.
2. **Campo `clase_trabajo`** en Inspección, con los valores reales del programa:
   ENC (encuesta), VERIF (verificación), ACCIÓN, TRATAMIENTO, FUM (fumigación).
3. **Campos propios** en Vivienda para manzana y número de casa, hoy embebidos en la
   dirección.
4. **Tres índices entomológicos** calculados por zona y periodo en el módulo de reportes:
   - Índice de Casas = casas positivas ÷ casas inspeccionadas × 100
   - Índice de Breteau = recipientes positivos ÷ casas inspeccionadas × 100
   - Índice de Recipientes = recipientes positivos ÷ recipientes inspeccionados × 100
   - Estratificación por Índice de Casas: menos de 10 BAJO, de 10 a 25 MEDIANO,
     25 o más ALTO. Estos cortes están deducidos de la hoja de estratificación 2026 del
     Centro de Salud y **hay que confirmarlos con la oficinista** antes de la defensa.
5. **Exportación en layout oficial**: hoja con la estructura del Formulario A-1 y hoja
   con la estructura del consolidado mensual de Vigilancia y Control del Dengue.

6. **Comando `importar_formatos`**, separado del seed. Lee los archivos Excel reales que
   entrega el Centro de Salud y carga los registros a la instancia de producción.

Nada de esto toca el clasificador de riesgo por vivienda que ya existe. Ese se queda
como está, porque es el que sustenta el 96.7 % de concordancia reportado en el capítulo.

### Regla de separación: demo y producción nunca se mezclan

El proyecto tiene dos comandos de carga de datos y **jamás se combinan**:

| Comando | Qué carga | Dónde corre | Para qué sirve |
|---|---|---|---|
| `seed_piloto` | Datos ficticios | Local y entornos de prueba | Capturas del documento académico, demos, pruebas |
| `importar_formatos` | Datos reales del Centro de Salud | Solo producción | Operación real del programa de ETV |

`importar_formatos` debe:

- Negarse a correr si `DEBUG=True`, y abortar con mensaje claro.
- Negarse a correr si detecta en la base registros creados por `seed_piloto`. Primero hay
  que limpiarlos.
- Leer los Excel desde una ruta pasada por argumento, nunca desde archivos versionados en
  el repo. **Ningún Excel con datos reales se sube a Git**, ni aunque el repositorio sea
  privado: un repo privado se clona a laptops, se comparte y se forkea.
- Validar antes de insertar y reportar las filas que rechaza, sin abortar todo el lote.
- Ser idempotente por correlativo y fecha, para que correrlo dos veces no duplique.

`seed_piloto`, por el contrario, debe negarse a correr si `DEBUG=False`.

### Qué datos reales importa, y cuáles no

Importa únicamente lo de vigilancia entomológica: viviendas, inspecciones, depósitos por
tipo y consolidados mensuales, provenientes del Formulario A-1 y del consolidado de
Vigilancia y Control del Dengue.

**No importa fichas epidemiológicas ni el formato MHT.** Esos contienen nombre completo,
fecha de nacimiento, teléfono y resultados de laboratorio de pacientes, y además son de
otro programa (casos humanos y malaria), fuera del alcance de este sistema. En Guatemala
el Decreto 57-2008 clasifica el estado de salud como dato sensible, conocible solo por su
titular, y el Centro de Salud es sujeto obligado. No se cargan, no se versionan, no
aparecen en capturas ni en anexos.

### Fuera de alcance, decidido y documentado

No se integran, por delimitación del proyecto:

- Control de insecticidas y medicamentos (es gasto e insumos, no vigilancia entomológica).
- Formato de control MHT (es vigilancia de malaria, no de dengue, y contiene datos de
  pacientes).
- Fichas epidemiológicas (contienen nombre, fecha de nacimiento, teléfono y resultados de
  laboratorio de pacientes reales; quedan fuera también por protección de datos
  sensibles y no deben aparecer ni en anexos).
- Análisis de sala situacional en PowerPoint (es un producto analítico derivado; el
  sistema entrega el consolidado exportado que le sirve de insumo).
- Formulario A-5 de identificación de muestras larvarias (es trabajo de laboratorio de
  entomología, género y especie).
