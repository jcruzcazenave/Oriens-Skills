# Metodología económica y supuestos

Este documento explica cómo el builder calcula el ahorro, el recupero (payback) y la
financiación, y de dónde salen los supuestos por defecto. Todo esto vive en el bloque
`economia` y `financiacion` del config; el builder no inventa nada, solo aplica estas
fórmulas.

Hay **dos modos** de cálculo en `economia`, elegidos con el campo `"modo"`:

- **Modo plano** (sin `"modo"`): un solo costo de kWh y un % de autoconsumo fijo todo el
  año. Pensado para proyectos **industriales/comerciales** sin batería, con tarifa de un
  solo precio. Ejemplo: JG Envases.
- **Modo `"mensual_escalonado"`**: calcula mes a mes, con tarifa por tramos de consumo y
  balance de batería. Pensado para proyectos **residenciales con batería** y/o generación
  desalineada del consumo (ej. pico de consumo en invierno por calefacción eléctrica,
  justo cuando menos genera el sistema). Ejemplo: Tallarico.

## De dónde sale la generación (kWh)

Lo ideal es una **simulación profesional** (PVsyst o similar) que entregue kWh mensuales
para la ubicación, orientación e inclinación exactas del proyecto — es lo que se usó en
JG Envases y Tallarico.

Cuando no hay simulación disponible, la fuente estándar de Oriens para estimar
generación a partir de la **irradiación solar del lugar** es **PVGIS** (Photovoltaic
Geographical Information System, de la Comisión Europea —
https://re.jrc.ec.europa.eu/pvg_tools/en/). Usalo siempre como primera opción:

- Es un simulador online, no sólo un dato de irradiación: permite cargar la ubicación
  exacta (lat/long), la potencia pico (kWp), la orientación e inclinación de los paneles,
  y devuelve directamente la **generación mensual estimada en kWh** para ese sistema —
  más preciso que aplicar una fórmula manual sobre un promedio de irradiación.
- Tiene la herramienta "PVGIS estimation utility" / "Grid-connected" en el sitio; también
  se puede consultar por API (`https://re.jrc.ec.europa.eu/api/...`) si hace falta
  automatizarlo.
- Cubre bien Argentina y el resto de Sudamérica (usa la base de datos satelital NSRDB /
  ERA5 según la región).

Citá siempre en `nota_consumo` o `nota_autoconsumo` del config que la generación es una
**estimación con PVGIS** (no una simulación certificada tipo PVsyst), con la fecha de
consulta. Si por algún motivo PVGIS no cubre la zona, como respaldo están **Global Solar
Atlas** (globalsolaratlas.info, promedio diario kWh/m²/día) o **NASA POWER**
(power.larc.nasa.gov, series históricas) — pero PVGIS es la referencia por defecto.

Si necesitás la fórmula manual (por ejemplo partiendo de un dato de irradiación en vez de
usar la salida directa de PVGIS):

```
generación mensual (kWh) ≈ irradiación (kWh/m²/día) × días del mes × kWp × PR
```

`PR` (performance ratio) conservador: 0,75–0,80 (pérdidas por temperatura, cableado,
inversor, suciedad).

## Costo real del kWh (input, no se calcula acá)

### Modo plano

`costo_real_kwh_ars` es el costo real del kWh que hoy paga el cliente, **con los impuestos
no recuperables incluidos** (Contribución Municipal, Decreto-Ley provincial, etc.) pero
**sin IVA ni percepciones** (que el cliente recupera, típico de empresa/comercio). Sale
del análisis de la factura del predio. Ejemplo JG Envases: $116,5/kWh.

**Excluí siempre el Cargo Fijo (cargo por potencia contratada) del cálculo.** Es un cargo
por capacidad, no por energía: no varía con el consumo y la central solar no lo reduce en
absoluto (aunque el cliente genere el 100% de su energía, sigue pagando el mismo cargo
fijo). Metelo en la cuenta y vas a inflar artificialmente el costo real del kWh — caso real
(Castresana): incluir el cargo fijo daba $506,9/kWh, excluirlo daba $393,5/kWh. Lo mismo
para cargos puntuales de un solo ciclo que no son parte del costo recurrente de la energía
(mora, tasa de reconexión/rehabilitación, etc.) — tampoco entran.

**Excepción: si el cliente está facturado como Monotributo, el "IVA Monotributo" (o cargo
equivalente, ~27%) SÍ es un costo no recuperable y hay que incluirlo.** Es distinto del IVA
de una empresa Responsable Inscripto (que si se recupera y por eso se excluye por regla
general de arriba). Verificá la condición fiscal en la factura antes de asumir cuál aplica.

### Modo `mensual_escalonado`

Acá no hay un único costo — se reconstruye la factura completa por tramo, mes a mes, con
`economia.tarifas` (`limite_kwh`, `precio_bajo`, `precio_alto`, `cargo_fijo_bajo`,
`cargo_fijo_alto`) más `leyes_frac` (recargos provinciales), `iva_frac_energia` (**sólo
distinto de 0 si el cliente NO recupera el IVA**, típico de una vivienda particular — para
comercial/industrial dejalo en 0, como en el modo plano) y `tasa_municipal_ars` (cargo
fijo mensual, ej. alumbrado público). Todos estos valores salen de leer la factura real
del cliente (y opcionalmente la de un vecino con consumo en el otro tramo, para validar
el precio del segundo escalón) — no se inventan.

## Balance mensual con batería (sólo modo `mensual_escalonado`)

Para cada mes, el builder reparte la generación en este orden de prioridad (así es como
un sistema híbrido real prioriza el uso de la energía):

1. **Autoconsumo directo**: cubre el consumo diurno del mes (`autoconsumo_directo_frac ×
   consumo_mes`), limitado por lo que efectivamente se generó ese mes. **Default 0,5
   (50% día / 50% noche) si el campo no está en el config** — política Oriens: asumí
   50/50 salvo que el asesor confirme un split distinto para ese cliente puntual: no lo
   preguntes de entrada ni lo infieras de supuestos (losa radiante, aire acondicionado,
   etc.), sólo actualizalo si te dan un dato mejor.
2. **Carga de batería**: lo que sobra de generación después del directo, hasta el tope
   mensual `bateria_kwh_mes` (capacidad × ciclos que carga en el mes).
3. **Excedente inyectado**: lo que sobra de generación después de directo + batería, se
   paga a `valor_inyeccion_ars`.
4. **Déficit comprado a la red**: consumo nocturno no cubierto por la batería (aplicando
   `bateria_eficiencia`, la pérdida round-trip de cargar/descargar), se paga al precio
   del tramo tarifario de ese mes.

El costo "sin central" y "con central" de cada mes se arma con precio de energía +
cargo fijo del tramo correspondiente, más leyes/IVA/tasa municipal si aplican, y se suman
los 12 meses para el ahorro anual.

## Valor de la energía solar (usd/kWh año 1, para la tabla de recupero)

### Modo plano

```
valor_blend ($/kWh) = autoconsumo × costo_real_kwh_ars + (1-autoconsumo) × valor_inyeccion_ars
USD/kWh año 1        = valor_blend / tc
```

- `autoconsumo` = fracción que se consume en el momento (default 0,90). El resto se
  inyecta a la red y se paga peor.
- `valor_inyeccion_ars` = precio conservador de la inyección (default $70/kWh).
- `tc` = tipo de cambio (BNA venta) para pasar a USD.

**Cómo derivar `autoconsumo` cuando el asesor da un objetivo de cobertura diurna** (ej.
"cubrir el 100% del consumo diurno, que es el 40% del consumo total"): NO uses los totales
anuales directamente (`min(generación_anual, 0,4×consumo_anual) / generación_anual`) — sin
batería, un mes con poca generación no se puede compensar con el excedente de otro mes.
Calculá mes a mes con los 12 valores de `consumo.mensual_kwh` y `generacion.mensual_kwh`:

```
autoconsumo_mes_i = min(generación_mes_i, frac_diurna × consumo_mes_i)
autoconsumo = Σ autoconsumo_mes_i (12 meses) / generación_anual
```

El resultado real casi siempre es más bajo que el atajo anual, porque en los meses de menor
generación (otoño-invierno en el hemisferio sur) el sistema autoconsume el 100% de lo que
genera pero no llega a cubrir el objetivo diurno, mientras que en los meses de mayor
generación sí lo cubre y además inyecta excedente — ese excedente de los meses buenos no
"rellena" el déficit de los meses flojos. Contáselo al asesor con el detalle mes a mes
(qué meses cubren el 100% diurno y cuáles no) en `nota_autoconsumo`, no sólo con el
número final.

### Modo `mensual_escalonado`

`USD/kWh año 1 = (ahorro_total_del_año / generación_anual) / tc` — es el ahorro real
(ahorro por energía no comprada + lo cobrado por excedente inyectado) dividido por toda la
energía generada, para tener un valor "por kWh generado" comparable al modo plano.

## Ahorro "a precio de hoy"

Modo plano:

```
autoconsumo_kwh = autoconsumo × generacion_anual
energia_con_central = consumo_anual − autoconsumo_kwh
costo_sin = consumo_anual × costo_real_kwh_ars
costo_con = energia_con_central × costo_real_kwh_ars
ahorro_anual = costo_sin − costo_con
% menos = ahorro_anual / costo_sin
```

Modo `mensual_escalonado`: `costo_sin` y `costo_con` son la suma de los 12 meses (ver
"Balance mensual" arriba), y al ahorro se le suma lo cobrado por excedente inyectado.

En ambos modos es un número congelado a precio de hoy; en la realidad crece con la
tarifa. Sobre el cargo por potencia contratada no hay ahorro (la red sigue como respaldo).

## Recupero (payback) a 12 años

Por cada año `y` (1..12), igual en ambos modos:

```
tope_efectivo = max( tope_usd_kwh , usd_kwh_1 )
generacion_y  = generacion_anual × (1 − degradacion)^(y−1)
usd_kwh_y     = min( usd_kwh_1 × (1 + aumento_anual)^(y−1) , tope_efectivo )
ahorro_bruto  = generacion_y × usd_kwh_y
ahorro_neto   = ahorro_bruto − mantenimiento × inversion_usd
acumulado    += ahorro_neto
```

El **payback** es el año donde el acumulado supera la inversión; el builder calcula los
meses exactos por interpolación (ej: "4 años 4 meses") y resalta esa fila.

**Ojo con `tope_usd_kwh` como piso, no sólo como techo.** El tope existe para no proyectar
un crecimiento de precio sin límite a 12 años — pero NUNCA debe pisar el valor real de HOY
(`usd_kwh_1`). En cuentas con mucho impuesto no recuperable (ej. un cargo tipo "IVA
Monotributo" del 27%), el costo real de hoy en USD puede terminar por encima del tope
histórico de 0,18 — si ahí se usara `min(..., tope_usd_kwh)` a secas, el año 1 (y los 12
años) quedarían aplastados al tope, por debajo de lo que el cliente paga hoy, subestimando
el ahorro real desde el primer momento. Por eso el techo efectivo es
`max(tope_usd_kwh, usd_kwh_1)`: sigue limitando cuánto puede CRECER el valor a futuro, pero
nunca lo baja por debajo de lo medido hoy.

Supuestos por defecto (conservadores):

| Supuesto | Default | Sentido |
|---|---|---|
| `aumento_anual` | 0,10 | Aumento del **costo + inflación en dólares** de la tarifa. |
| `tope_usd_kwh` | 0,18 | Techo del precio; no sube más. ≈ promedio LatAm, por debajo de EE.UU. (~0,19) y Europa (~0,25). |
| `degradacion` | 0,004–0,005 | Pérdida de los paneles por año (0,4–0,5%). |
| `mantenimiento` | 0,01 | 1% de la inversión por año. |
| `factor_co2` | 0,000351 | tCO₂ evitadas por kWh (para la métrica ambiental). |

En el documento, el aumento del 10% se rotula **"Aumento del costo + inflación (USD)"**,
no "aumento real" (aclaración pedida por el equipo). Y el tope de 0,18 se acompaña del
comentario de que es aprox. el promedio de kWh en Latinoamérica, menor que EE.UU. y Europa.

## Financiación (sistema francés)

Se calcula sobre el **total con IVA** (`inversion_usd × (1+iva)`). En proyectos donde el
cliente recupera el IVA (empresa/comercio) se aclara que igual se financia por
desembolsarse por adelantado; en proyectos donde NO se recupera (vivienda particular) se
aclara que es parte del costo real, no un adelanto financiero — el texto de
`nota_financiacion` debe reflejar cuál es el caso. Cada modalidad es
`["Nombre", adelanto_frac, cuotas, TNA_frac]`:

```
adelanto = total_iva × adelanto_frac
saldo    = total_iva − adelanto
cuota    = saldo × r / (1 − (1+r)^(−cuotas))     con r = TNA/12   (francés)
total    = adelanto + cuota × cuotas
```

El "Contado fraccionado" (cuotas = 0) es sin interés: adelanto + resto post-instalación.

Defaults JG Envases (industrial, sin batería): 6c/40%/5%, 12c/30%/10%, 24c/20%/14%,
36c/15%/18%. Defaults Tallarico (residencial, con batería): 6c/40%/5%, 12c/30%/10%,
24c/20%/14% (contado fraccionado 50/50 sin interés en ambos).

## Unidades y formato

- **Energía siempre en kWh** en todo el documento (consumo y generación), para no mezclar
  GWh/MWh/kWh. Si la simulación viene en MWh, multiplicar por 1000 al cargar el config.
- Moneda argentina: `$ 1.234.567,89`. Dólares: `USD 40.053`. El builder ya formatea así.

## Origen de este modelo

El modo plano es el mismo esquema del "Proyecto Energía Solar Duke" (proyecto de
referencia de Oriens), adaptado. El ejemplo completo cargado es JG Envases (Morón), que
sirve como plantilla industrial: 122 paneles / 75,64 kWp / inversor Growatt 80 kW,
109.928 kWh/año, ~33% de cobertura, recupero 4 años 4 meses.

El modo `mensual_escalonado` se sumó para el caso Tallarico (residencial con batería,
Ranchos): 30 paneles / 18,6 kWp / inversor Deye híbrido 15 kW + batería 16 kWh,
27.126 kWh/año generados, autoconsumo ~49%, tarifa escalonada de la cooperativa local.
Sirve de plantilla para cualquier proyecto residencial con batería.

## Catálogo de equipos (presets)

Los equipos recurrentes se cargan como preset en `fichas` y el builder los expande
(`catalogo_ficha` en `build_propuesta.py`), garantizando misma imagen y descripción. Ver
la tabla completa en `SKILL.md` ("Catálogo de equipos"); resumen de los criterios de
diseño de cada familia:

- `panel_jinko` (param `wp`, default 620): paneles Jinko Tiger Neo bifacial N-type.
- `inversor_growatt` (param `kw` ∈ {50,80,100,125}, `modelo` opcional): Growatt MAX On
  Grid trifásico, para proyectos industriales/comerciales. Sólo cambia la potencia:
  **VA aparente = kW × 1,11** y **FV máx = kW × 1,5** (ratios de placa tomados del
  datasheet MAX 50–80KTL3-LV). Para 100/125 kW confirmar el código comercial exacto
  (`modelo`) si hace falta.
- `inversor_growatt_chico` (param `kw`, default 10): Growatt On Grid mono/trifásico chico,
  para residencial sin batería.
- `inversor_deye_hibrido` / `inversor_deye_hibrido_grande` (param `kw`): línea Deye
  híbrida (opera con batería y on-grid); la variante "grande" es para 50-125 kW
  trifásico.
- `inversor_deye_offgrid` (param `kw`, default 6): Deye sin conexión a red.
- `inversor_huawei` (param `kw`, default 20): Huawei On Grid, cambia de imagen según el
  rango de potencia (≤20 kW vs 20-150 kW).
- `bateria_deye` (param `kwh`, default 16), `bateria_pylontech_fidus`,
  `bateria_pylontech_uf5000`: baterías LiFePO4 de baja tensión, para proyectos híbridos.
- `estr_coplanar` / `estr_techo_plano` / `estr_piso` / `estr_tejas` / `estr_miniriel`
  (param `paneles` opcional): las cinco estructuras de montaje del catálogo, según el
  tipo de cubierta o terreno.
