---
name: habilidad-armado-de-presupuesto-y-analisis
description: >
  Genera la propuesta/presupuesto en PDF de Oriens Energía Solar a partir del presupuesto
  de componentes, la simulación de generación y las fichas técnicas de los equipos. Sirve
  para proyectos industriales/comerciales On Grid, residenciales híbridos con batería, y
  off-grid con 2-3 alternativas de batería comparadas lado a lado. Usar SIEMPRE que un
  asesor de Oriens pida "armá la propuesta", "generá el presupuesto", "hacé el PDF para el
  cliente", "propuesta solar para [cliente]", "comparame estas opciones de batería", o
  cuando haya presupuesto de equipos + simulación/estimación de generación y el objetivo
  sea un documento comercial con ahorro, recupero y financiación — empresa o casa, con o
  sin batería, con o sin inyección a red. También al actualizar una propuesta ya hecha, o
  al buscar datos que la alimentan (irradiación vía PVGIS, tarifa eléctrica, tipo de
  cambio). NO usar para el plano de paneles en el techo ni para una factura aislada.
---

# Propuesta Oriens (industrial y residencial)

Genera el PDF comercial de 5 páginas, marca Oriens, que se entrega al cliente de una
central fotovoltaica — de autoconsumo industrial/comercial, o residencial con batería.
El resultado es un documento pulido con portada + resumen, fichas técnicas con fotos,
generación vs. consumo, ahorro, análisis de recupero, financiación en cuotas y próximos
pasos.

## Cómo funciona

Todo el documento se arma con un builder parametrizado que lee un archivo de
configuración JSON con la data del proyecto y produce el PDF. No hay que tocar el HTML:

```bash
pip install weasyprint --break-system-packages     # si hace falta
python scripts/build_propuesta.py mi_config.json "Propuesta Cliente.pdf"
```

Sin argumentos usa `reference/ejemplo_config.json` (proyecto JG Envases, industrial). **La
forma recomendada de empezar un proyecto nuevo es copiar el ejemplo que más se parezca al
caso y cambiar los valores** — ver "Qué ejemplo copiar" más abajo.

Las fuentes Poppins (títulos) y Lato (cuerpo) suelen estar en el sistema; si no, el
render igual sale (usa una sans por defecto). El logo de Oriens va como cabezal en todas
las hojas y está recreado en vector dentro del builder.

## Qué builder / ejemplo usar

Hay **dos builders** y **tres ejemplos completos** en `reference/`. Elegí según la forma
del proyecto:

| Proyecto | Builder | Ejemplo | Cuándo |
|---|---|---|---|
| Industrial/comercial, On Grid, sin batería | `build_propuesta.py` (modo plano) | `ejemplo_config.json` (JG Envases) | Autoconsumo directo simple, un solo costo de kWh, un % de autoconsumo fijo. |
| Residencial híbrido con batería, **un solo escenario** | `build_propuesta.py` (`"modo": "mensual_escalonado"`) | `ejemplo_config_residencial.json` (Tallarico) | Hay batería y/o la generación está desalineada del consumo mes a mes (ej. losa radiante en invierno), tarifa por tramo de consumo mensual. PDF: `ejemplo_tallarico.pdf`. |
| Off-grid, **2 o 3 alternativas de batería a comparar** en el mismo documento | `build_propuesta_offgrid.py` | `ejemplo_config_offgrid.json` (Ferrero) | El asesor quiere mostrarle al cliente 2-3 tamaños de batería lado a lado (mismo arreglo solar e inversor), sin inyección a red. PDF: `ejemplo_ferrero.pdf`. Ver `reference/metodologia_offgrid.md`. |

Si dudás entre el modo `mensual_escalonado` de `build_propuesta.py` (un escenario) y
`build_propuesta_offgrid.py` (2-3 escenarios comparados): la pregunta clave es si el
asesor quiere **una sola propuesta** o **varias alternativas una al lado de la otra** en
el mismo PDF. Un solo escenario con batería → `build_propuesta.py`. Comparativa de
baterías → `build_propuesta_offgrid.py`.

## Qué necesitás juntar antes (inputs)

Preguntá o buscá en los archivos que aporte el asesor:

1. **Presupuesto de componentes**: lista de ítems con cantidad y el precio total del
   proyecto en USD (sin IVA). De acá salen la tabla de componentes y `inversion_usd`.
2. **Simulación de generación** (software tipo PVsyst / similar, o estimada con
   **PVGIS** — https://re.jrc.ec.europa.eu/pvg_tools/en/, la fuente estándar de Oriens
   para irradiación solar): generación anual y mensual en kWh. Si viene en MWh, convertir
   a kWh (× 1000) — **el documento usa kWh en todo, misma unidad, para no confundir.** Si
   no hay simulación profesional, cargá ubicación, kWp, orientación e inclinación en
   PVGIS y usá su generación mensual estimada; aclaralo en `nota_consumo`/
   `nota_autoconsumo` como estimación (no simulación certificada). Ver
   `reference/metodologia.md` → "De dónde sale la generación" para el detalle y fuentes
   alternativas.
3. **Consumo del predio/hogar**: idealmente 12 meses reales de las facturas; si hay
   menos, anualizar el promedio y aclararlo en `nota_consumo`. En proyectos
   residenciales con tarifa escalonada, conviene tener el desglose de la factura
   (cargo variable por tramo, cargo fijo, recargos, IVA) — ver `desglose_tarifa_html`.
4. **Fichas técnicas de los equipos** (PDF del fabricante): para extraer las fotos del
   panel, inversor y batería si no hay preset para ese equipo (ver catálogo abajo).
5. **Datos del cliente**: razón social o nombre, domicilio, N° de presupuesto, fecha.
6. **Tipo de cambio (`tc`) y costo real del kWh**: si no te los pasan, hay que buscarlos
   (BNA venta del día; tarifa de la distribuidora/cooperativa de la zona).

Si falta algo que cambia los números (consumo anual, precio, split de paneles), **pedilo
antes de generar** en vez de inventarlo.

## Checklist: qué hace que un presupuesto sea preciso

Esta es la lista completa de variables que definen si el número final (ahorro, repago,
cuotas) es confiable o es una aproximación gruesa. Antes de generar, repasala y marcá
qué falta — no hace falta tener el 100%, pero cada campo que falta hay que aclararlo en
el config (`nota_consumo`, `nota_autoconsumo`, etc.) en vez de dejarlo implícito.

**Del lado del consumo (la variable que más mueve el resultado):**
- Consumo real de 12 meses (facturas), no un promedio estimado — sobre todo si hay
  estacionalidad (riego, aire acondicionado, calefacción eléctrica).
- Para proyectos con batería: qué fracción del consumo es diurna vs. nocturna
  (`autoconsumo_directo_frac` / `autoconsumo_dia_frac` según el builder). **Default:
  asumí 50% día / 50% noche y no lo preguntes de entrada** — es la política de Oriens.
  Sólo usá un split distinto si el asesor te lo aclara explícitamente para ese cliente
  puntual (ver el caso "Ezequiel" en el historial, donde pasar de 40/60 a 35/65 movió el
  repago de 4a6m a 5 años — por eso no conviene inventarlo).

**Siempre preguntá (no asumas ni inventes) estos cuatro datos, salvo que ya te los
hayan dado:**
1. **Ubicación exacta** del proyecto (para PVGIS y para la propuesta).
2. **Orientación** de los paneles.
3. **Inclinación** de los paneles.
4. **Presupuesto de componentes** (precio de cada ítem/total). Este suele venir en un
   **Excel adjunto** del asesor — revisá si te pasó uno antes de preguntar por los
   números a mano.

**Del lado de la factura (para el costo real del kWh):**
- El desglose completo, no sólo el cargo variable: cargo fijo, impuestos directos
  (provinciales, municipales) y si el IVA se recupera o no (empresa vs. vivienda
  particular cambia el cálculo).
- Si la tarifa tiene tramos por volumen de consumo mensual, el precio y cargo fijo de
  cada tramo (no un promedio).
- Nombre de la distribuidora/cooperativa y categoría tarifaria — sirve para validar el
  número contra otra factura de la zona si hace falta.

**Del lado de la generación:**
- Simulación profesional (PVsyst o similar) si existe. Si no, PVGIS con ubicación exacta
  (lat/long), kWp, orientación e inclinación reales — no un promedio genérico de la
  región.
- Si el sistema es off-grid o híbrido con batería chica: cuánta generación diaria hay de
  margen sobre el consumo diurno (para saber si además de cubrir el directo, sobra para
  cargar la batería).

**Del lado de los equipos:**
- Presupuesto de componentes con precio total en USD sin IVA — de un proveedor real, no
  estimado.
- Marca/modelo exacto de cada equipo (para elegir el preset correcto o armar la ficha a
  mano) y su garantía.
- Si hay batería: capacidad total, cuántas unidades, y si el asesor quiere reservar
  capacidad fija para autonomía ante cortes (y cuánta).

**Supuestos económicos (estos sí tienen default razonable, pero conviene confirmarlos
si el proyecto es grande o el cliente pregunta de dónde salen):**
- Tipo de cambio del día (BNA venta).
- Aumento anual de tarifa + inflación en USD asumido (default 10%).
- Tope de precio del kWh a 12 años (default USD 0,18, ver metodología).
- % de mantenimiento anual y % de degradación de paneles.

**Del lado comercial:**
- N° de presupuesto, condiciones de pago/financiación vigentes (adelanto, cuotas, TNA),
  y si el cliente tiene alguna condición particular (permuta, descuento, plazo especial).

## Armar el config

Copiá el ejemplo que corresponda (ver "Qué ejemplo copiar") y editá los campos. Los más
importantes:

- `titulo`, `cliente`, `ubicacion`, `presupuesto`, `fecha`, `subtitulo`
- `sistema`: n_paneles, panel_wp, paneles_chapa, paneles_plano, inversor_marca,
  inversor_kw, n_inversores. (kWp se calcula solo = n_paneles × panel_wp / 1000.)
- `sistema_titulo`, `sistema_texto`, `nota_inversor`: prosa de la página 1.
- `nombre_lugar` (opcional): cómo referirse al sitio en el texto ("del hogar", "del
  establecimiento"...). Default: "del predio".
- `texto_intro`, `desglose_tarifa_html` (opcional): en proyectos residenciales con
  tarifa por tramos conviene escribir el párrafo de intro a mano con el desglose real de
  la factura, en vez de dejar el texto genérico por defecto.
- `componentes`: filas `[n, "Componente", "Descripción", "Cant."]`.
- `inversion_usd` y `iva` (0.21 por defecto; en residencial el IVA suele no recuperarse,
  aclarar esto en `nota_financiacion`). El total con IVA se calcula y se muestra debajo
  del total sin IVA.
- `consumo.anual_kwh` + `consumo.mensual_kwh` (dict Ene…Dic en kWh).
- `generacion.anual_kwh` + `generacion.mensual_kwh` (dict Ene…Dic en kWh).
- `economia`: supuestos del modelo de recupero. Dos modos — ver
  `reference/metodologia.md` para las fórmulas completas:
  - **Modo plano** (sin `"modo"`, o industrial): `costo_real_kwh_ars`, `autoconsumo`
    (fracción fija), `valor_inyeccion_ars`.
  - **Modo `"mensual_escalonado"`** (residencial/batería): `tarifas` (tramo, precio bajo
    y alto, cargo fijo), `bateria_kwh_mes`, `bateria_eficiencia`,
    `autoconsumo_directo_frac`, `leyes_frac`, `iva_frac_energia`, `tasa_municipal_ars`.
  - Comunes a ambos modos: `valor_inyeccion_ars`, `tc`, `aumento_anual`, `tope_usd_kwh`,
    `degradacion`, `mantenimiento`, `factor_co2`.
- `financiacion`: filas `["Nombre", adelanto_frac, cuotas, TNA_frac]`.
- `fichas`: 4 productos típicamente (panel, inversor, batería si hay, estructura). Usá
  **presets** para equipos recurrentes (ver "Catálogo de equipos"); o ficha completa
  (`img`, `name`, `sub`, `specs`) para equipos nuevos.
- `condiciones`: pasos de "Cómo avanzamos".

Los cálculos de ahorro, recupero, payback y cuotas los hace el builder — no los pongas a
mano. Ver `reference/metodologia.md` para las fórmulas y de dónde salen los supuestos.

## Catálogo de equipos (presets)

Para que los equipos que se repiten en casi todos los proyectos usen **siempre la misma
imagen y descripción**, en lugar de escribir la ficha a mano se usa un *preset*. Una
entrada de `fichas` puede ser un preset `{"preset": "...", ...}` y el builder la expande
sola. Usá presets siempre que apliquen — es la forma de mantener todas las propuestas
consistentes.

| Preset | Cuándo usarlo | Parámetros | Qué fija |
|---|---|---|---|
| `panel_jinko` | Paneles Jinko Tiger Neo bifacial N-type | `wp` (default 620) | Imagen + descripción del panel; sólo cambia la potencia Wp |
| `panel_amerisolar` | Paneles Amerisolar Mono PERC 144 celdas, All Black (usado en proyectos off-grid residenciales) | `wp` (default 550) | Imagen + descripción del panel; sólo cambia la potencia Wp |
| `inversor_growatt` | Inversor **Growatt On Grid** trifásico de **50, 80, 100 o 125 kW** | `kw`, `modelo` opcional | Imagen + descripción; VA = kW×1,11, DC ≈ kW×1,5 |
| `inversor_growatt_chico` | Growatt On Grid mono/trifásico chico (≤10 kW), residencial sin batería | `kw` (default 10) | Imagen + descripción básica |
| `inversor_deye_hibrido` | Inversor **Deye híbrido** (con batería) mono/trifásico, hasta 20 kW | `kw` (default 15), `modelo` opcional | Imagen + descripción; modo híbrido y on-grid |
| `inversor_deye_hibrido_grande` | Deye híbrido trifásico de mayor porte, 50 a 125 kW | `kw` (default 50) | Imagen + descripción |
| `inversor_deye_offgrid` | Deye off-grid (sin conexión a red), típico 6 kW | `kw` (default 6) | Imagen + descripción |
| `inversor_huawei` | Inversor Huawei On Grid trifásico | `kw` (default 20) | Cambia de imagen según sea ≤20 kW o 20-150 kW |
| `bateria_deye` | Batería Deye de baja tensión, línea SE-F | `kwh` (default 16), `modelo` opcional | Imagen + descripción, LiFePO4, 10 años garantía |
| `bateria_pylontech_fidus` | Batería Pylontech Fidus 16 kWh todo-en-uno | — | Imagen + descripción fija |
| `bateria_pylontech_uf5000` | Batería Pylontech UF5000 5 kWh formato rack | — | Imagen + descripción fija |
| `estr_coplanar` | Estructura coplanar de aluminio sobre chapa | `paneles` opcional | Imagen + descripción |
| `estr_techo_plano` | Estructura triangular de aluminio con lastres | `paneles` opcional | Imagen + descripción |
| `estr_piso` | Estructura de piso para terrenos/parques solares | `paneles` opcional | Imagen + descripción |
| `estr_tejas` | Estructura para techo de tejas (ganchos + riel) | `paneles` opcional | Imagen + descripción |
| `estr_miniriel` | Estructura de perfil bajo, mini-riel sobre chapa | `paneles` opcional | Imagen + descripción |

Ejemplo de `fichas` con presets, caso residencial con batería (equivale a la ficha de
Tallarico):

```json
"fichas": [
  {"preset": "panel_jinko", "wp": 620},
  {"preset": "inversor_deye_hibrido", "kw": 15},
  {"preset": "bateria_deye", "kwh": 16},
  {"preset": "estr_coplanar", "paneles": 30}
]
```

Reglas:
- Si el inversor es un **Growatt On Grid de 50/80/100/125 kW**, usá `inversor_growatt`.
  Si es un **Deye híbrido**, usá `inversor_deye_hibrido` (≤20 kW) o
  `inversor_deye_hibrido_grande` (50-125 kW). No reescribas la ficha a mano en estos
  casos — sólo cambiá el `kw`.
- Si son **paneles Jinko Tiger Neo**, usá `panel_jinko` (cambiá `wp` sólo si la potencia
  del módulo es otra).
- Si la **estructura es una de las cinco del catálogo**, usá el preset correspondiente.
- Si el equipo es distinto (otra marca/modelo, o un preset que todavía no existe),
  escribí la ficha completa a mano (dict con `img`, `name`, `sub`, `specs`), agregá su
  imagen a `assets/`, y considerá sumar el preset nuevo a `catalogo_ficha` en
  `scripts/build_propuesta.py` si es un equipo que se va a repetir.

Los presets viven en `scripts/build_propuesta.py` (función `catalogo_ficha`). Para sumar
un equipo nuevo al catálogo, agregá un caso ahí.

## Imágenes de los componentes

Las imágenes de las fichas van en `assets/`. Ya vienen 8: panel Jinko, panel Amerisolar,
inversor Growatt, inversor Deye, estructura coplanar, estructura triangular con lastres,
estructura mini-riel y batería Pylontech Fidus — reutilizadas por los presets de arriba
(el mismo `img_inversor_deye.png` sirve para `inversor_deye_hibrido` e
`inversor_deye_offgrid`; para `inversor_deye_hibrido_grande` conviene conseguir una foto
del modelo de mayor potencia si un proyecto lo necesita). **Todas deben quedar sobre
fondo blanco**, igual que la hoja. Los presets `inversor_growatt_chico`,
`inversor_deye_hibrido_grande`, `inversor_huawei`, `bateria_deye` y
`bateria_pylontech_uf5000`, y las estructuras `estr_piso`/`estr_tejas`, todavía no tienen
imagen — hay que generarla la primera vez que un proyecto los necesite.

Para un proyecto con equipos distintos, o para sumar la imagen que falte de un preset:

1. Extraé la foto del PDF del fabricante:
   `pdfimages -all ficha.pdf /tmp/x` → tomá la imagen más grande. Si tiene `smask`,
   ese es el canal de transparencia.
2. Limpiá el fondo con `scripts/prep_images.py`:
   - `python scripts/prep_images.py whiten foto.jpg assets/img_panel.png` (crema→blanco)
   - `python scripts/prep_images.py smask render.png render_smask.png assets/img_estr_plano.png` (aplica transparencia + recorta)
3. Apuntá el `img` de la ficha al archivo en `assets/`.

Regla clave: el recuadro de la ficha (`.fimg`) tiene fondo blanco, así que cualquier
tono crema/gris del render tiene que blanquearse para que no se note el borde.

## Estilo (no cambiar salvo pedido)

Tipografías Poppins + Lato; acentos dorado (#c99320) y verde (#4e9e3a); bordes
redondeados; barras del gráfico redondeadas (consumo gris oscuro, generación dorada);
formato de moneda argentino ($ 1.234.567,89 · USD 40.053). Son las convenciones de marca
de Oriens; mantenelas para que todas las propuestas se vean iguales.

## Estructura del documento (5 páginas — `build_propuesta.py`)

Esta estructura aplica a `build_propuesta.py` (industrial y residencial de un solo
escenario). `build_propuesta_offgrid.py` genera un documento de **3 páginas** con otra
estructura (lectura de consumo + factura, presupuestos comparativos + condiciones,
comparativa + metodología) — ver `reference/metodologia_offgrid.md` para el detalle.

1. **Portada**: título, cliente, resumen en 4 tarjetas (paneles / % menos / inversión /
   recupero), sistema propuesto, tabla de componentes con total sin y con IVA.
2. **Fichas técnicas**: los productos del proyecto (panel, inversor, batería si hay,
   estructura) con foto sobre blanco + specs.
3. **Generación y aprovechamiento**: gráfico consumo vs. generación (kWh), tabla mensual,
   cobertura (%, autoconsumo/inyección, tCO₂).
4. **Ahorro + Recupero**: ahorro a precio de hoy y tabla de recupero a 12 años con el año
   de repago resaltado.
5. **Financiación + Próximos pasos**: cuotas y condiciones, siempre juntos en la última
   hoja.

## Verificación antes de entregar

Renderizá el PDF a imágenes y revisá cada página (números que cierren, fondos blancos,
que entre en 5 páginas):

```bash
pdftoppm -png -r 100 "Propuesta Cliente.pdf" /tmp/chk
```

Chequeá que: el total con IVA = inversión × (1 + iva); cobertura = generación/consumo;
el año resaltado del recupero sea donde el acumulado supera la inversión; que
financiación + próximos pasos queden en la página 5; y en proyectos con batería, que el
autoconsumo/déficit mensual tenga sentido (no puede ser mayor al consumo del mes).

Para `build_propuesta_offgrid.py`, además: que el % de autoconsumo de cada escenario sea
mayor cuanto más grande la batería; que la fila de "Repago estimado" tenga sentido junto
a la inversión y el ahorro año 1; y que con 3 escenarios las columnas de la página de
presupuestos no queden demasiado apretadas (si es así, achicar la descripción de los
componentes o pasar a propuestas individuales).

## Errores ya cometidos — no repetirlos

Lista viva de correcciones reales sobre propuestas ya entregadas (origen: caso Castresana,
ago-2026, industrial/comercial On Grid sin batería). Cada vez que un asesor corrija algo de
fondo — no sólo texto o formato — sumá acá qué pasó y cómo evitarlo la próxima vez.

- **Autoconsumo en modo plano: nunca lo calcules con el total anual.** Si el asesor da un
  split día/noche del consumo (ej. "40% diurno, 60% nocturno") y pedís cubrir el 100% del
  consumo diurno, NO hagas `min(generación_anual, 0.4×consumo_anual) / generación_anual`
  — eso asume que se puede "compensar" un mes de baja generación con el excedente de otro
  mes, cosa que sin batería es imposible (cada mes se autoconsume como mucho lo que ese mes
  genera). Calculá **mes a mes**: `autoconsumo_mes = min(generación_mes, 0.4×consumo_mes)`,
  sumá los 12 meses, y dividí por la generación anual. El resultado real suele ser bastante
  más bajo que el atajo anual (Castresana: 89% real vs. 94% calculado con el atajo). Esto
  cambia el ahorro anual (aunque no necesariamente el payback, si ya está topeado — ver el
  punto siguiente).

- **El tope `tope_usd_kwh` es un TECHO al crecimiento futuro, nunca un PISO que baje el
  valor de hoy.** Si el costo real de hoy en USD (`usdkwh1`) ya supera el tope configurado
  (pasa en cuentas con mucho impuesto no recuperable, ver punto de Monotributo abajo), la
  fórmula ingenua `min(usd_kwh_1 × (1+aumento)^(y-1), tope)` colapsa TODO el año 1 — y los
  12 años — al tope, subestimando el ahorro real desde el primer día. Ya está corregido en
  `scripts/build_propuesta.py` (`tope_efectivo = max(tope_usd_kwh, usdkwh1)`), pero si tocás
  esa función de nuevo, no reintroduzcas el bug.

- **`costo_real_kwh_ars`: nunca incluyas el Cargo Fijo / potencia contratada de la
  factura, ni cargos puntuales (mora, tasa de rehabilitación/reconexión).** El cargo fijo
  no varía con el consumo y la central no lo reduce (el cliente sigue necesitando la
  conexión de respaldo) — dividir la factura COMPLETA entre los kWh consumidos infla el
  costo real y exagera el ahorro. Restá esos cargos antes de dividir por los kWh del
  período. Esto ya estaba en la metodología pero conviene remarcarlo: es el error más fácil
  de cometer al leer una factura por primera vez.

- **Si la factura dice "Responsable Monotributo", el cargo tipo "IVA Monotributo" (o
  equivalente) SÍ hay que incluirlo en el costo real** — al revés del supuesto por defecto
  de "empresa recupera el IVA" (que aplica a Responsable Inscripto). Fijate siempre la
  condición fiscal de la cuenta antes de asumir qué se recupera y qué no; si el titular de
  la factura no coincide con el cliente del proyecto (cuenta a nombre de otra persona,
  típico cuando no se actualizó el titular ante la distribuidora), preguntá antes de
  asumir la condición fiscal del cliente real.

- **Historial de consumo en la factura: si el asesor dice "están los datos", buscá el
  gráfico de barras que imprime la distribuidora (aunque sea una imagen dentro del PDF)
  antes de asumir que sólo hay un mes o pedir que te lo pasen de nuevo.** Se puede leer con
  precisión razonable: `pdftoppm -r 300` para renderizar la página a alta resolución,
  recortar la zona del gráfico con PIL, y medir con numpy la altura en píxeles de cada
  barra contra el eje (detectar filas de píxeles "verdes"/de color de barra, y calibrar la
  escala con al menos un valor exacto conocido — el ciclo más reciente suele estar en el
  detalle de facturación de esa misma factura). Aclarar siempre en `nota_consumo` que son
  lecturas aproximadas del gráfico, salvo el valor exacto usado para calibrar.

- **Estructura de montaje: seguí siempre lo que dice el presupuesto/cotizador real del
  asesor, no lo que "suena parecido" en el catálogo.** Coplanar y mini-riel son productos
  distintos (aunque los dos van sobre chapa) — si el cotizador dice "mini-riel", usá el
  preset `estr_miniriel`, no `estr_coplanar` por default. Ídem con cualquier ficha: si el
  asesor edita una ficha para sacar una línea de specs (ej. "Garantía: a confirmar"),
  escribila a mano sin preset en vez de forzar el preset genérico.

- **Financiación: si el presupuesto/cotizador ya tiene su propia tabla de cuotas y TNA,
  usá esos valores reales — no los defaults genéricos de otro proyecto (Mercedes/JG
  Envases).** Para reconstruir la TNA real a partir de una cuota ya cotizada, probá values
  candidatos en la fórmula francesa (`cuota = saldo × r/(1-(1+r)^-cuotas)`, `r=TNA/12`)
  hasta que la cuota calculada coincida con la del cotizador.

- **Propuesta que se manda directo al cliente (no a través de un asesor intermediario):
  nunca escribas "según lo indicado por el asesor" ni "estimación provista por el
  asesor".** El texto va en la voz de Oriens, sin mencionar a un asesor como tercero, aunque
  los datos hayan salido de la charla con el asesor. Preguntá de entrada si la propuesta es
  para mandar directo al cliente o para que el asesor la revise primero.

- **Cuando el asesor pida sacar una sección o comprimir páginas** (ej. sacar "Análisis de
  recupero" y unir Financiación con Ahorro en una sola hoja): el layout está hardcodeado en
  `build_propuesta.py` con un `<div class="page">...</div>` por hoja — sacar el bloque de
  HTML de la sección pedida y borrar el `</div>` + `<div class="page">` que separa las dos
  hojas que hay que unir. Verificar siempre con `pdftoppm` que el contenido resultante entre
  en una sola hoja sin cortarse (si no entra, achicar texto o dejarlo en dos hojas y
  avisarle al asesor).

- **Si el asesor pide "dame en Word para corregir yo"**: generar un `.docx` con `docx`
  (npm) con todo el contenido de texto/tablas — no hace falta replicar el diseño de marca,
  eso lo pone el builder al final. Cuando el asesor devuelva el documento corregido (a
  veces como link de Google Docs en vez de un archivo), leer el contenido con
  `mcp__Google_Drive__read_file_content` (pasando el fileId de la URL) y comparar contra el
  texto original campo por campo para detectar los cambios reales — no asumir que no hay
  cambios ni pedir que los liste de nuevo. Aplicar los cambios detectados al config JSON y
  regenerar el PDF final con el builder; no convertir el Word directamente a PDF (pierde
  todo el diseño de marca).
