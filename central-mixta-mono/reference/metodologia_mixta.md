# Metodología — central mixta monofásica

## Motor mensual (igual para los dos modos)

Para cada mes, recorriendo el año desde `mes_inicio_idx` (default septiembre) para arrastrar el crédito:

```
dia       = autoconsumo_dia_frac × consumo
noche     = consumo − dia
directo   = min(dia, generación)
sobra     = generación − directo
aporte    = min(noche, bateria_util × eficiencia × días, sobra × eficiencia)
carga     = aporte / eficiencia
resto     = sobra − carga
red       = consumo − directo − aporte

off grid: no_aprovechado = resto, inyectado = 0
híbrido : inyectado = resto,       no_aprovechado = 0
```

`bateria_util` = útil real menos `reserva_bateria_kwh` (UF5000: 5,12 nominal, ~4,86 útil).

## Factura

```
energia = red × (precio_tramo + cargo_variable_kwh) × (1 + leyes_frac + iva_frac)
fijo    = cargo_fijo_tramo × (1 + leyes_frac + iva_frac) + fijos_exentos
credito = saldo_anterior + inyectado × precio_inyeccion      (sólo híbrido con inyección valorizada)
pago    = fijo + max(0, energia − credito)
saldo   = max(0, credito − energia)                           → pasa al mes siguiente
```

El crédito descuenta sólo energía: el piso de la factura es el cargo fijo.

## Precio de inyección

Criterio Oriens: 50% del promedio, **sin impuestos**, de los precios de todos los tramos del cuadro
(`precio_inyeccion_kwh` lo sobreescribe si la distribuidora informa otro valor). No aplicarle el
multiplicador impositivo: infla el ahorro ~30%. Confirmar con la distribuidora el porcentaje
reconocido y si el crédito se arrastra.

## Año 1 y régimen

- Año 1: todas las alternativas se calculan sin crédito (`anios_sin_inyeccion`, default 1).
- Régimen (desde el año 2): la híbrida con inyección valorizada, con el saldo estabilizado (se corre
  un año de calentamiento y se toma el segundo). `crédito sin usar` = lo que el saldo crece en un
  año: si es mayor que cero, hay saturación.
- Sin recupero (`mostrar_recupero: false`) la inyección no se valoriza en ningún año: se muestra sólo
  como energía.

## Recupero

- Año n: generación × (1 − degradación)^(n−1); ahorro en USD = ahorro en pesos / tc × (1 + aumento)^(n−1).
- Defaults: aumento 10% anual en dólares, degradación 0,5%, horizonte 25 años.
- El saldo de crédito se arrastra entre años en las híbridas.
- Repago: año (con fracción en meses) en que el acumulado alcanza `inversion_usd` (default `total_usd`,
  con IVA; si el cliente es RI y recupera IVA, pasar el subtotal).

## Chequeos automáticos (consola)

| Aviso | Cuándo |
|---|---|
| Generación perdida | off grid con más del 25% de la generación no aprovechada |
| Saturación | híbrida con crédito sin usar > 0 |
| Batería en invierno | en jun/jul/ago la batería cicla menos del 30% de su capacidad útil diaria |
| Respaldo sobre inversor | cargas `respaldo` > 80% de la potencia del inversor |
| Potencia monofásica | kWp máximo > `limite_mono_kwp` |
