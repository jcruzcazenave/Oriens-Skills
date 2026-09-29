# Metodología — Propuesta Integral Off-Grid (comparativa)

Este documento explica las fórmulas de `scripts/build_propuesta_offgrid.py`, el builder
para propuestas **off-grid con 2-3 escenarios de batería comparados lado a lado** (mismo
arreglo solar, mismo inversor, sólo cambia la batería). Ejemplo completo:
`ejemplo_config_offgrid.json` (caso Ferrero, City Bell).

A diferencia de `build_propuesta.py`, acá no hay inyección a la red: toda la generación
que no se autoconsume ni se almacena en el momento se pierde. El sistema funciona en
paralelo al suministro de la distribuidora (no requiere alta como Usuario-Generador).

## De dónde sale la generación

Igual que en el resto de la skill: idealmente una simulación profesional; si no hay,
**PVGIS** con la ubicación, orientación e inclinación reales del proyecto (ver
`metodologia.md` → "De dónde sale la generación"). En el ejemplo Ferrero: 10 paneles ·
5,5 kWp orientados al norte con 15° de inclinación y 10% de pérdidas → 7.425 kWh/año.

## Costo real del kWh

Mismo criterio que el modo plano de `metodologia.md`: costo con impuestos directos no
recuperables incluidos, sin IVA. Sale de la factura real del cliente. En vivienda
particular no hay "modo escalonado" salvo que la tarifa de la distribuidora lo tenga —
si la tuviera, hay que decidir caso a caso si conviene adaptar este builder o usar el modo
`mensual_escalonado` de `build_propuesta.py` en su lugar (ver "Qué builder usar" en
`SKILL.md`).

## Autoconsumo: reparto día/noche + batería

A diferencia del modo `mensual_escalonado` (que trabaja mes a mes con generación
estacional), acá el consumo se modela como un patrón **diario constante** repetido los
365 días del año — apropiado cuando no hay estacionalidad marcada de consumo o cuando
sólo se cuenta con un promedio mensual (no 12 meses reales mes a mes):

```
consumo_diario = consumo_anual / 365
directo_diario = autoconsumo_dia_frac × consumo_diario      # cubierto en el momento, de día
noche_diario   = (1 − autoconsumo_dia_frac) × consumo_diario # debe salir de la batería

ciclable_diario = capacidad_bateria_kwh − reserva_bateria_kwh
autoc_noche_diario = min(ciclable_diario, noche_diario)

autoconsumo_total_anual = (directo_diario + autoc_noche_diario) × 365
% autoconsumo = autoconsumo_total_anual / consumo_anual
```

- `autoconsumo_dia_frac` (**default 0,5**, es decir 50% día / 50% noche): fracción del
  consumo que ocurre en horas de sol. Es la variable que más cambia el resultado —
  chequeá el caso "Ezequiel" en el historial, donde pasar de 40%/60% a 35%/65% empeoró
  bastante el autoconsumo y el repago. Política Oriens: **asumí 50/50 salvo que el
  asesor aclare un split distinto para ese cliente puntual** — no lo preguntes de
  entrada ni lo inventes a partir de suposiciones (losa radiante, aire acondicionado,
  etc.); usá el default y, si el asesor te da un dato mejor, actualizalo. El ejemplo
  Ferrero usa 35/65 porque en esa propuesta puntual se había confirmado ese split — no
  es el default general.
- `reserva_bateria_kwh` (default 4): energía que NO se cicla nunca, reservada para
  sostener la casa ante un corte de luz prolongado. Es un compromiso: más reserva = más
  autonomía ante corte, pero menos capacidad ciclable = menos autoconsumo diario.
- La cobertura del consumo nocturno (`cobertura_noche_pct` en el código) es
  `autoc_noche_diario / noche_diario` — se muestra en la metodología del PDF para que el
  cliente entienda cuánto de "la parte difícil" (la noche) cubre cada batería.

## Ahorro y recupero (12 años)

Misma lógica de recupero año a año que en `metodologia.md` (degradación, aumento anual,
tope de precio, mantenimiento — mismos defaults: `aumento_anual` 0,10, `tope_usd_kwh`
0,18, `degradacion` 0,005, `mantenimiento` 0,01), aplicada sobre el autoconsumo total en
vez de la generación total (acá lo que no se autoconsume no vale nada, no hay precio de
inyección):

```
usd_kwh_1 = costo_real_kwh / tc
autoc_y   = autoconsumo_total_anual × (1 − degradacion)^(y−1)
precio_y  = min(usd_kwh_1 × (1 + aumento_anual)^(y−1), tope_usd_kwh)
ahorro_neto_y = autoc_y × precio_y − mantenimiento × inversion_usd
```

El payback es el año en que el acumulado supera la inversión (sin IVA) — mismo criterio
que el resto de la skill: "el kWh comprado a la distribuidora incluye IVA y la inversión
también, así que ambos lados se compensan y se trabaja sin IVA en los dos extremos".

**Nota de trazabilidad:** el PDF de referencia (`ejemplo_ferrero.pdf`) se generó en una
sesión anterior con un script ad-hoc que no quedó guardado, y sus cifras de repago
(6 años 9 meses / 8 años 1 mes) pueden no coincidir exactamente con lo que da este
builder (que aplica la misma fórmula de degradación + mantenimiento + tope que el resto
de la skill, por consistencia). Con el mismo config, este builder da ~7 años 7 meses /
9 años 9 meses — el autoconsumo (96%/67%) y el ahorro año 1 (USD 900/613) sí coinciden
casi exacto. Si en algún momento se recupera el criterio exacto que se usó para el repago
del PDF original, actualizar esta fórmula.

## Multi-escenario (2 o 3 columnas)

El template de 3 páginas está pensado para 2-3 escenarios uno al lado del otro (columna
por escenario en la página de presupuestos y en la tabla comparativa). Con más de 3 se
empieza a ver apretado — si hace falta comparar 4+ alternativas, conviene separarlas en
propuestas individuales con `build_propuesta.py` en lugar de forzarlas en este formato.

## Cuándo usar este builder vs. los otros dos

Ver `SKILL.md` → "Qué builder / ejemplo usar" para la tabla de decisión completa. En
resumen: **este builder** es para off-grid con **2-3 alternativas de batería a comparar**
en el mismo documento. Para un solo escenario (industrial on-grid, o residencial
híbrido/off-grid sin comparar alternativas), usar `build_propuesta.py` con el modo plano
o `mensual_escalonado` según corresponda.
