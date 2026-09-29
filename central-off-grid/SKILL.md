---
name: central-off-grid
description: Arma la propuesta PDF de Oriens para una central OFF GRID — inversor off grid y batería que trabaja en paralelo a la red SIN inyectar excedente, o aislada de la red. Soporta 1 a 3 alternativas que difieren en paneles, batería o ambas. USAR SIEMPRE que un asesor de Oriens pida "la propuesta off grid", "armá la propuesta off grid de [cliente]", "comparame 4 y 8 paneles", "propuesta con batería sin inyectar"; cuando haya un PRESUPUESTO OFF GRID más la factura del cliente; cuando el cliente consulte por CORTES DE LUZ y respaldo; y al actualizar una propuesta off grid, cambiar sus alternativas, sacar o poner secciones de ahorro, o corregir su tarifa. Sirve además para leer la factura y reconstruir el costo del kWh con cargo fijo por tramos. NO usar para on grid con inyección (ver central-ongrid-una-alternativa), híbridos con inyección (ver central-hibrida-*) ni para el plano de paneles.
---

# Central OFF GRID — propuesta comparativa

Genera el PDF comercial de Oriens para centrales off grid. El documento sale íntegro
de un archivo JSON de configuración: no se escriben números a mano en el HTML ni en el
script.

```
python3 scripts/build_propuesta_offgrid_comparativa.py config.json "Propuesta_OFF_GRID_Cliente.pdf"
```

Requiere `weasyprint` (`pip install weasyprint --break-system-packages`). El script imprime
por consola el resumen de cada alternativa (generación, cobertura, ahorro, excedente), que
sirve para revisar los números antes de mirar el PDF.

## Lo que distingue a un off grid de todo lo demás

**No hay inyección.** Es la regla que gobierna todos los cálculos. La energía que los paneles
producen y la casa no consume en ese momento —ni entra en la batería— simplemente no se
aprovecha: no se vende, no genera crédito, no baja la factura. De ahí se desprende todo:

1. **El autoconsumo tiene un techo duro**: lo que la casa gasta de día, más lo que la batería
   puede ciclar por noche. Nada más.
2. **Sumar paneles no baja la factura una vez alcanzado ese techo.** Es el error más fácil de
   cometer al comparar alternativas que sólo difieren en paneles: dan exactamente el mismo
   ahorro. Verificar SIEMPRE con la salida por consola antes de prometer una diferencia.
3. **Sumar batería sí baja la factura**, porque corre el techo: cada kWh ciclable por noche es
   un kWh que deja de comprarse.
4. El recupero suele dar largo (10-20 años en residencial). Preguntar al asesor si va o no;
   por defecto conviene no mostrarlo y vender respaldo + reducción de factura.

## Antes de calcular: qué pedir

- **Presupuesto de cada alternativa** (PDF de Oriens): ítems, cantidades, subtotal, IVA, total
  y tabla de financiación. Nunca derivar el precio de una alternativa escalando otra.
- **Factura del cliente**, para el consumo mensual histórico y el cuadro tarifario completo.
- **Simulación de generación** de una configuración; el script escala el resto por cantidad de
  paneles (ver `generacion_base`).
- **Reparto día/noche del consumo** (por defecto 50/50 si el asesor no dice otra cosa).
- **Tipo de cambio** BNA venta del día, si se va a expresar algo en dólares.

## Lectura de la factura y armado de la tarifa

Muchas cooperativas facturan **por bloque**: todo el consumo del mes se cobra al precio del
tramo alcanzado, y el cargo fijo también es el del tramo. El salto de tramo puede ser brutal
—en Brandsen, pasar de 151 a 152 kWh sumaba $12.000 de cargo fijo—, y buena parte del ahorro
de una central sale justamente de bajar de tramo. Modelarlo con `modo: "bloque"` y cargar
todos los tramos del cuadro "TARIFAS APLICADAS" de la factura.

Fórmula que usa el script:

```
subtotal = consumo × precio_del_tramo + cargo_fijo_del_tramo + consumo × cargo_variable_kwh
factura  = subtotal × (1 + leyes_frac + iva_frac)
```

Para verificar que la tarifa está bien cargada: correr el consumo real de un mes y comparar
con el total de esa factura. Tiene que dar casi exacto.

- `cargo_variable_kwh`: cargos por kWh fuera de la energía (CTT y similares).
- `leyes_frac`: suma de leyes provinciales como fracción del subtotal (en PBA ≈ 0,155).
- `iva_frac`: 0,21 en vivienda particular y en cualquier cliente que no recupere IVA. Si el
  cliente es responsable inscripto y lo recupera, poner 0.
- Si la distribuidora cobra un único precio y un único cargo fijo, usar `modo: "plano"`.

## Motor de cálculo (por mes, por alternativa)

```
dia      = autoconsumo_dia_frac × consumo
noche    = consumo − dia
directo  = min(dia, generación)
sobra    = generación − directo
aporte   = min(noche, bateria_util × eficiencia × días, sobra × eficiencia)
facturado = consumo − directo − aporte
excedente = sobra − aporte / eficiencia
```

- `bateria_util_kwh`: capacidad útil real de la batería, no la nominal (UF5000: 5,12 kWh
  nominales, ~4,86 útiles al 95% DoD).
- `reserva_bateria_kwh`: capacidad que se aparta para respaldo y no se cicla. Con una sola
  batería chica y cortes breves, 0 es razonable; con cortes largos, reservar baja el ahorro
  y hay que decirlo.
- `excedente`: energía que los paneles pueden producir y nadie usa. Es el argumento para
  alternativas con más paneles: margen para consumos futuros, no ahorro de hoy.

## Secciones del documento y cómo activarlas

Página 1 (siempre): portada, el proyecto, consumo actual y tarjetas de alternativas.
Después, según flags en `documento`:

| Flag | Qué controla |
|---|---|
| `mostrar_comparativa` | Tabla lado a lado de las alternativas |
| `mostrar_ahorro` | Filas económicas de la comparativa (generación, cobertura, factura, ahorro, excedente, inversión) |
| `mostrar_mes_a_mes` | Tabla mensual de generación, excedente y factura |
| `mostrar_futuro` | Sección de excedente disponible y equivalencia en km de auto eléctrico |
| bloque `respaldo` | Sección "Qué pasa durante un corte de luz" (omitir el bloque la saca) |

Las páginas se reacomodan solas: si la comparativa se apaga, el respaldo y "Cómo funciona"
se unen en una sola sección corrida; si se apagan ahorro y mes a mes, la comparativa breve
sube a la página del respaldo. Siempre revisar el PDF rasterizado después de cambiar flags
(`pdftoppm -png -r 55`) para que no queden páginas semivacías ni en blanco.

Advertir al asesor cuando los flags dejan el documento sin ningún número de ahorro ni de
generación: queda una propuesta con precios y nada que los justifique.

## Cuando el cliente consulta por cortes de luz

Es un caso frecuente y cambia el eje de la propuesta. Puntos a modelar en el bloque
`respaldo`:

- **El límite no es la energía, es la potencia.** Un corte de 20-30 minutos consume poco,
  pero la batería tiene un tope de descarga (UF5000: 100 A ≈ 5,1 kW) y el inversor otro.
  Nunca prometer que "la casa sigue funcionando" sin acotar.
- **Tablero de cargas esenciales**: heladera, iluminación, tomas, internet, bomba, un aire.
  Fuera del respaldo: termotanque y horno eléctrico, que son de alta potencia y uso diferible.
  Se define en el relevamiento técnico.
- Si las alternativas comparten inversor y batería, el respaldo es idéntico en todas: decirlo
  explícitamente para que no parezca que la más cara respalda mejor.
- Una alternativa sin batería NO da respaldo. Si el cliente vino por cortes, ofrecerla puede
  jugar en contra.

## Señales de alerta que hay que levantar ante el asesor

- **El equipamiento declarado no cierra con el consumo histórico** (termotanque, aires y
  cocina eléctrica con 200 kWh/mes). Preguntar si ya están en uso o los va a incorporar: todo
  el cálculo se apoya en el consumo histórico.
- **Arreglo muy sobredimensionado** frente al consumo. Plantearlo como margen para crecer,
  nunca esconderlo.
- **Auto eléctrico**: sólo se alimenta del excedente si carga de día. Cargado de noche toma
  de la red igual que antes. Dejarlo escrito en la propuesta.
- **Inversor off grid sin batería**: confirmar con el asesor cómo opera (bypass de red) antes
  de describirlo en el documento.

## Estructura del config

Ver `reference/ejemplo_config_diego_ortiz.json` (caso real: Brandsen, 4 vs 8 paneles con
batería, sin inyección, cliente con cortes frecuentes y auto eléctrico en evaluación).

Bloques: `cliente`, `documento` (títulos, intro y flags), `consumo` (meses, distribuidora y
`tarifa`), `sistema` (`panel_wp`, `inversor_kw`, `generacion_base`), `supuestos`
(`autoconsumo_dia_frac`, `bateria_eficiencia`, `reserva_bateria_kwh`, `tc`), `alternativas`
(una por escenario: `paneles`, batería, ítems del presupuesto, totales y financiación),
`respaldo`, `futuro`, `fichas` y `condiciones`.

Cada alternativa puede traer su propia `generacion_mensual_kwh`; si no, se escala desde
`generacion_base` por cantidad de paneles.

## Fichas técnicas disponibles en `assets/`

`img_panel.png` (Jinko Tiger Neo), `img_inversor_deye.png` (Deye off grid),
`img_bateria_pylontech_uf5000.png`, `img_estr_chapa.png` (estructura coplanar).
Una ficha sin `img` se renderiza a ancho completo, sin foto. Para sumar un producto nuevo,
extraer la imagen de la ficha del fabricante (`pdfimages -all`) y componerla sobre fondo
blanco antes de guardarla.
