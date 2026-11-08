# BRIEF FASE 2 — VectorScan QR — Importación de formatos oficiales MSPAS

Para Claude Code. Deriva del análisis de los Excel oficiales del MSPAS que usa la
oficinista del Centro de Salud de San Felipe, Retalhuleu. Este brief traduce esa
estructura a cambios concretos en el proyecto Django.

---

## REGLA DURA (leer antes de tocar nada)

1. **NO romper lo que ya funciona.** El clasificador de riesgo por vivienda (alto/medio/
   bajo) sostiene el 96.7 % de concordancia ya reportado en el documento de graduación.
   **No se toca su lógica.** Lo de esta fase es ADICIONAL.
2. **El seed del piloto (`seed_piloto`) no se modifica.** Sigue generando los datos demo
   tal cual (40 inspecciones, 30 viviendas, 8/12/10, 6 barrios del casco urbano).
3. Todo cambio de modelo va con su **migración**; no se editan migraciones ya aplicadas.
4. **Pedir confirmación al usuario antes de correr `makemigrations`/`migrate`.**
5. Trabajar en una rama nueva (`feature/fase2-importacion`), no en `main`.

---

## CONTEXTO: qué Excel entran y cuáles NO

**Entran (vigilancia entomológica):**
- `FORMULARIO A1-ENC-CENSO` → hoja `ENC1` (núcleo de inspección, 9 tipos de depósito)
- `ENCUESTAS Y VERIFICACIONES DENGUE 2026` → hoja `2026` y `EST. SALA` (índices entomológicos)
- `VIGILANCIA Y CONTROL MENSUAL DEL DENGUE 2026` → hojas por mes + `INF` (consolidado)

**NO entran (decidido y documentado, Decreto 57-2008):**
- Control de insecticidas y medicamentos (gasto e insumos)
- Formato control MHT (malaria, datos de pacientes)
- Fichas epidemiológicas (datos sensibles de pacientes)
- Resumen A-5 (laboratorio de entomología)
- Sala situacional (producto derivado)

---

## PARTE 1 — CAMBIOS DE MODELO (requieren migración)

### 1.1 Nueva tabla `DepositoInspeccion` (hija de Inspeccion)

Los 9 tipos de depósito oficiales del Formulario A-1 (hoja ENC1), cada uno con
inspeccionados y positivos. Confirmado contra el Excel real:

```python
class DepositoInspeccion(models.Model):
    TIPOS = [
        ('PILAS', 'Pilas'),
        ('TONELES', 'Toneles'),
        ('LLANTAS', 'Llantas'),
        ('FLOREROS', 'Floreros'),
        ('CUBETAS', 'Cubetas'),
        ('ARBOL_PLANTAS', 'Árbol y plantas'),
        ('POZOS', 'Pozos y similares'),
        ('TANQUES', 'Tanques'),
        ('OTROS', 'Otros'),
    ]
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='depositos')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    inspeccionados = models.PositiveIntegerField(default=0)
    positivos = models.PositiveIntegerField(default=0)
```

Nota: esto NO reemplaza los campos `num_depositos`/`depositos_positivos` que ya existen en
Inspeccion (los usa el clasificador). Esta tabla los DESGLOSA por tipo. El total debe
cuadrar con los campos existentes; agregar validación opcional que avise si no cuadran,
pero sin bloquear.

### 1.2 Campo `clase_trabajo` en Inspeccion

Valores confirmados en los Excel (hoja INF del consolidado):

```python
CLASE_TRABAJO = [
    ('ENC', 'Encuesta'),
    ('VERIF', 'Verificación'),
    ('ACCION', 'Acción'),
    ('PLAN', 'Plan'),
    ('TRATAMIENTO', 'Tratamiento'),
    ('FUM', 'Fumigación'),
]
clase_trabajo = models.CharField(max_length=15, choices=CLASE_TRABAJO, default='ENC')
```

### 1.3 Campos de ubicación en Vivienda

Hoy `direccion` es texto libre. El Formulario A-1 separa manzana y número de casa:

```python
manzana = models.CharField(max_length=20, blank=True)       # columna MZ
numero_casa = models.CharField(max_length=20, blank=True)   # columna CASA
```

Mantener `direccion` como está (no migrar datos viejos a la fuerza; los nuevos campos
son opcionales).

### 1.4 (Opcional, recomendado) Catálogo `Zona`

Hoy `Vivienda.zona` es texto libre. El brief del piloto traía cifras oficiales por barrio
del Distrito No. 7. Un catálogo evitaría inconsistencias:

```python
class Zona(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    total_casas = models.PositiveIntegerField(default=0)
    total_habitantes = models.PositiveIntegerField(default=0)
```

Si se agrega, `Vivienda.zona` pasaría a FK en una migración posterior. **Dejar para el
final**, no es bloqueante.

---

## PARTE 2 — REPORTES: 3 ÍNDICES ENTOMOLÓGICOS

Calcular por zona y periodo (mes). Fórmulas oficiales confirmadas contra la hoja
`ENCUESTAS Y VERIFICACIONES`:

- **Índice de Casas (I.C.)** = casas positivas ÷ casas inspeccionadas × 100
- **Índice de Breteau (I.B.)** = recipientes positivos ÷ casas inspeccionadas × 100
- **Índice de Recipientes (I.R.)** = recipientes positivos ÷ recipientes inspeccionados × 100

**Estratificación por I.C. — cortes CONFIRMADOS con los datos reales del MSPAS:**

- I.C. < 10 → **BAJO**
- I.C. ≥ 10 y < 25 → **MEDIANO**
- I.C. ≥ 25 → **ALTO**

(Verificado contra la hoja EST. SALA: 48.1/30/26 = ALTO; 24/20.3/14.8/13.7 = MEDIANO;
5.5/3.7/0 = BAJO.)

**IMPORTANTE:** estos índices son por ZONA (agregados), distintos del riesgo por VIVIENDA
que ya existe. No confundir ni mezclar las dos lógicas. El riesgo por vivienda se queda
intacto; esto es un reporte nuevo agregado.

Entregable: una vista/reporte nuevo "Índices Entomológicos por Zona" con filtro de mes,
que muestre por cada zona: casas insp/pos, recipientes insp/pos, I.C., I.B., I.R. y el
estrato (BAJO/MEDIANO/ALTO) con color semáforo.

---

## PARTE 3 — EXPORTACIÓN EN LAYOUT OFICIAL

Dos exportaciones nuevas en Excel (openpyxl), replicando la estructura oficial:

1. **Formulario A-1** — una hoja con las columnas de la hoja ENC1: No. Orden, HAB, P/O,
   MZ, CASA, casas insp/pos, y los 9 tipos de depósito (insp/pos cada uno), criadero,
   pupas, abate.
2. **Consolidado mensual de Vigilancia y Control del Dengue** — estructura de la hoja
   mensual: localidad, personas orientadas, viviendas (insp/pos/abatizadas/
   deschatarrizadas/fumigadas), depósitos (insp/pos/tratados), muestras, clase.

No es necesario que sea pixel-perfect; sí que tenga las mismas columnas y orden para que
la oficinista pueda usarlo.

---

## PARTE 4 — COMANDO `importar_formatos`

Management command separado del seed. Requisitos:

- Nombre: `python manage.py importar_formatos --archivo <ruta.xlsx> --tipo <a1|encuestas|consolidado>`
- **Se niega a correr si `DEBUG=True`** (es solo de producción). Candado cruzado con el
  seed: `seed_piloto` solo corre con DEBUG=True, `importar_formatos` solo con DEBUG=False.
- **Se niega a correr si detecta registros creados por `seed_piloto`.** Primero hay que
  limpiarlos. (Detectar por los usuarios demo tecnico1/tecnico2, o por el campo `es_demo`
  si se agrega — ver nota abajo.)
- Lee los Excel desde una ruta por argumento, **nunca versionada en Git** (agregar
  `*.xls`, `*.xlsx` al `.gitignore` si no están ya).
- **Valida antes de insertar.** Reporta las filas rechazadas (con número de fila y motivo)
  sin abortar el lote completo.
- **Idempotente** por correlativo + fecha (no duplica si se corre dos veces).
- Importa SOLO vigilancia entomológica. **Rechaza explícitamente** si le pasan fichas
  epidemiológicas o formato MHT (datos sensibles de pacientes, Decreto 57-2008).

**Nota sobre idempotencia:** hoy no hay campo "origen/demo" en los modelos. Considerar
agregar `es_demo = models.BooleanField(default=False)` a Vivienda/Inspeccion para
distinguir limpiamente datos demo de datos reales, en vez de depender de los usuarios.
Esto facilita el candado del comando. Decisión del usuario.

---

## ORDEN SUGERIDO DE TRABAJO

1. Rama `feature/fase2-importacion`.
2. Modelos: `DepositoInspeccion`, `clase_trabajo`, `manzana`/`numero_casa` (+ `es_demo` si
   se aprueba). Migración. **Confirmar antes de migrar.**
3. Reporte de índices entomológicos por zona (Parte 2).
4. Exportaciones en layout oficial (Parte 3).
5. Comando `importar_formatos` (Parte 4).
6. Catálogo `Zona` al final, si se decide (1.4).

Cada paso: correr las pruebas existentes antes y después para confirmar que el clasificador
y el seed siguen intactos.

---

## CHECKLIST DE NO-REGRESIÓN (correr tras cada cambio)

- [ ] `seed_piloto` sigue generando 40 inspecciones / 30 viviendas / 8-12-10
- [ ] El clasificador de riesgo por vivienda devuelve los mismos resultados
- [ ] Las vistas de paneles siguen mostrando "viviendas inspeccionadas" (fix previo)
- [ ] Ninguna migración vieja fue modificada
- [ ] Los Excel reales no quedaron versionados en Git
