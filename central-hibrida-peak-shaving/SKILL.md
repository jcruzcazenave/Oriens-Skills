---
name: "central-hibrida-peak-shaving"
description: "Arma la propuesta PDF de Oriens para una central híbrida con PEAK SHAVING sobre un suministro con tarifa de demanda (Edenor T2 y similares), donde la factura la manda la potencia y no la energía consumida. USAR SIEMPRE que la factura traiga cargos de Potencia Contratada, Adquirida o Excedida; cuando el asesor hable de \"peak shaving\", \"recortar picos\", \"potencia excedida\" o \"bajar la potencia contratada\"; y cuando haya un presupuesto híbrido con banco de baterías dimensionado para aplanar picos. Cubre la lectura del recuadro de valores históricos, el modelo de ahorro en dos etapas tarifarias y el salto de categoría que elimina los cargos de potencia. NO usar para tarifas sin cargo de potencia (ver central-ongrid-una-alternativa, central-hibrida-* y central-off-grid)."
---

# Central híbrida · peak shaving

Acá el cliente **no paga por lo que consume: paga por el pico que le pide a la red**. En una
tarifa de demanda los cargos de potencia pueden ser el 75-80% de la factura mientras la
energía pesa menos del 20%. La propuesta demuestra eso con sus propias facturas y muestra
cómo las baterías lo eliminan.

Es el único esquema de la familia donde **el ahorro no viene de generar energía**, y por eso
tiene su propio documento: el de 5 páginas de `habilidad-armado-de-presupuesto-y-analisis`
no sirve porque está armado alrededor de generación vs. consumo.

## Todo parametrizado, siempre

**Ningún dato del cliente va escrito en el código ni en los textos.** El motor de cálculo y
el armador del PDF son genéricos; todo lo que cambia de un cliente a otro vive en un único
archivo de configuración:

```json
{
  "cliente":     { "nombre": "...", "localidad": "...", "suministro": "...", "fecha": "..." },
  "suministro":  { "distribuidora": "Edenor", "tarifa": "T2", "potencia_contratada_kw": 25,
                   "horario": "lunes a viernes de 8 a 18 h", "horas_operacion_ano": 2600 },
  "facturas":    [ { "mes": "...", "periodo": "...", "consumida_kw": 0, "kwh": 0, "kvarh": 0,
                     "fijo": 0, "contratada": 0, "adquirida": 0, "excedida": 0,
                     "variable": 0, "otros": 0, "electricos": 0, "impuestos": 0,
                     "ajustes": 0, "saldo_anterior": 0, "total_mes": 0 } ],
  "potencia_historica":  [ ["08/07/2025", 32.0] ],
  "consumo_mensual_kwh": { "Ene": 0 },
  "generacion_simulador_kwh": { "Ene": 0 },
  "sistema":     { "n_paneles": 0, "panel_wp": 0, "inversor_kw": 0,
                   "n_baterias": 0, "bateria_kwh": 0 },
  "presupuesto": { "items": [], "total_sin_iva": 0, "total_con_iva": 0 },
  "supuestos":   { "derate": 0.95, "split_dia": 0.70, "bat_efic": 0.90, "tope_kw": 0,
                   "mes_cambio_categoria": 6, "precio_iny_frac": 0.5, "tc": 0 },
  "tarifa_destino": { "categoria": "T1-G2", "cargo_fijo": 0, "precio_kwh": 0 }
}
```

Reglas que se desprenden:

- **Los textos del documento nunca llevan números escritos a mano.** Todo importe, kW o kWh
  sale del modelo. Un número hardcodeado queda viejo al primer cambio y nadie lo nota hasta
  que el cliente lo suma.
- **Cambiar un supuesto es editar una línea del config**, no buscar y reemplazar en el
  builder. Si el asesor pide "probá con tope de 12 kW" tiene que ser un solo cambio y un
  recompilado.
- **Los supuestos se declaran, no se esconden.** Cada uno con su valor y su origen; los que
  no estén confirmados van rotulados en la nota al pie del documento.
- El mismo config alimenta el PDF y cualquier análisis de sensibilidad que pida el asesor:
  correr tres topes distintos tiene que ser un bucle, no tres copias del archivo.

## Lo que define este esquema

- **La batería está para aplanar picos, no para la noche.** La cobertura nocturna es una
  consecuencia de la capacidad sobrante, nunca el objetivo. Presentarlo al revés confunde al
  cliente sobre para qué sirve el equipo —y el asesor lo va a corregir—. Verificá que no
  compitan: un pico de media hora consume `(pico − tope) × 0,5` kWh contra el consumo
  nocturno diario; con un banco grande entran los dos con margen.
- **El inversor se dimensiona por el hueco de potencia, no por los kWp.** Tiene que cubrir
  `pico registrado − tope de diseño`. Un inversor de 50 kW con 20 kWp de paneles no está
  sobredimensionado: está dimensionado para otra cosa.
- **La carga es muy "picuda".** Factor de carga típico del 6-15%: demanda media de 7 kW
  contra picos de 49. Ese contraste es el argumento de venta.
- **El ahorro llega en dos etapas** y hay que mostrarlas por separado (ver Paso 3).

## Paso 1 — Leer las facturas (acá se cometen los errores)

De cada factura, tabular por separado: cargo fijo, potencia contratada, potencia adquirida,
potencia excedida, cargo variable kWh, otros conceptos, conceptos eléctricos, impuestos,
ajustes, **saldo anterior**, total, potencia contratada y consumida, kWh, kVArh y el
recuadro de valores históricos.

**El saldo anterior no es consumo del mes.** Varias liquidaciones arrastran deuda impaga y
la suman al total intimado. Para comparar mes contra mes se usa
`conceptos eléctricos + impuestos + ajustes`, nunca el "Total a pagar". Una factura de
$4,1 M podía ser $2,5 M de consumo real y $1,6 M de deuda vieja.

**El recuadro "Valores históricos" da el año completo.** Cada factura trae los tres períodos
anteriores de potencia y energía. Encadenando los recuadros de 5-6 facturas se reconstruyen
12-13 períodos consecutivos: es la única serie que cubre el año y la que sirve para
dimensionar y para respaldar el pedido de cambio de categoría. **Aclaralo en el documento**:
no hay una factura por cada mes mostrado, y si el cliente pide el respaldo de un mes puntual
vas a estar mostrando el recuadro de otra factura.

**Pero el histórico NO es la base de liquidación.** Corre por encima de la línea "Consumida"
del cuerpo de la factura, y lo que se factura es la Consumida. Verificalo así:

1. `contratada $ / kW contratados` → precio unitario del kW de ese mes.
2. Con ese precio, la excedida tiene que dar `(consumida − contratada) × precio × 1,5`.

En Edenor da **exactamente 1,5** todos los meses. Y si algún mes tiene cargo de excedida con
el histórico clavado en el tope, queda probado que la base es la Consumida.

- **El histórico manda para dimensionar** (es el pico real que el equipo debe absorber).
- **La Consumida manda para calcular el ahorro** (es lo que se factura).

**Factor de impuestos.** `total_mes / conceptos_eléctricos` da un factor estable (~1,515 en
Edenor). Prorratearlo sobre cada concepto permite mostrar todo "con IVA incluido", que es la
convención de Oriens; dejalo dicho en la nota al pie.

**Factor de potencia.** `cos φ = kWh / √(kWh² + kVArh²)`. Si da menos de 0,95 el cliente está
penalizado —suele estar dentro de "Otros conceptos"— y el inversor híbrido lo corrige. Es
ahorro real: mencionalo aunque no lo computes.

## Paso 2 — Demanda media, bien calculada

Preguntá el **régimen horario** (ej. lunes a viernes de 8 a 18 = 2.600 h/año) y el reparto
diurno/nocturno. Sin ese dato la política de Oriens es 50/50. Los dos van al config.

`demanda media en operación = consumo anual × fracción diurna / horas de operación`

**No dividas el consumo por las 8.760 horas del año.** Eso da el promedio 24/7 —incluye
noches, fines de semana y feriados con la planta parada— y subestima la demanda real por un
factor de 2 a 3. Es un número que el cliente cuestiona en dos segundos.

## Paso 3 — El modelo de ahorro, en dos etapas

**Etapa 1 — todavía en la tarifa de demanda:**

| Concepto | Qué pasa |
|---|---|
| Potencia excedida | → cero. El peak shaving la elimina por completo. |
| Potencia adquirida | → `adquirida × min(1, tope / consumida_del_mes)`. |
| Cargo variable kWh | → lo cubre la generación solar según el balance mensual. |
| Inyección del excedente | → si el proyecto la contempla. |
| **Potencia contratada** | → **se sigue pagando íntegra.** No contarla acá. |

**Etapa 2 — cambio de categoría:** al bajar de una tarifa de demanda a una de pequeña demanda
(T2 → T1) desaparecen **los tres** cargos de potencia, no solo la contratada. Pedí el cuadro
tarifario de destino, cargalo en `tarifa_destino` y modelá la factura nueva con él: el kWh es
bastante más caro (2 veces o más) y el cargo fijo bastante menor. **No recicles los valores
de la tarifa vieja.**

La segunda etapa suele valer más que las cuatro palancas de la primera juntas. Requiere
acreditar 6-12 meses consecutivos sin superar el tope, así que va marcada como diferida.

### Coherencias que se rompen fácil

Son las que el cliente puede detectar leyendo. Conviene chequearlas por código sobre el
config, no a ojo:

- **El tope de diseño no puede superar la potencia que se va a contratar.** No se puede
  prometer bajar a 15 kW contratados diseñando el tope en 18.
- **Si prometés el cambio de categoría, el tope tiene que estar por debajo del límite de esa
  categoría.** Confirmá el límite con la distribuidora: de ahí cuelgan los números más
  grandes del documento.
- **La inyección no se valoriza contra la tarifa minorista.** Si al cambiar de categoría
  escalás el precio de inyección al kWh nuevo (más caro), la factura da cerca de cero y el
  ahorro 100%. Eso no es un hallazgo: es la señal de que el supuesto está mal. Dejá el
  precio de inyección fijo y aclaralo.
- **Los frentes dejan de ser aditivos** cuando cambia la tarifa, porque también cambian el
  cargo fijo y el precio de la energía. Un gráfico de barras por frente va a contradecir al
  total: usá un cuadro de tres columnas en su lugar.

## Paso 4 — Balance energético

Mes a mes: la generación cubre primero el consumo diurno; con el excedente se carga el
banco, que devuelve de noche afectado por el rendimiento round-trip (~90%); lo que no se
consume ni se almacena se inyecta.

Aplicá el **descuento conservador sobre el simulador** que indique el asesor (5-10%), desde
`supuestos.derate`. Chequeo: `generación = autoconsumo + inyección + pérdidas de batería`.

## Paso 5 — El documento (8 páginas)

Formato propuesta Oriens, reusando `_style.css` y el logo de
`habilidad-armado-de-presupuesto-y-analisis`. Tres piezas separadas: **el config** con los
datos del cliente, **el motor** que calcula el modelo y **el armador** que produce el HTML y
lo pasa a PDF con weasyprint (`pip install weasyprint --break-system-packages`). El motor y
el armador no cambian de un cliente a otro.

1. **Portada y diagnóstico** — destinatario, la tesis, tres números grandes y el gráfico del
   año completo de potencia con los excesos en naranja sobre la línea de contratada.
2. **Composición de la factura** — tabla de las facturas relevadas y balance energético
   mensual (generación, consumo, cubierto, inyectado, compra a la red).
3. **La solución** — cómo funciona, tabla de componentes **solo con cantidades** (los
   importes van únicamente en el total con y sin IVA), garantías y qué no cambia.
4. **Los dos escenarios** — cuadro de tres columnas concepto por concepto: *hoy · con el
   sistema en la tarifa actual · con la nueva categoría*. Es la página más importante.
5. **Recupero** — inversión, ahorro anual y plazo, con la curva acumulada, la línea de
   inversión y el cruce marcado.
6-8. **Anexo técnico** — una página por equipo: foto, tres cifras destacadas,
   especificaciones, garantía y un "Qué significa" en lenguaje llano.

**Registro:** formal pero legible, es para un cliente. Nada de "manda", "de sobra",
"picuda", "plata". Los títulos afirman la tesis en vez de anunciar la sección: *"Se paga por
el pico, no por el consumo"* funciona mejor que *"De qué se trata"*.

## Revisión de textos con el asesor

Antes de cerrar, ofrecé un archivo aparte con toda la prosa numerada por página y tipo de
bloque (`[4.4] RECUADRO DESTACADO`), para que edite y devuelva. Extraelo parseando el HTML
que produce el armador, así los códigos son estables. Aclarale que **no edite los números
ahí**: se recalculan solos y se pisan. Al recibirlo, difealo contra el original en vez de
releer todo.

## Verificación antes de entregar

- Cada factura: los conceptos suman los eléctricos; `eléctricos + impuestos + ajustes` da el
  total del mes.
- Los ítems del presupuesto suman el subtotal del cotizador; el IVA implícito es coherente
  con la mezcla de alícuotas (10,5% paneles, 21% resto).
- Balance: `cubierto + comprado = consumo` y `generación = autoconsumo + inyección + pérdidas`.
- Las tres columnas del cuadro cierran contra la factura promedio real.
- El recupero calculado a mano coincide con el del gráfico.
- El tope de diseño es coherente con la potencia a contratar y con el límite de la categoría.
- Ningún gráfico contradice a la tabla.
- **Ningún número del PDF está escrito a mano**: grepeá el armador buscando importes sueltos.

Y revisá qué **no** está contemplado, para poder responderlo en la reunión: mantenimiento
anual (~1%, mueve el recupero unos meses), degradación de paneles, recambio del inversor a
mitad del horizonte, y el mes más ajustado para el tope (compará demanda media en horas de
trabajo contra generación media en esas mismas horas).

## Sobre el IVA

Si el cliente no recupera el IVA —la factura lo dice en "Situación IVA"— va todo con IVA
incluido de los dos lados. Si es Responsable Inscripto el recupero **empeora levemente, no
mejora**: la factura de luz carga ~51% de impuestos y el equipo solo ~18%, así que sacarlos
de los dos lados quita más ahorro que inversión. En ese caso mostrá la inversión sin IVA,
porque para él es crédito fiscal.

## Errores ya cometidos — no repetirlos

- **Hardcodear los datos del cliente en el motor de cálculo.** El próximo cliente obliga a
  reescribir código en vez de cambiar un config. Datos, motor y armador van separados desde
  el primer archivo, no "después lo ordeno".
- **Armar un slide deck apaisado en vez del documento vertical de Oriens.** Pasó, con el PDF
  de referencia a la vista. Antes de construir nada, mirá el documento modelo que pasó el
  asesor y copiale la estructura.
- **Sumar el saldo anterior al consumo del mes.** Infla todo el diagnóstico.
- **Usar la línea "Consumida" como si fuera el pico** —o el histórico como si fuera la base
  de liquidación—. Son dos variables distintas con dos usos distintos.
- **Prometer una baja de potencia contratada incoherente con el tope de diseño.**
- **Escalar la inyección al kWh de la tarifa nueva** y terminar con una factura de cero.
- **Dar la demanda media dividiendo por 8.760 h.** Da 3 kW donde la planta opera a 7,4.
- **Citar un mes como si hubiera factura de ese mes** cuando el dato salió del recuadro
  histórico de otra. Atribuilo bien.
- **Dejar un gráfico de barras por frente después de meter el cambio de tarifa:** deja de
  sumar el total.
- **Presentar la batería como sistema de respaldo nocturno.** Es una aplanadora de picos.
- **Palabras oscuras en las notas al pie** ("se restituye durante la noche"). Si el asesor
  pregunta qué quisiste decir, el cliente tampoco lo entiende.