---
name: "central-ongrid"
description: >
  Arma la propuesta PDF de Oriens Energía Solar para una central ON GRID sin
  batería, en UNA alternativa o en DOS/TRES alternativas comparadas (ej.
  "consumo actual" vs. "preparada para la ampliación"), con fichas técnicas con
  fotos, financiación y "Cómo avanzamos". USAR SIEMPRE que un asesor de Oriens
  pida "la propuesta on grid", "armá la propuesta de [cliente]", "central on
  grid", "propuesta sin batería", "poné dos alternativas"; cuando haya uno o más
  PRESUPUESTOS ON GRID (inversor on grid, sin batería) más la factura o la
  simulación; al actualizar una propuesta on grid, recalcular su recupero o
  volverla más conservadora. Usar también para leer la factura
  (distribuidoras y cooperativas) y sacar el costo real del kWh, o verificar
  cuántos paneles entran en el techo. Usar aunque no se diga "on grid" si hay
  inversor on grid o limitador de inyección. Usar también para comparar ON GRID
  vs. HÍBRIDA SIN BATERÍA con los mismos paneles (caso Gentile). NO usar para
  híbridos con batería (ver central-hibrida) ni off grid.
---

# Propuesta Central On Grid — una o varias alternativas

Genera el PDF comercial de Oriens para una central fotovoltaica conectada a red,
sin batería. Dos modos, dos builders que comparten motor de cálculo, gráfico y
estilo:

| Modo | Builder | Ejemplo | Páginas |
|---|---|---|---|
| **Una alternativa** (caso Llacomotti) | `scripts/build_propuesta_ongrid.py` | `reference/ejemplo_config_ongrid.json` + `ejemplo_llacomotti.pdf` | 5 |
| **Dos o tres alternativas** (caso Alaux) | `scripts/build_propuesta_ongrid_comparativa.py` | `reference/ejemplo_config_comparativa_alaux.json` + `ejemplo_alaux_comparativa.pdf` | 6 |
| **On grid vs. híbrida sin batería** (caso Gentile) | `scripts/build_propuesta_ongrid_comparativa.py` | `reference/ejemplo_config_comparativa_gentile.json` + `ejemplo_gentile_ongrid_vs_hibrida.pdf` | 6 |

Si el asesor manda más de un presupuesto del mismo cliente, o pide "dos
alternativas", usá el modo comparativo.

## Cómo funciona

Todo sale de un JSON de configuración. El builder no contiene ningún dato de
cliente:

```bash
pip install weasyprint --break-system-packages     # si hace falta
python scripts/build_propuesta_ongrid.py mi_config.json "Propuesta Cliente.pdf"
```

**Empezá copiando `reference/ejemplo_config_ongrid.json`** (caso Llacomotti,
carnicería en Pilar) y cambiando los valores. El PDF de referencia es
`reference/ejemplo_llacomotti.pdf`.

El builder calcula solo: kWp, generación anual, cobertura, autoconsumo e
inyección mes a mes, ahorro, reducción de factura, repago y la tabla de
recupero. **No pongas ningún resultado a mano en el config** — si un número te
parece mal, el que está mal es un supuesto de entrada.

## Modo una alternativa — estructura del documento (5 páginas)

1. **Lectura del consumo + presupuesto.** Portada, perfil del establecimiento,
   lectura de la factura, objetivo del cliente, recurso disponible, y la tabla de
   componentes con subtotal, IVA y total.
2. **Qué es y qué incluye.** La solución Oriens en bloques: llave en mano,
   relevamiento, autoconsumo con monitoreo, preparada para crecer, garantías y
   plazos. (Sin bloque de gestión del medidor bidireccional: ver criterios.)
3. **Resultados proyectados.** Tabla de resultados de una columna + nota que
   explica los supuestos.
4. **Generación y metodología.** Gráfico de tres series (consumo total, consumo
   diurno, generación), tabla mensual y metodología en cinco pasos.
5. **Recupero + anexo de financiación.** Tabla de recupero a 12 años con el año
   de repago resaltado, cuotas y notas.

El pie **no lleva numeración de página** (criterio del asesor). Tampoco va
recuadro de consultas con teléfono al final.

## Modo comparativo (2 o 3 alternativas) — estructura del documento

```bash
python scripts/build_propuesta_ongrid_comparativa.py mi_config.json "Propuesta Cliente.pdf"
```

Orden de páginas fijado por el asesor (caso Alaux):

1. **Portada + lectura del consumo + presupuestos lado a lado** (una caja por
   alternativa con ítems, subtotal, IVA, total y N° de presupuesto).
2. **Resultados proyectados**: tabla comparativa (una columna por alternativa,
   repago resaltado en dorado), nota del escenario conservador y **un gráfico
   de generación vs. consumo por alternativa**.
3. **Generación mes a mes** (tabla con generación y cobertura de cada
   alternativa) **+ metodología** en cinco pasos.
4. **Qué es y qué incluye** + nota "dos alternativas, dos momentos del proyecto".
5. **Fichas técnicas con fotos** (panel, inversor, estructura) + nota del
   limitador/materiales/mano de obra. Las fotos están en `assets/`.
6. **Financiación** (cuota y total por alternativa) **+ "Cómo avanzamos"** con la
   visita técnica previa como primer paso + resumen final.

**Sin tabla de recupero año por año** por defecto (el asesor la sacó: el repago
ya está en la comparativa). Si se pide, `mostrar_tabla_recupero: true` la agrega
antes de la financiación.

Los textos del config aceptan tokens que el builder completa con lo calculado:
`{rep1}` `{repopt1}` `{tot1}` `{sub1}` `{cob1}` `{gen1}` `{ahorro1}` `{iny1}`
`{kwp1}` (y `…2`, `…3`), `{dif_sub_12}`, `{dif_gen_12_pct}`, `{consumo_anual}`,
`{frac_diurno_pct}`. **Usalos en vez de escribir resultados a mano.**
Claves opcionales del modo comparativo: `cap_grafico_unico`, `cap_tabla_gen`,
`nota_presupuestos` (nota debajo de las cajas de presupuesto; si falta, no se
dibuja). El builder
imprime al final el resumen de cada alternativa para chequear.

Cómo plantear las alternativas (lo que funcionó en Alaux):
- Alt. 1 = dimensionada al **consumo actual** (mejor aprovechamiento, menos
  inyección). Alt. 2 = **preparada para la ampliación** (más paneles, mismo
  inversor): hoy inyecta más, y cuando la ampliación entre al mismo medidor ese
  excedente pasa a autoconsumirse a valor pleno.
- Las dos se calculan con el **consumo actual verificable**; la ampliación va
  como nota cualitativa. No inventar el consumo futuro.
- Si la alternativa grande se recupera antes (pasa cuando el delta de precio es
  chico: en Alaux USD 760 más por 33% más de generación), **destacarlo** en la
  nota de resultados: es el mejor argumento de venta.

## On grid vs. híbrida sin batería (caso Gentile)

Cuando el asesor pide "un esquema híbrido y otro on grid" sin batería:

- **Los mismos paneles en las dos alternativas.** Sin batería, las dos generan,
  autoconsumen e inyectan exactamente lo mismo: lo único que cambia es el
  inversor. No sumarle paneles a la híbrida "porque después va batería" (el
  asesor lo corrigió: la comparación tiene que aislar el inversor). Alcanza con
  una sola simulación.
- **Si las generaciones son idénticas, el builder muestra un solo gráfico**
  (más alto) y una sola columna de generación, en vez de duplicarlos. Texto de
  arriba del gráfico: `cap_grafico_unico`; aclaración de la tabla mensual:
  `cap_tabla_gen`.
- **`tag` de cada alternativa** ("On Grid", "Híbrida preparada para batería")
  es el encabezado de la tabla comparativa: elegilo descriptivo.
- **La diferencia de precio es lo que se vende.** La nota de resultados explica
  qué paga la diferencia con IVA. El valor de la híbrida, en palabras del asesor:
  1. **Inversor de mayor potencia** (ej. Deye 8 kW vs. Growatt 6 kW): facilita
     ampliar con más paneles el día de mañana. **No poner la cantidad de paneles
     ampliables** en el PDF (el asesor lo pidió): mencionarlo cualitativamente.
  2. **Batería a futuro sin cambiar el inversor** (cubriría la noche y los picos
     de simultaneidad).
  3. **Ante un corte de red**: el on grid se apaga por norma (anti-isla) y
     "corre la misma suerte que la distribuidora"; la híbrida puede seguir
     alimentando los **circuitos de respaldo** con los paneles. **Sin batería,
     sólo mientras haya sol y con la potencia que se esté generando**: escribirlo
     así, no "funciona sin problemas". Con batería lo haría también de noche.
     Agregar en las fichas de inversor la fila "Ante un corte de red".
- **Confirmar con el asesor** que el híbrido cotizado opera sin batería
  conectada e inyectando a red.
- **Bajada monofásica con consumos simultáneos**: el on grid (y la híbrida)
  trabaja en paralelo con la red sobre el mismo tablero; de día los equipos
  toman primero lo que generan los paneles y la red completa la diferencia, sin
  conmutaciones ni tope de carga. Alivia la bajada sólo con sol; de noche queda
  igual (eso sólo lo resuelve una batería). Presentarlo como "comparte la carga
  con la red en las horas de mayor uso simultáneo".

## Gráfico de generación vs. consumo (ambos modos)

La leyenda muestra el consumo diurno como **línea punteada con punto**, igual
que en el gráfico (no un cuadradito). Textos de leyenda: "Barra gris: consumo
total", "Línea punteada: consumo diurno (X % del consumo del mes)", "Barra
dorada: generación solar". En el modo comparativo va además un texto arriba de
los gráficos (`CAP_GRAFICO_LINEA`): mientras la barra dorada queda por debajo de
la línea, todo se autoconsume; cuando la supera, el excedente se inyecta. En el
modo de una alternativa conviene poner esa misma explicación en `cap_grafico`.

## Qué necesitás juntar antes (inputs)

1. **Presupuesto de componentes de Oriens para ESTE cliente** (uno por
   alternativa): ítems, cantidades, subtotal sin IVA, desglose de IVA, total y
   tabla de cuotas. **No se arma nada hasta tenerlo**: no extrapolar precios ni
   equipos de otro cliente, aunque haya una propuesta parecida a mano. De otra
   propuesta sólo se toma el modelo (formato y estructura), nunca datos.
2. **Factura del cliente**: consumo del período, días, cargo fijo, cargo
   variable, otros conceptos, impuestos y contribuciones, tasa municipal,
   distribuidora y categoría tarifaria. Ver "Cómo leer la factura".
3. **Simulación de generación** mensual en kWh (una por alternativa) y la
   potencia con la que se corrió. Chequeá la **localidad** elegida en el
   simulador: si no es la del cliente (ej. corrida con "Buenos_Aires" para
   Trenque Lauquen), avisale al asesor; si no hay una más cercana, se usa igual
   (queda del lado conservador). El simulador a veces muestra al lado de la
   energía anual un valor ×0,93: **usar la anual del simulador**, el 93% ya se
   aplica aparte como aprovechamiento diurno. Si no hay simulación, pedila;
   PVGIS (https://re.jrc.ec.europa.eu/pvg_tools/en/) sólo como último recurso.
4. **Ubicación, orientación, inclinación y tipo de techo.**
5. **Superficie disponible** para los paneles. Ver "Cuántos paneles entran".
6. **Tipo de cambio** BNA venta del día (buscarlo si no lo pasan).
7. **Perfil de consumo diurno/nocturno.** Default de Oriens: 50/50. Solo usar
   otro valor si el asesor lo aclara (ej. comercio que trabaja de 8 a 20: 70/30).
8. **Datos del establecimiento**: actividad, horario, equipos grandes
   (compresor, elevador), bajada mono/trifásica, techos (tipo y medidas),
   ampliaciones previstas y si quedan en el mismo medidor.

**Al asesor le gusta aclarar de entrada en vez de ir corrigiendo**: antes de
generar (o apenas termines la primera versión), preguntale lo que mueve números
o contenido — escenario del repago (conservador/optimista), cómo proyectar los
meses sin factura, tabla de recupero, si recomendar una alternativa, garantías,
errores del presupuesto — con opciones cerradas.

Si falta algo que mueve el número, **pedilo antes de generar** en vez de
inventarlo. Lo que sí se puede estimar (meses de consumo faltantes) va declarado
como estimación en el texto.

## Criterios fijos de Oriens (aplicar siempre)

- **"Mano de obra" siempre con cantidad 1**, aunque el presupuesto diga otra cosa.
- **Generación del simulador tal cual**, sin descontarle ningún porcentaje extra:
  el simulador de Oriens ya es conservador. No hace falta aclararlo al cliente.
  La única corrección legítima es por potencia del panel o por disposición
  (ver abajo).
- **Valorización de la inyección**: kWh limpio sin impuestos, tomado como
  promedio de todos los tramos del cuadro tarifario, y se reconoce el **50% de
  ese promedio** por kWh inyectado. En tarifas de un solo precio de energía, el
  promedio es ese único valor. "Limpio" = sólo el precio de la energía: **sin
  CTT ni otros cargos por kWh, sin impuestos**. Si la factura trae dos precios
  por un cambio de cuadro dentro del período (ej. 29 días a un precio y 2 a
  otro), no son tramos: usar el último vigente.
- **Financiación propia**: 6 cuotas TNA 10%, 12 cuotas TNA 12%, 24 cuotas TNA
  14%. Las tablas del presupuesto ya vienen con esos valores: reproducilas.
- Sin numeración de página en el pie y sin recuadro de teléfono al cierre.
- **Garantías, versión estándar**: paneles 12 años de producto y 30 de
  rendimiento, inversor 5 años, instalación propia 1 año.
- **Trámite del medidor bidireccional / inyección**: **no** poner en la
  propuesta que Oriens se ocupa de la gestión ante la distribuidora o
  cooperativa (el asesor lo sacó en Alaux). Sólo incluirlo si el asesor lo pide
  para ese cliente.
- **Cierre "Cómo avanzamos"** (modo comparativo, y recomendable también en el
  de una alternativa): 1) visita técnica previa para definir cuestiones técnicas
  (techo y orientación, estado de la cubierta, disposición, canalizaciones,
  ubicación del inversor, punto de conexión, coordinación con obras); 2) elección
  de alternativa y firma con anticipo; 3) provisión e instalación en 15-20 días;
  4) puesta en marcha y monitoreo. Cerrar con un resumen de las alternativas.
- **Fichas técnicas con fotos** de panel, inversor y estructura (modo
  comparativo). Imágenes en `assets/` (`img_panel.png`, `img_inversor.png` =
  Growatt, `img_estr_chapa.png` = coplanar sobre chapa, `img_estr_miniriel.png`,
  `img_estr_plano.png` = inclinable con lastres para losa,
  `img_inversor_growatt_min.png` = Growatt MIN monofásico chico,
  `img_inversor_deye.png` = Deye híbrido). La foto `img_inversor.png` es de la
  línea MAX: para un MIN usar `img_inversor_growatt_min.png`; si el asesor manda
  la hoja de datos de otro modelo, la foto se puede extraer con
  `pdfimages -png` (imagen + máscara como canal alfa).
- **Reproducir el presupuesto tal cual**: ítems, cantidades, IVA, total y
  cuotas. **Chequear siempre que el IVA cierre**: IVA 21% ÷ 0,21 + IVA 10,5% ÷
  0,105 tiene que dar el subtotal. El cotizador a veces arrastra un IVA de otro
  presupuesto (Gentile on grid: las bases daban USD 6.555 contra un subtotal de
  USD 5.755,7). Explicáselo al asesor con esa cuenta, aclarando que el error está
  en **su presupuesto** (no en la propuesta), y preguntá si el subtotal es
  correcto. Si lo confirma: mantener el IVA 10,5% si su base coincide con la de
  los paneles de otro presupuesto, recalcular el IVA 21% sobre el resto, el
  total y **las cuotas con las TNA de Oriens** (anticipo + cuota francesa sobre
  el saldo, redondeada a USD enteros), y recordarle regenerar el PDF del
  presupuesto en el cotizador para que coincida.
- **Resumen final**: no repetir la visita técnica en la nota de cierre si ya
  está en "Cómo avanzamos".

## Escenario conservador vs. optimista

El asesor puede pedir explícitamente **no sobrevender**. Estos son los cinco
parámetros que controlan qué tan exigente es el análisis:

| Parámetro del config | Optimista | Conservador |
|---|---|---|
| `escalada` (suba real de la tarifa en USD) | `0.10` | `0.0` |
| `generacion_mensual` | según simulación | ajustada por disposición (Este-Oeste: ×0,90) |
| `aprovechamiento_diurno` | `1.0` | `0.93` |
| `precio_inyeccion` | 50% del kWh limpio | `0` (el limitador recorta el excedente) |
| `mantenimiento_usd_anual` | `0` | `120` |

**Remarcarlo en negro**: el asesor pidió destacar que el repago es un panorama
conservador porque no considera aumento de la tarifa. Usar
`<b style='color:#000'>…</b>` en `intro_resultados` y en `nota_resultados`.
Si el asesor pregunta si se considera la inyección: sí, al 50% del kWh limpio;
mostrarle cuánto pesa (en Gentile, USD 253 de 1.457 al año ≈ un año de repago) y
ofrecer el repago sin inyección como piso si el trámite del medidor puede
demorarse.

En el caso Llacomotti, el escenario conservador movió el repago de 1 año 7 meses
a 2 años 1 mes. **Cuando se usa el escenario conservador, hay que decirlo en el
documento**: la nota de resultados enuncia los supuestos como decisión de Oriens
y cierra con el resultado que daría el escenario optimista, para que el plazo
informado funcione como piso y no como promesa. Ver `nota_resultados` y el paso 4
de `metodologia` en el ejemplo.

## Cómo leer la factura

1. **Verificá que la factura del mes cierre**: cargo fijo + cargo variable +
   otros conceptos = "conceptos eléctricos". Después conceptos eléctricos +
   impuestos y contribuciones + tasa municipal = factura del mes.
2. **Cuidado con el saldo anterior.** El "total a pagar" puede incluir deuda de
   períodos previos. Para el ahorro se usa la factura del mes, no el total.
3. **Cruzá contra el gráfico de composición del valor** (generación /
   distribución / impuestos) si la factura lo trae: tiene que dar parecido.
4. **Costo real del kWh (el número que va al PDF)**: cargo variable ÷ kWh, y a
   ese valor sumarle los impuestos en la proporción que representan sobre los
   conceptos eléctricos. No incluir cargo fijo ni "otros conceptos": no se van
   con el sol. No usar el promedio de la factura completa: sobreestima.
5. **Evolución anual**: el gráfico de barras suele venir en **kWh/día** — hay
   que multiplicar por los días del período. Verificá contra el consumo del mes
   en curso para confirmar la unidad y si el ciclo es mensual o bimestral.
   **Cooperativas (ej. Trenque Lauquen, T1G)**: el gráfico de evolución suele
   venir en **kWh/mes** (la barra del período coincide con el consumo leído):
   verificalo igual. Tomá los últimos 12 meses y descartá el mes repetido del
   año anterior.
6. **Situación IVA**: si el cliente no lo recupera (consumidor final, no
   categorizado), el repago va sobre la inversión **con** IVA
   (`base_repago: "con_iva"`). Si es **Responsable Inscripto**, el repago va
   `"sin_iva"` **y el costo del kWh también se calcula sin IVA**: sólo cargo
   variable (energía + CTT/cargos por kWh) más los tributos de arrastre
   proporcionales (en cooperativas bonaerenses suelen venir como % sobre el
   subtotal: leyes provinciales, alumbrado público, fondo compensador, IIBB).
   Ej. Alaux: 263,16 $/kWh variable × 1,325 = 349 $/kWh (con IVA daría 420).
   La factura anual para la reducción (%) va en la misma base.
7. Si faltan meses, estimarlos con la forma de la curva real y la regla que dé
   el asesor (ej. "verano el doble que invierno"), y **declararlo como estimación
   en el texto**.
8. **Consumo que cambió de nivel (reforma, equipos nuevos).** Si el asesor
   confirma que el aumento "llegó para quedarse", proyectar con el perfil
   posterior: meses reales posteriores al cambio tal cual; meses previos =
   su kWh/día real + la carga base nueva (ej. heladera, lavavajillas,
   lavarropas, horno: ~6-7 kWh/día), sin sumar calefacción fuera del invierno.
   Declararlo como estimación. La factura anual (`factura_anual_ars`) se
   proyecta con ese consumo: precio vigente × kWh + cargo fijo × 12, por
   (1 + % impuestos) + tasa municipal × 12.
9. **Suba del precio del kWh**: si entre facturas cambió la categoría (ej. Edenor
   R5 → R6 por mayor consumo), parte de la suba es el cambio de categoría y no
   aumento de tarifa: escribirlo así ("pasó de $147 a $190, por las subas de
   tarifa y por el cambio de categoría"), no como "la tarifa subió 29%".
10. **Edenor residencial (T1-R)**: gráfico de evolución en kWh/día, etiquetado
   por mes de liquidación (26/06 = período 28/05–26/06); faltan meses si hubo
   huecos. Cargo variable de precio único por categoría: el limpio es el último
   vigente del detalle de la liquidación.
11. **Perfil estacional**: si el consumo pica en invierno (cuando menos genera
   el sol), en esos meses todo lo generado se autoconsume y en primavera-verano
   sobra para inyectar. Presentarlo como estrategia: "atacar el invierno y
   compensar con la inyección del resto del año". Si el asesor dice "parejo todo
   el año" y la factura muestra otra cosa, usar la curva de la factura y
   comentárselo.

## Cuántos paneles entran (restricción de superficie)

Cuando el techo es el límite y no el presupuesto, verificá antes de generar. Para
un panel de 630 Wp (2,38 × 1,13 m ≈ 2,70 m² de módulo) sobre **losa**, con
separación entre filas para no sombrearse:

| Disposición | m² por panel | Rendimiento relativo |
|---|---|---|
| Norte, 15° | ~3,8 | 100% |
| Norte, 10° | ~3,5 | ~97% |
| Este-Oeste, 10° enfrentados | ~2,9 | ~90% |

Si los paneles del presupuesto no entran en la superficie declarada, decilo al
asesor con el número concreto y proponé la disposición Este-Oeste, que es la
salida estándar. En el texto del PDF, la superficie queda atada al relevamiento
técnico previo, presentado como servicio de Oriens y no como duda pendiente.

## Errores a chequear en el presupuesto antes de generar

Aparecen seguido por arrastre de presupuestos anteriores:

- **Potencia del panel distinta a la de la simulación.** Si la simulación se
  corrió con otro Wp, escalá la generación por la relación de potencias y
  avisale al asesor.
- **Estructura equivocada para el techo.** Coplanar es para chapa o teja; sobre
  **losa** va kit inclinable con lastres (más caro, y suma 15-20 kg/m² a la
  losa). Si el techo es de losa y el presupuesto dice coplanar, marcalo.
- **Marca del limitador de inyección** que no coincide con el inversor. En el PDF
  se escribe sin marca: "compatible con el inversor instalado".
- **Inversor muy sobredimensionado.** No es un error: es el argumento
  "Preparada para crecer". Calculá cuántos paneles más admite y decíselo al
  asesor; en el PDF, mencionarlo sin la cantidad salvo que el asesor la pida.
- **Diseño de strings.** Con paneles de 630 Wp (Voc ~50 V), no superar la
  tensión máxima de entrada con frío (+10%): en un Growatt MIN (550 V) 12
  paneles van en **2 cadenas de 6**, una por MPPT. Chequear también que la
  potencia FV admitida del inversor cubra los kWp (MIN 5000 = 7.500 W no
  alcanza para 7,56 kWp; MIN 6000 = 9.000 W sí).
- **Tope de potencia en tarifas chicas (T1).** La distribuidora/cooperativa
  suele limitar la potencia del generador a la del suministro (típico 10 kW en
  T1). Con un inversor mayor, en el texto: "la potencia de inyección se ajusta a
  la que habilite la Cooperativa", y avisale al asesor.
- **Varias acometidas.** Si el predio tiene más de un medidor, el solar descuenta
  solo del medidor donde está el inversor: no se compensa entre medidores.
  Aclaralo en el perfil del establecimiento y pedí la otra factura si el asesor
  quiere hablar del gasto total.

## Tono de los textos

Los bloques de texto del config (`perfil_html`, `consumo_html`, `objetivo_html`,
`recurso_html`, `intro_*`, `nota_*`) van en **tono formal pero vendedor**: la
misma información, pero cada dato apuntando a por qué el proyecto conviene. Los
giros que funcionaron:

- El consumo diurno alto es "la mejor noticia del proyecto", porque no hay
  energía que se desperdicie ni que haya que almacenar.
- La ausencia de cortes no es una limitación sino una **ventaja económica**:
  cada dólar va a generar energía y no a acumularla.
- La superficie acotada no es una restricción sino un **diseño optimizado**,
  "dimensionada al milímetro del recurso disponible".

No inventes datos del cliente para que el texto suene mejor, y no tapes una
limitación real: si el ahorro aplica a un solo medidor, o si la superficie está
por confirmar, tiene que estar escrito.

## Claves del config

Ver `reference/ejemplo_config_ongrid.json` para el archivo completo.

**Datos y encabezado**: `cliente`, `ubicacion`, `provincia`, `fecha`,
`presupuesto_nro`, `tc`, `titulo`, `subtitulo`.

**Textos de portada**: `h_consumo`, `perfil_html`, `consumo_html`,
`objetivo_html`, `recurso_html`, `h_presupuesto`.

**Sistema y presupuesto**: `sistema` (`etiqueta`, `paneles`, `wp`, `inversor`,
`inversor_corto`), `items` (`item`, `desc`, `cant`), `subtotal_usd`, `iva`
(lista de `pct` + `monto`), `total_usd`.

**Energía y supuestos**: `consumo_mensual` (12 valores), `generacion_mensual`
(12 valores), `frac_diurno`, `costo_kwh`, `precio_inyeccion`,
`factura_anual_ars`, `aprovechamiento_diurno`, `escalada`, `degradacion`,
`mantenimiento_usd_anual`, `anios_recupero`, `base_repago`,
`mostrar_recupero`.

**Páginas de texto**: `h_incluye`, `sub_incluye`, `intro_incluye`, `incluye`
(lista de `t` + `d`), `condiciones` (lista de `t` + `d`, **dejar vacía `[]`** si
el bloque se pisa con la página 2), `eyebrow_resultados`, `h_condiciones`,
`sub_condiciones`, `h_resultados`, `intro_resultados`, `nota_resultados`,
`h_generacion`, `cap_grafico`, `metodologia` (5 pasos, sin numerar: la lista los
numera sola), `h_recupero`, `intro_recupero`, `nota_recupero`,
`h_financiacion`, `cap_financiacion`, `financiacion`, `notas_financiacion`.

En los textos se pueden usar `<b>` y `<span class='gold'>` para resaltar en
dorado.

## Verificación antes de entregar

```bash
pdftoppm -png -r 70 "Propuesta Cliente.pdf" /tmp/chk
```

Revisá página por página:

- **Que sean 5 páginas (una alternativa) o 6 (comparativa).** Si son más, algo
  desbordó (lo típico: la página de resultados con los gráficos): compactá
  texto, alto del gráfico (`svg.chart` height) o padding de tablas; no agregues
  hojas.
- Que no quede ningún token `{…}` sin reemplazar en el PDF.
- Subtotal + IVA = total, igual que el presupuesto original.
- Cobertura = generación anual ÷ consumo anual.
- El año resaltado del recupero es donde el acumulado supera la inversión, y el
  "resultado neto" cambia de signo ahí.
- Que la metodología no quede numerada dos veces (los pasos del config van sin
  "1.", "2.", etc.).
- Que el repago del texto de las notas coincida con el de la tabla.
- Que no se haya colado ningún dato de otro cliente (precios, equipos,
  ubicación, generación).
- Que el pie no muestre número de página.
