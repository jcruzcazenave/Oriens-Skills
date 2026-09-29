---
name: central-hibrida-propuesta-unica-sin-bateria
description: "Arma la propuesta PDF de Oriens para una central híbrida SIN batería en un único escenario: inversor híbrido que hoy opera on-grid, con inyección del excedente a la red y batería prevista para una segunda etapa. Usar cuando el asesor pida la propuesta de un proyecto híbrido sin batería, o cuando haya un presupuesto HIBRIDO sin ítem de batería más la factura del cliente. Cubre la lectura y validación de la factura, el modelo de ahorro con tarifa por tramos marginales, y las decisiones comerciales del recupero."
---

# Central híbrida · propuesta única sin batería

Este caso es el intermedio entre el on-grid puro y el híbrido con batería: **el inversor es
híbrido pero la central arranca sin batería**. Hoy funciona conectada a la red, autoconsume
de día e inyecta el excedente; la batería queda cotizada aparte para una segunda etapa.

Usa el builder `build_propuesta.py` de la skill `habilidad-armado-de-presupuesto-y-analisis`,
con el modo de cálculo `mensual_progresivo` que se describe abajo.

## Lo que define este esquema

- **El autoconsumo está limitado por la demanda diurna, no por la generación.** Sin batería
  la central solo puede reemplazar el consumo que ocurre mientras hay sol. Si el asesor dice
  "70% diurno", el techo del autoconsumo es 70% del consumo de cada mes, por más que se genere
  de sobra. El 30% nocturno se compra a la red los doce meses, a tarifa plena.
- **El excedente vale mucho menos que el kWh evitado.** Se liquida al precio de inyección de
  la cooperativa (típicamente $150/kWh) contra los ~$500 que cuesta comprarlo. Si el excedente
  es grande, decilo: es el argumento de venta de la segunda etapa.
- **Nunca digas "on-grid" en el documento.** El título, el texto del sistema y la tabla de
  componentes dicen híbrido. "On-grid" solo aparece describiendo el modo de operación actual
  del inversor.
- **El texto va en condicional** (operaría, cubriría, inyectaría): es una propuesta, no una
  instalación hecha.

## Paso 1 — Juntar los datos, sin inventar ninguno

| Dato | De dónde sale |
|---|---|
| Consumo mensual, 12 meses | **Del gráfico de barras que imprime la propia factura** (suele traer 13 períodos). Leelo período por período. |
| Cuadro tarifario completo | Recuadro "CUADRO TARIFARIO" de la factura. Anotá todos los tramos, incluido el de arriba de todo. |
| Cargo fijo, aportes y tasas | Detalle de la factura, línea por línea, con su importe. |
| Condición de IVA y categoría | Encabezado de la factura, junto al CUIT. |
| Generación mensual | Simulación (PVsyst/PVGIS). Aplicarle la previsión por pérdidas (ver paso 4). |
| Presupuesto de componentes | El PDF del presupuesto. **Verificá el número de presupuesto y que el subtotal e IVA coincidan.** |
| Tipo de cambio | BNA venta del día. Buscalo, no lo asumas: un TC viejo distorsiona todo el recupero. |

**Si falta el consumo real, pedilo y frená.** No lo estimes ni lo completes con la serie de
generación. Un consumo inventado invalida el ahorro, el recupero y la cobertura, y es
indetectable a simple vista en el PDF final.

## Paso 2 — Reconstruir la factura y validarla al centavo

Antes de calcular ningún ahorro, reproducí una factura real. La estructura típica de una
cooperativa de Córdoba es:

```
base   = energía_por_tramos_marginales(kWh) + cargo_fijo
total  = base × (1 + recargos_frac + iva_frac)
```

Para descubrir `recargos_frac`, dividí **cada** línea de aporte/tasa por la base. Van a dar
porcentajes redondos y exactos (ej. FODEP 10%, ERSEP 0,1%, Tasa Reg. 0,4%, Tasa Municipal 5%
= 15,5%). Ese chequeo prueba además que **no son cargos fijos: bajan con el consumo**, y es la
respuesta si el asesor pide tratarlos como fijos.

El IVA puede aplicarse sobre la base y no sobre el subtotal con recargos — verificá dividiendo
el importe del IVA por la base.

**No sigas hasta que el total calculado dé igual al total impreso** (una diferencia de centavos
por la línea de redondeo es normal). Si no cierra, leíste mal algún tramo.

## Paso 3 — El modo `mensual_progresivo`

Si el builder no lo tiene, agregalo en `compute()` de `build_propuesta.py`, antes de la rama
`mensual_escalonado`:

```python
if e.get("modo") == "mensual_progresivo":
    cons_m = cfg["consumo"]["mensual_kwh"]; gen_m = cfg["generacion"]["mensual_kwh"]
    tramos = [(t[0], float("inf") if t[1] in (None, 0) else t[1], t[2]) for t in e["tramos"]]
    cfijo = e.get("cargo_fijo_ars", 0.0)
    recg  = e.get("recargos_frac", 0.0)
    ivaen = e.get("iva_frac_energia", 0.0)
    fdia  = e.get("autoconsumo_dia_frac", 0.5)
    p_iny = e["valor_inyeccion_ars"]
    mult  = 1.0 + recg + ivaen

    def energia_ars(kwh):
        t = 0.0
        for d0, h0, pr in tramos:
            if kwh <= d0:
                break
            t += (min(kwh, h0) - d0) * pr
        return t

    def factura_ars(kwh):
        return (energia_ars(kwh) + cfijo) * mult

    costo_sin = 0.0; costo_con = 0.0; iny_kwh = 0.0
    autoc_total = 0.0; deficit_total = 0.0
    for m in MES_ORDER:
        if m not in gen_m:
            continue
        c = cons_m[m]; g = gen_m[m]
        auto = min(fdia * c, g)      # techo = demanda diurna del mes
        iny  = g - auto
        red  = c - auto
        costo_sin += factura_ars(c)
        costo_con += factura_ars(red)   # el cargo fijo se paga igual
        iny_kwh += iny; autoc_total += auto; deficit_total += red
    ing_iny = iny_kwh * p_iny
    ahorro = (costo_sin - costo_con) + ing_iny
    con_kwh = deficit_total
    p_auto = costo_sin / cons_year
    p_iny_disp = p_iny
    auto = autoc_total / gen1 if gen1 else 0.0
    usdkwh1 = (ahorro / gen1) / tc if gen1 else 0.0
elif e.get("modo") == "mensual_escalonado":
    ...
```

Bloque `economia` del config:

```json
"economia": {
  "modo": "mensual_progresivo",
  "tramos": [[0, 500, 337.58], [500, 800, 336.72], [2000, null, 352.59]],
  "cargo_fijo_ars": 4244.22,
  "recargos_frac": 0.155,
  "iva_frac_energia": 0.27,
  "autoconsumo_dia_frac": 0.70,
  "valor_inyeccion_ars": 150,
  "tc": 1535,
  "aumento_anual": 0.10, "tope_usd_kwh": 0.18,
  "degradacion": 0.004, "mantenimiento": 0.01, "factor_co2": 0.000351
}
```

Si el asesor prefiere valuar el kWh al promedio del cuadro en vez de al tramo marginal, poné
un solo tramo `[[0, null, promedio]]`. Con tramos casi planos la diferencia es ~2%.

## Paso 4 — Previsión por pérdidas del sistema

Aplicá **5% sobre la generación simulada** (temperatura, suciedad, cableado y conversión) y
documentalo en la página de generación como previsión técnica, sin mencionar ningún efecto
comercial.

Ojo: si la generación derateada **sigue superando la demanda diurna todos los meses**, el
autoconsumo no cambia y el recupero tampoco — solo baja el excedente inyectado y la cobertura.
Calculalo y decíselo al asesor antes de prometer que el número se mueve.

## Paso 5 — Decisiones comerciales del recupero (preguntar, no asumir)

Estas tres cambian el número y son del asesor, no tuyas:

1. **Base**: ¿sobre la inversión sin IVA o con IVA? Si el cliente no recupera el IVA, el
   desembolso real es con IVA. Flag `"recupero_base": "con_iva"`.
2. **Inyección**: ¿entra en el repago? Si depende de un trámite no incluido en el presupuesto,
   conviene dejarla afuera. Flag `"recupero_excluye_inyeccion": true`.
3. **Tabla a 12 años**: si el valor real del kWh en USD ya supera el `tope_usd_kwh`, la tabla
   queda congelada desde el año 1 y no aporta. Sacala y dejá solo el número
   (`"mostrar_recupero": "numero"`).

Avisá siempre para qué lado cae el error de cada opción: en una propuesta comercial conviene
quedar corto y no largo.

## Verificación antes de entregar

```bash
pdftoppm -png -r 95 "Propuesta Cliente.pdf" /tmp/chk
```

- El total calculado de la factura de referencia coincide con el impreso.
- Cada línea de aporte/tasa da un porcentaje exacto de la base.
- La suma de los 12 meses de consumo coincide con `anual_kwh`, y con la factura mes a mes.
- Ningún mes de consumo repite un valor de la serie de generación (señal de dato inventado).
- La compra a la red del año ≈ (1 − `autoconsumo_dia_frac`) × consumo anual.
- El crédito por inyección de cada mes no supera la factura de ese mes (si la supera, se pierde).
- `inversion_usd` y el IVA coinciden con el presupuesto; si hay 10,5% en paneles y 21% en el
  resto, usá el IVA efectivo y una `iva_label` que lo explique.
- No aparecen "Growatt", "chapa", "on-grid" en el título, ni ítems que el asesor sacó.
- El TC es el del día.
- Entra en 5 páginas y financiación + próximos pasos quedan juntos.

## Errores ya cometidos — no repetirlos

- **Rellenar meses de consumo con la serie de generación.** Pasó y no se detecta leyendo el
  PDF. Si faltan meses, pedí la factura.
- **Tres consumos anuales distintos** conviviendo en el config (suma de meses, `anual_kwh` y
  el número escrito en el texto de intro). Que el texto salga de los datos, no a mano.
- **Números escritos a mano en los textos.** El recupero y el ahorro del recuadro final tienen
  que salir de los valores calculados; si los hardcodeás, quedan viejos al primer cambio.
- **Poner un `autoconsumo` alto "porque es híbrido".** Híbrido es el inversor. Sin batería el
  techo lo pone la demanda diurna, y hay que calcularlo mes a mes.
- **Dejar un TC viejo.** Fue el error más caro de todos: un dólar desactualizado movió el
  recupero un 50%.
- **Mezclar marcas y tipos de cubierta** entre el bloque `sistema`, las fichas, la tabla de
  componentes y las garantías. Después de cualquier cambio de equipo, buscá la marca vieja en
  todo el config.
- **Cadenas de `.replace()` sobre literales adyacentes en Python.** Los literales se concatenan
  ANTES de aplicar el método, así que el replace pisa texto que no querías. Formateá los
  números con una función aparte.