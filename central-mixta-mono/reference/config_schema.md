# Esquema del config

Ver `ejemplo_config_campo_demo.json` (datos ficticios) para un caso completo con tres alternativas.

## cliente
`nombre`, `ubicacion` (vacía por defecto), `fecha`.

## documento
| Clave | Uso |
|---|---|
| `titulo`, `subtitulo`, `eyebrow`, `intro` | Portada |
| `mostrar_recupero` | Se pregunta en cada caso. `true`: ahorro año 1 / año 2+, repago y tabla de recupero |
| `mostrar_ahorro` | Filas económicas de la comparativa (default true) |
| `mostrar_mes_a_mes` | Tabla mensual (default true) |
| `mostrar_modos` | Tabla "Qué cambia entre una y otra" (default true) |
| `texto_modos` | Reemplaza el párrafo introductorio de esa tabla |
| `nota_generacion` | Pie de la tabla mensual |
| `nota_comparativa` | Nota bajo la comparativa. Si falta y el esquema es el estándar, se genera sola; `""` la saca |
| `nota_financiacion` | Pie de los presupuestos |
| `borrador` | `true` o un texto: marca de agua en todas las páginas, para versiones con datos provisorios |
| `mostrar_cierre` | Frase final al pie del documento (default: no) · `frase_cierre` la cambia · `cierre` agrega una línea de contacto |

## consumo
`distribuidora`, `tipo_usuario`, `periodo_analizado`, `texto` (opcional, reemplaza el párrafo),
`meses_kwh` (12 valores, **enero a diciembre** calendario), `tarifa`:

- `modo`: `"bloque"` con `tramos: [{hasta, precio_kwh, cargo_fijo}]` (último `hasta: null`) o
  `"plano"` con `precio_kwh` y `cargo_fijo`.
- `cargo_variable_kwh`, `leyes_frac`, `iva_frac`, `fijos_exentos`, `precio_inyeccion_kwh` (opcional).

## sistema
`panel_wp`, `limite_mono_kwp` (default 10), `generacion_base: {paneles, mensual_kwh[12]}`.

## supuestos
`autoconsumo_dia_frac` (0,5), `bateria_eficiencia` (0,9), `reserva_bateria_kwh` (0), `tc`,
`mes_inicio_idx` (8 = septiembre), `anios_sin_inyeccion` (1), `aumento_anual_usd` (0,10),
`degradacion` (0,005), `horizonte_anios` (25).

## alternativas (2 o 3; al menos una de cada modo)
`id`, `nombre`, `modo` (`"off_grid"` | `"hibrido"`), `paneles`, `generacion_mensual_kwh` (opcional),
`inversor_kw`, `inversor_desc`, `bateria_kwh` (nominal, se muestra), `bateria_util_kwh` (se calcula),
`bateria_desc`, `resumen`, `presupuesto_nro`, `items: [[ítem, descripción, cant]]`,
`subtotal_usd`, `iva_usd`, `total_usd`, `inversion_usd` (opcional),
`financiacion: [[modalidad, anticipo, cuota, total]]`.

## cargas (opcional)
`[{nombre, potencia_w, circuito: "respaldo" | "red"}]`. Si está, arma las dos listas de circuitos;
si no, se usan `respaldo.esenciales` y `respaldo.diferibles`.

## respaldo (opcional; sin él no hay sección de cortes)
`motivo`, `autonomia_ejemplo`, `descarga_max_kw`, `nota`.

## Otros
`modos_comparacion: [[fila, off grid, híbrida]]`, `proximos_pasos: [texto]`,
`condiciones: [[clave, texto]]`, `fichas: [{img, cat, name, sub, specs: [[k, v]]}]`
(imágenes en `assets/`).

## Agregados
- `documento.valorizar_inyeccion`: el crédito por inyección entra en la factura con el sistema (default = `mostrar_recupero`).
- `consumo.estimado`: sin facturas previas; cambia los textos a consumo y factura estimados frente a la red.
