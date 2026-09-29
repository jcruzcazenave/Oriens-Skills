---
name: "central-mixta-mono"
description: Arma la propuesta PDF de Oriens para una central MONOFÁSICA MIXTA que compara, en 2 o 3 alternativas (estándar off grid 5 kWh, off grid 16 kWh, híbrida 16 kWh con más paneles), una opción OFF GRID (en paralelo a la red, sin inyectar) contra una o más HÍBRIDAS (con inyección y crédito que se arrastra mes a mes), con recupero opcional. USAR SIEMPRE que un asesor de Oriens pida "central mixta", "mixta mono", "off grid o híbrida", "comparame off grid contra híbrido", "una sin inyectar y otra inyectando"; cuando haya presupuestos del mismo cliente con inversor off grid Y inversor híbrido sobre bajada monofásica; en casas de campo, chacras o quintas con varias viviendas, taller o cargas pesadas (soldadora, amoladora, cocina eléctrica, bombas) que hay que separar entre circuito respaldado y circuito de red; y al actualizar, recalcular o sacar el recupero de una propuesta mixta. NO usar si todas las alternativas son off grid (ver central-off-grid) o todas híbridas (ver central-hibrida), trifásico ni peak shaving.
---

# Central mixta monofásica — off grid vs. híbrida

Genera el PDF comercial de Oriens cuando el cliente tiene que decidir **si inyectar o no**: una
alternativa off grid (sin trámite, sin inyección) contra una o dos híbridas (con alta como
Usuario-Generador y crédito por el excedente), todas sobre bajada monofásica. El documento sale
íntegro de un JSON de configuración; no se escriben números a mano en el HTML ni en el script.

```bash
python3 scripts/build_propuesta_mixta.py config.json "Propuesta Oriens - <Cliente>.pdf"
python3 scripts/build_propuesta_mixta.py config.json --solo-calculo   # sólo números, sin PDF
```

Requiere `weasyprint` (`pip install weasyprint --break-system-packages`). El script imprime el
balance de cada alternativa y una lista de **avisos para el asesor**: leerla siempre antes de
mirar el PDF.

## Lógica gráfica de Oriens — no negociable

El builder usa la misma hoja de estilos que las propuestas off grid e híbridas (`scripts/_style_mixta.css`:
Poppins/Lato, dorado `#e0a92a`, logo SVG, encabezado corrido, tiras de stats, tarjetas, notas,
fichas con foto y cierre). No inventar estilos nuevos por caso: si hace falta algo, agregarlo al
CSS respetando esa paleta, como la etiqueta de modo (`.modo.og` azul gris / `.modo.hb` dorada) y
la lista numerada `.steps`. Después de cada cambio de contenido o de flags, rasterizar
(`pdftoppm -png -r 55`) y revisar que no queden páginas semivacías ni tablas partidas.

## Al arrancar: preguntar

Estas definiciones cambian el cálculo; no asumirlas. Preguntar de a pocas, con opciones:

1. **¿Va recupero?** Se decide en cada caso (`mostrar_recupero`). Sin recupero, la inyección se
   muestra sólo como energía y la factura se calcula sin crédito.
2. **Si va el esquema estándar** (off grid 5 kWh / off grid 16 kWh / híbrida 16 kWh, mismos paneles)
   o una variante. Con cualquier variante: al menos una off grid y una híbrida.
3. **Reparto día/noche del consumo** (default 50/50). En campo con aires y cocina eléctrica suele
   haber consumo nocturno fuerte: preguntar.
4. **Cortes de luz**: frecuencia y duración, y qué cargas quieren sostener sí o sí.
5. **Cargas pesadas**: soldadora (inverter o de transformador, amperaje), amoladora, cocina
   eléctrica, bomba, aires. Definen el reparto entre circuito respaldado y circuito de red.
6. **Condición fiscal** (consumidor final / monotributo / RI): define si el IVA entra en el ahorro
   y en la inversión.
7. Dudas sobre los kWh de la factura (lectura bimestral, período ≠ mes de consumo).

## Esquema estándar: tres alternativas

Salvo que el asesor diga otra cosa, la propuesta mixta lleva estas tres alternativas (primer caso
real: Ezequiel Perazzio, presupuestos 005-000232 / 233 / 234):

| | Modo | Paneles | Inversor | Batería |
|---|---|---|---|---|
| A | Off grid | 12 × 630 Wp | 2 × Deye off grid 6,6 kW en paralelo (13,2 kW) | UF5000 · 5 kWh |
| B | Off grid | 12 × 630 Wp | 2 × Deye off grid 6,6 kW en paralelo (13,2 kW) | Fidus · 16 kWh |
| C | Híbrida | 16 × 630 Wp | Deye híbrido monofásico 8 kW (picos 12 kW) | Fidus · 16 kWh |

Cómo contar cada salto:

- **A → B cambia sólo la batería.** Muestra cuánto vale la batería grande sin inyección: más consumo
  nocturno cubierto y más horas de respaldo. Verificar el invierno: en junio la de 16 kWh puede
  recibir los mismos kWh/día que la de 5.
- **B → C cambia el destino del excedente, y con él los paneles.** La híbrida lleva más paneles
  porque inyectando el excedente se aprovecha; en una off grid, sumar paneles no baja la factura
  una vez alcanzado el techo (la consola muestra cuánto se pierde en la B). En el año 1, con el alta
  en trámite, la C ahorra sólo por lo que los paneles extra suman al autoconsumo y a la batería.
- **La potencia no es la misma.** Las off grid tienen 13,2 kW entre los dos inversores; la híbrida,
  8 kW con picos de 12 kW. Importa para las cargas pesadas (soldadora, cocina, aires): en la C
  puede tener que ir al circuito de red algo que en la A y la B entra en el respaldado. La
  comparativa lo muestra en la fila "Potencia disponible" y la consola lo avisa.
- **16 × 630 Wp = 10,08 kWp**: pasa el aviso de potencia monofásica. Confirmar con la distribuidora
  el máximo admitido como Usuario-Generador antes de presentar.
- La nota comparativa se escribe sola describiendo los dos saltos con los números del motor
  (`nota_comparativa` la reemplaza; `""` la saca).

Cargar los presupuestos tal cual: `inversor_kw` es la potencia total (13,2 con dos en paralelo),
`inversor_pico_kw` el pico si el presupuesto lo declara, y la financiación como
`[["Contado · 50% anticipo", "5.357", "5.357", "10.714,77"], ...]`, con el mismo nombre de modalidad
en todas las alternativas: el PDF arma una única tabla comparada. El IVA es la suma de las líneas
de 21% y 10,5% del presupuesto.

Ejemplo: `reference/ejemplo_config_campo_demo.json` (equipos y precios del caso real; consumo y
tarifa ficticios).

## Insumos

- **Presupuesto de cada alternativa** (PDF de Oriens): ítems, subtotal, IVA, total y financiación.
  Nunca derivar el precio de una alternativa escalando otra.
- **Factura** con 12 meses de consumo y el cuadro de cargos. Sin factura se puede hacer un
  relevamiento preliminar en la conversación, pero **no armar el PDF**.
- **Simulación de generación** de una configuración (`generacion_base`); el resto escala por
  paneles. Planilla del simulador Oriens (ya trae 10% de pérdidas): usarla tal cual, sin recortar
  y sin decir en el PDF que es conservadora. Planilla sin pérdidas: reescalar a 1.425 kWh/kWp o
  pedir PVGIS al asesor.
- **Tipo de cambio** BNA venta del día.

## Lo que define una propuesta mixta

Cada kWh generado va a tres destinos: la casa en el momento, la batería, o el sobrante. **La única
diferencia de cálculo entre los modos es qué pasa con el sobrante**: en la off grid se pierde; en
la híbrida se inyecta y, una vez aprobada el alta, genera crédito que descuenta de la **energía**
(nunca del cargo fijo) y se arrastra al mes siguiente. De ahí salen las conclusiones que hay que
tener claras antes de presentar:

1. **La off grid tiene techo duro**: consumo diurno + lo que la batería cicla por noche. Paneles de
   más no bajan la factura. El builder avisa cuando se pierde más del 25% de la generación.
2. **La híbrida arranca igual que la off grid.** El año 1 (alta en trámite, `anios_sin_inyeccion: 1`)
   ahorra sólo por autoconsumo. Si las dos alternativas tienen el mismo arreglo y la misma batería,
   en el año 1 ahorran lo mismo: la diferencia es el crédito desde el año 2, contra el mayor costo
   del inversor híbrido. Mostrar las dos cifras por separado.
3. **Saturación**: si la híbrida genera de más, el crédito cubre toda la energía y el resto queda
   sin usar (`crédito sin usar` en consola). La factura no baja del piso de cargos fijos. Marcárselo
   al asesor con los números antes de armar el PDF.
4. **Batería en invierno**: si la generación de junio/julio no supera el consumo diurno, la batería
   casi no cicla. El builder avisa; no escribir que "ataca el invierno" sin verificarlo.

Detalle de fórmulas, precios del kWh y recupero: `reference/metodologia_mixta.md`.

## Monofásico: límites a cuidar

- **Potencia del inversor**: en monofásico el techo práctico es el del inversor elegido (6,6 kW
  off grid, 8 kW híbrido en los presupuestos habituales). Soldadora, amoladora y cocina eléctrica
  pueden superarlo solas.
- **Dos circuitos**: el respaldado (heladeras, iluminación, tomas, internet, bomba, un aire) sale del
  inversor; el de red (cocina, aires restantes, taller) va directo al suministro. Cargarlo en
  `cargas` con `circuito: "respaldo" | "red"`: el PDF arma las dos listas y la consola avisa si el
  respaldo supera el 80% del inversor. Con red, las cargas del circuito de red **también aprovechan la
  energía solar en los dos modos**; sólo la pierden durante un corte:
  - Híbrida: por el CT del lado de red, con el limitador.
  - Off grid Deye SUN-6.6K-OG03LP1: sólo en modo **"Zero Export To CT"** (Modo II del manual) y con un
    **CT externo, que no viene en la caja**. Verificar que el presupuesto lo incluya. Sin CT, lo que va
    por afuera nunca usa solar y hay que restarlo del consumo cubrible de esa alternativa.
  - La off grid no inyecta en ningún modo (el limitador de exportación figura como inválido).
- **Potencia de generación admitida**: confirmar con la distribuidora el máximo como Usuario-Generador
  en un suministro monofásico (`limite_mono_kwp`, default 10 kWp, dispara el aviso).
- **Paneles fuera de la casa por sombras**: estructura de piso; medir la distancia al tablero para el
  cableado de CC. Se define en la visita técnica.

## Sin conexión previa a la red (consumo estimado)

Pasa en campos donde la distribuidora recién está tendiendo la red: no hay facturas. Entonces:

- `consumo.estimado: true`. Los 12 meses salen de un relevamiento de cargas con horas de uso
  (verano/invierno) que se arma en la conversación con el asesor; nunca inventarlos.
- La tarifa sale del cuadro vigente de la distribuidora para la categoría que va a tener.
- El PDF cambia solo los textos: "Consumo estimado", "factura estimada, sólo con la red" y
  "ahorro frente a la red". No hay "factura actual".
- Advertir al asesor que el cálculo es tan bueno como la estimación de consumo.

## Sin tarifa: propuesta sólo en energía

Si el asesor no quiere recupero ni análisis en pesos (típico cuando no hay red todavía), no estudiar el
cuadro tarifario: dejar `consumo.tarifa` en `null`. El PDF saca solo toda cifra en pesos (factura,
ahorro, crédito) y muestra energía: generación, energía solar usada, cobertura (resaltada), inyectado,
no aprovechado y energía tomada de la red. En la portada quedan sólo el consumo anual y el
promedio mensual; el reparto diurno/nocturno se usa en el cálculo pero no se imprime (`mostrar_reparto: true` lo muestra). Presupuestos y financiación quedan igual.

## Sin garantizar abastecimiento solar

Si el asesor no quiere que el PDF comprometa un porcentaje de abastecimiento (lo pidió en el caso
Perazzio, con consumo estimado): `mostrar_cobertura: false` y `mostrar_mes_a_mes: false`. La
comparativa queda con el equipamiento, la generación anual estimada y la inversión, sin energía
usada, cobertura, inyectado, no aprovechado ni energía de red. La nota comparativa se escribe a mano
en `nota_comparativa`, describiendo cada salto **sin cifras de cobertura**.

## Valorizar la inyección sin mostrar recupero

`valorizar_inyeccion` (default = `mostrar_recupero`) decide si el crédito entra en la factura con el
sistema. Sin recupero pero con valor conocido del kWh inyectado (ej. EPE: $140/kWh), preguntar al
asesor: si se valoriza, la comparativa muestra factura y ahorro del año 1 (alta en trámite) y desde
el año 2; si no, la inyección aparece sólo como energía, y en una propuesta mixta eso esconde justo
lo que diferencia a la híbrida.

## Datos del Deye off grid 6,6 kW (manual SUN-6K-OG03LP1-EU-AM2)

- Salida 6,6 kW / 28,7 A por equipo; pico 2 × nominal durante 10 s (13,2 kW por equipo).
- Entrada de red y de generador: 35 A por equipo (~8 kW a 230 V). Cable de 6 mm².
- PV máx. de entrada: 10.560 W por equipo, 2 MPPT, 125–500 V.
- Con red suma red + solar + batería (no conmuta). Modos: Load First, Batt First, Grid Peak Shaving.
- Aires sin retardo de rearranque (2–3 min) pueden disparar sobrecarga si la luz vuelve enseguida:
  revisarlo en la visita técnica.

## Lectura de la factura

- Tarifa por bloque (`modo: "bloque"`, cooperativas: todo el consumo al precio del tramo alcanzado)
  o plana (`modo: "plano"`). Cargar todos los tramos del cuadro: de ahí sale también el precio de
  inyección.
- **Fuera de PBA las leyes provinciales son otras** (EPE Santa Fe, EDESE, etc.): sacarlas de la
  factura, no copiar el 0,155 bonaerense. Verificar que `factura(consumo real)` dé el total de un
  mes real.
- Cargos proporcionales (CTT y similares) → `cargo_variable_kwh`. Alumbrado y fijos exentos de IVA
  → `fijos_exentos`.
- Asignar cada consumo al mes calendario real de lectura; pares iguales = lectura bimestral repartida.
- Si el equipamiento declarado no cierra con el consumo histórico (aires + cocina eléctrica con
  poco consumo), preguntar si ya están en uso: todo el cálculo se apoya en el histórico.

## Secciones y flags

Orden del documento (definido por el asesor en el caso Perazzio): las fotos de los equipos van en el
medio, antes de los presupuestos, y los próximos pasos al final, después de las cotizaciones y la
financiación.

| Orden | Contenido | Control |
|---|---|---|
| 1 | Portada, el proyecto, consumo, tarjetas por alternativa con etiqueta de modo | siempre |
| 2 | "Qué cambia entre una y otra" (off grid vs. híbrida) + circuito respaldado / de red | `mostrar_modos`, `respaldo`, `cargas` |
| 3 | Comparativa lado a lado + recupero (**se puede sacar**: las tarjetas y los presupuestos ya muestran el equipamiento) | `mostrar_comparativa`, `mostrar_cobertura`, `mostrar_recupero` |
| 3 bis | Mes a mes | `mostrar_mes_a_mes` |
| 4 | Cómo funciona: diagrama, "Qué hace el sistema en cada situación", nota de prioridades | `situaciones`, `texto_funciona` |
| 5 | Fichas técnicas con foto | `fichas` |
| 6 | Presupuesto de cada alternativa | siempre |
| 7 | Financiación comparada + cómo avanzamos + condiciones + cierre | `proximos_pasos`, `condiciones` |

La tabla de modos tiene textos por defecto correctos; se reemplaza entera con `modos_comparacion`.
Esquema completo del config: `reference/config_schema.md`. Ejemplo que corre:
`reference/ejemplo_config_campo_demo.json` (**datos ficticios**, sólo para probar).

## Reglas de redacción

- **Objetivo, no persuasivo.** No inducir la elección: describir qué hace cada alternativa con la
  energía, con números. Cuál conviene se discute con el asesor, no en el PDF.
- **No poner que Oriens gestiona ante la distribuidora el alta ni el medidor bidireccional.** Decir
  que la híbrida los requiere.
- **"Cómo avanzamos" arranca en la visita técnica** (ubicación de paneles fuera de sombras,
  cableado, tablero, definición de circuitos).
- **Fichas con foto** de cada equipo presupuestado (panel, inversor off grid e híbrido, cada batería).
- No mencionar ni caracterizar la zona del cliente ("zona rural con cortes"): `ubicacion` vacía por
  defecto. El motivo de los cortes se cuenta desde lo que dijo el cliente.
- Batería: mostrar la **capacidad nominal**; la útil va en `bateria_util_kwh` para el cálculo.
- **Sin cierre**: el documento termina en los próximos pasos, sin frase final ("Empezá a controlar tu energía.") ni datos de contacto (teléfono, web, mail). Si el asesor los pide: `mostrar_cierre: true`, `frase_cierre` y `cierre`.
- Una alternativa sin batería no da respaldo: si el cliente vino por cortes, avisar al asesor.

## Auditoría antes de entregar

- En cada mes y alternativa: `directo + batería + red = consumo` y
  `directo + batería/eficiencia + inyectado + no aprovechado = generación`.
- Cada cifra de la prosa del config coincide con la consola. Al cambiar un supuesto, barrer los
  textos del JSON buscando valores viejos.
- Sin recupero: que no quede ninguna cifra de repago ni de crédito en textos ni notas.
- Revisar el PDF rasterizado página por página.

Si el asesor lo pide, guardar con la skill `guardar-en-google`.

## Archivos

```
central-mixta-mono/
├── SKILL.md
├── scripts/
│   ├── build_propuesta_mixta.py   ← builder y motor (off grid + híbrido, recupero opcional)
│   └── _style_mixta.css           ← estilos Oriens (base off grid + etiqueta de modo y pasos)
├── reference/
│   ├── metodologia_mixta.md
│   ├── config_schema.md
│   └── ejemplo_config_campo_demo.json   ← datos ficticios, para probar
└── assets/                         ← fotos de panel, inversor Deye, UF5000, Fidus, estructuras
```
