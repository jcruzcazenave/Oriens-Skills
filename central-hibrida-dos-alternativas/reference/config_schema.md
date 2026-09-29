# Esquema del config

Ejemplos reales completos: `ejemplo_config_van_waarde.json` (mismo arreglo, con recupero) y `ejemplo_config_muglia.json` (distintos paneles y baterías, sin recupero). Este esquema corresponde al builder flexible (`build_propuesta_hibrido_flex.py`), que también acepta los configs del builder original.

## Bloques

### Identidad
`titulo`, `subtitulo`, `cliente`, `ubicacion` (dejarla vacía: no se menciona dónde vive el cliente), `fecha`, `telefono` (opcional: si falta, no se dibuja el recuadro de consultas), `factura.distribuidora`, `factura.tarifa`

### `opciones` (builder flexible)
| Campo | Qué es |
|---|---|
| `mostrar_recupero` | `true` por defecto. `false`: sin repago; la inyección no se valoriza (sólo energía) |
| `filas_comparativa` | Lista de claves, en orden. Si falta, se usa el default según `mostrar_recupero` |

Claves de `filas_comparativa`: `configuracion`, `almacenamiento`, `generacion_anual`, `generacion_vs_consumo`, `consumo_cubierto`, `autoconsumo_inyeccion`, `red_kwh`, `inyeccion_kwh`, `inversion_con_iva`, `inversion_pesos`, `factura_actual`, `factura_con_sistema`, `factura_con_sistema_sin_iny`, `ahorro_anual_factura`, `reduccion_factura`, `ahorro_a1`, `ahorro_desde_a2`, `reduccion_a1_a2`, `repago`, `respaldo`. Las cuatro de recupero (`ahorro_a1`, `ahorro_desde_a2`, `reduccion_a1_a2`, `repago`) exigen `mostrar_recupero: true`.

Defaults: con recupero → configuracion, almacenamiento, generacion_anual, generacion_vs_consumo, autoconsumo_inyeccion, red_kwh, inversion_con_iva, inversion_pesos, ahorro_a1, ahorro_desde_a2, reduccion_a1_a2, repago, respaldo. Sin recupero → configuracion, almacenamiento, generacion_anual, generacion_vs_consumo, consumo_cubierto, red_kwh, inyeccion_kwh, factura_actual, factura_con_sistema_sin_iny, respaldo.

### `sistema_compartido`
`n_paneles`, `panel_wp`, `kwp`, `inversor_kw` — común a todas las alternativas. Si las alternativas difieren en paneles, estos campos van dentro de cada escenario y este bloque se puede omitir.

### `consumo` y `generacion`
`anual_kwh` más `mensual_kwh` con las doce claves `Ene`…`Dic`. El consumo sale del cuadro comparativo de la factura, **asignado al mes calendario de lectura**; la generación, del simulador de Oriens, de PVGIS o de la planilla reescalada. Si cada alternativa tiene su propia generación, `generacion` se omite y va `generacion_mensual_kwh` en cada escenario.

### `metodologia`
| Campo | Qué es |
|---|---|
| `orientacion`, `inclinacion_deg` | Para el texto de la metodología |
| `rendimiento_kwh_kwp`, `perdidas_frac` | Idem |
| `autoconsumo_dia_frac` | Fracción diurna por defecto |
| `autoconsumo_dia_frac_mensual` | Override por mes; omitir si aplica a todo el año |
| `bateria_dod`, `bateria_eficiencia` | Defaults 0,90 y 0,96 |
| `mes_inicio_idx` | Mes de puesta en marcha, 0 = enero |
| `carga_respaldo_kw` | Carga asumida para calcular horas de autonomía |

### `economia`
| Campo | Qué es |
|---|---|
| `costo_real_kwh` | `(cargo_variable + transporte) × multiplicador` |
| `valor_inyeccion_kwh` | 50% del promedio de los cargos variables de todos los tramos, sin impuestos. Se ignora si `mostrar_recupero: false` |
| `cargo_fijo_mensual` | Cargo fijo del tramo vigente × multiplicador + alumbrado público + servicios sociales (si son fijos) |
| `tc` | BNA venta del día |
| `aumento_anual` | 0.10 |
| `degradacion` | 0.005 |
| `mantenimiento` | 0.0 en el formato de 4 páginas |
| `inversion_con_iva` | `true` si el IVA no se recupera |
| `anios_sin_inyeccion` | 1 por defecto |

### `escenarios` (2 o 3)
| Campo | Qué es |
|---|---|
| `nombre`, `nombre_corto`, `resumen` | Títulos de la tarjeta y de la columna |
| `bateria_kwh` | **Capacidad que entra al cálculo** (ej. 16.076) |
| `bateria_kwh_nominal` | **Lo que se imprime** (ej. "16,1"). Nunca redondear `bateria_kwh` |
| `bateria_label` | Texto de la fila "Almacenamiento" |
| `inversion_usd`, `inversion_usd_con_iva` | Del presupuesto |
| `componentes` | Lista de `[ítem, descripción, cantidad]` |
| `financiacion` | Lista de `[modalidad, adelanto, cuota, total, tna]`. La TNA es opcional: si ninguna fila la trae, la columna no se dibuja |
| `respaldo_kwh_utiles` | Opcional. Si se omite, se calcula como capacidad × DoD |
| `n_paneles`, `kwp`, `inversor_kw` | Opcionales: arreglo propio de la alternativa (si no, `sistema_compartido`) |
| `generacion_mensual_kwh` | Opcional: curva propia de la alternativa (si no, `generacion.mensual_kwh`) |

### Textos
`texto_lectura_consumo` (HTML), `intro_presupuestos`, `condiciones` (opcional, lista de `[título, texto]`), `intro_comparativa`, `nota_comparativa` (HTML, opcional), `intro_balance` (opcional), `metodologia_titulo` (opcional; default según haya recupero), `metodologia_sub` (ej. "En seis pasos."; tiene que coincidir con la cantidad de pasos), `metodologia_html` (`<ol class="mlist">`), `notas_financiacion`, `proximos_pasos` (opcional).
