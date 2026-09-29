# Metodología — híbrido comparativo con inyección

## El motor: balance mes a mes con arrastre de crédito

Para cada mes y cada alternativa de batería:

```
consumo_diurno    = consumo × fracción_diurna
consumo_nocturno  = consumo − consumo_diurno

autoconsumo_directo = min(generación, consumo_diurno)
excedente           = max(0, generación − consumo_diurno)
descarga_bateria    = min(excedente, consumo_nocturno, capacidad_ciclable × días)
inyectado           = excedente − descarga_bateria
compra_a_red        = consumo − autoconsumo_directo − descarga_bateria
```

Y la factura del mes:

```
costo   = compra_a_red × precio_autoconsumo
credito = inyectado × precio_inyeccion + saldo_del_mes_anterior
pago    = cargo_fijo + max(0, costo − credito)
saldo   = max(0, credito − costo)      ← se arrastra al mes siguiente
```

`capacidad_ciclable = capacidad_nominal × DoD × eficiencia` (defaults 0,90 y 0,96).

El arrastre de crédito es la razón de ser del modelo mensual. Con consumos estacionales, los meses de excedente acumulan un saldo de varios millones de pesos que es lo que después absorbe el invierno, cuando el sistema no llega a cubrir la demanda. Un modelo anual promedia esto y no lo muestra.

El mes de arranque (`mes_inicio_idx`) importa: arrancar en primavera acumula crédito antes del invierno, arrancar en otoño no. Default septiembre (índice 8).

## Los tres precios del kWh

| Destino | Valor |
|---|---|
| Autoconsumo directo | Costo real del kWh: `(cargo_variable + transporte o CTT por kWh) × multiplicador_impositivo` |
| Descarga de batería | El mismo que el autoconsumo directo |
| Inyección | `promedio(cargos variables de todos los tramos del cuadro) / 2`, **en pesos planos, sin impuestos** |
| Inyección, en propuestas sin recupero | 0 para el cálculo económico: se muestra sólo como energía |

Ejemplo Muglia (T1R, cuadro OCEBA Área Atlántica julio 2026): tramos R1–R7 = 206,67 · 215,06 · 221,62 · 226,40 · 236,38 · 246,93 · 264,18 $/kWh → promedio 231,03 → inyección $115,52/kWh. Costo real = (246,93 del tramo vigente + 15,45 de CTT) × 1,36501 = $358,15/kWh.

El kWh propio termina valiendo cerca de tres veces el inyectado. Esa asimetría es lo que justifica económicamente la batería, y es lo que un builder On Grid no modela.

## Multiplicador impositivo

Sumar los porcentajes que se aplican sobre la energía neta. Ejemplo de la Cooperativa de Coronel Dorrego con cliente monotributista:

```
Ley 7290      1,000%
Ley 11769     0,001%
Ley 11769     5,500%
Ley 11969     6,000%
IVA          27,000%   ← monotributo; responsable inscripto sería 21%
                       
multiplicador = 1,39501
```

Verificarlo siempre contra la factura: `total_factura / energía_neta` tiene que dar el mismo número.

Ejemplo de consumidor final residencial (Cooperativa de Las Flores): IVA 21% + Ley 11769 5,5% + Ley 11969B 0,001% + Ley 11969T 6% + Ley 7290 4% = **1,36501**. Ahí `importe_impuesto / total_energía` = 0,36501, y el "importe exento" es alumbrado público + servicios sociales (fijos, sin IVA).

## Repago

- Ahorro del año n: se recalcula el balance completo con la generación degradada `(1 − degradación)^(n−1)` y los precios escalados `(1 + aumento)^(n−1)`.
- `aumento_anual`: 10% en dólares (escenario base prudente de Oriens).
- `degradacion`: 0,5% anual.
- `anios_sin_inyeccion`: durante esos años `precio_inyeccion = 0`.
- El repago es el año en que el ahorro acumulado alcanza la inversión.

No aplicar tope al precio del kWh en USD: en tarifas argentinas actuales el kWh ya supera los topes históricos de la skill industrial y el tope distorsionaría el cálculo.

## Cargo fijo

Entra en la factura con y sin solar, así que **se cancela en el ahorro**. Sólo afecta la factura de referencia y el porcentaje de reducción. Incluirlo igual, porque es el número que el cliente ve.

`cargo_fijo_mensual = cargo_fijo_del_tramo × multiplicador + alumbrado_público + servicios_sociales` (estos dos, si son fijos). Con esto la factura de referencia cierra contra la real: en Muglia, 1.379 kWh × $358,15 + $86.833 = $580.722 contra $579.018 facturados.

Conservadurismo que el modelo no captura: si las compras a la red caen por debajo del tramo actual, la tarifa baja de tramo (cargo variable y fijo menores). El modelo mantiene el tramo vigente, así que el ahorro real es igual o mayor al calculado.

## Reserva al amanecer y días nublados

El modelo trabaja con promedios mensuales. Para describir qué pasa en rachas nubladas, `reserva_amanecer()` del builder flexible calcula, mes a mes, con cuánta energía amanece el banco:

- si el excedente diurno promedio ≥ consumo nocturno, el banco se llena cada tarde y amanece con `capacidad_ciclable − consumo_nocturno_diario`;
- si no, se vacía todas las noches y la reserva es 0 (típico de junio y julio).

La batería extra de la alternativa grande suma su capacidad ciclable a esa reserva sólo en los meses que llenan. Expresarla también en horas de consumo promedio (`kWh útiles / (consumo anual / 8.760)`). En una racha de varios días, todas las alternativas terminan tomando de la red: la batería extra demora ese momento y es respaldo ante un corte que coincida con días nublados. En el inversor Deye se puede fijar una reserva mínima de carga (SOC) que el uso diario no toque.
