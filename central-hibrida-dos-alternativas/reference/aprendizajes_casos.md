# Casos resueltos y aprendizajes

Cada cliente es distinto. Este archivo junta los casos ya armados con esta skill, qué se decidió y por qué, para usarlos como punto de partida cuando un caso nuevo se parezca. Agregar un caso nuevo al final cada vez que una propuesta obligue a cambiar algo del flujo.

---

## Claudio Van Waarde — mismo arreglo, dos baterías, con recupero

- **Configuración:** 16 paneles de 620 Wp (9,92 kWp), inversor híbrido 12 kW, batería de 5 kWh contra 16,1 kWh. Tarifa T4 pequeña demanda, cliente monotributista (IVA 27% no recuperable).
- **Supuestos:** planilla de HSP **sin** pérdidas, reescalada a 1.425 kWh/kWp. Inyección a la mitad del cargo variable. 40% diurno. Año 1 sin inyección.
- **Resultado:** repago 4 años 11 meses contra 5 años 1 mes. Formato estándar con recupero.
- **Aprendizajes:** el chequeo de invierno (generación contra consumo diurno) define si la batería grande aporta algo en los meses críticos. El arrastre de crédito entre meses es lo que absorbe el invierno.
- Config: `ejemplo_config_van_waarde.json` · PDF: `ejemplo_van_waarde.pdf`.

---

## Gerardo Muglia — distintos paneles y baterías, sin recupero (septiembre 2026)

**Configuración.** A: 16 × Jinko Tiger Neo 630 Wp (10,08 kWp) + 2 × Pylontech Fidus (32,2 kWh), USD 22.635 con IVA. B: 20 paneles (12,6 kWp) + 3 baterías (48,2 kWh), USD 27.296. Mismo inversor Deye híbrido trifásico 20 kW. Residencial T1R sin subsidio, consumidor final (IVA no recuperable), 12.502 kWh/año.

**Qué obligó a cambiar la skill.**

1. **Las alternativas diferían en paneles, no sólo en batería.** El builder original asumía un único arreglo y una única curva. Se armó el builder flexible con generación y arreglo por escenario, gráfico con una serie por alternativa y columna de generación por alternativa en el balance.
2. **Saturación.** Las dos alternativas generaban más que el consumo anual (131% y 163%). Con inyección valorizada, desde el año 2 las dos ahorraban exactamente lo mismo (USD 2.917/año, el techo de la parte variable) y hasta la A con una sola batería llegaba ahí. La B sólo sumaba crédito sin usar (~$820.000/año). Se le marcó al asesor antes de armar el PDF.
3. **Sin recupero.** El asesor decidió: "al cliente no le interesa cuándo recupera". La inyección quedó sólo en el análisis de reparto de la energía (consumo directo, batería, inyección potencial, red) y la factura se calcula sin inyección, con los cargos fijos que se siguen pagando.
4. **Iteraciones de contenido del asesor** sobre el PDF, en orden: sacar el porcentaje de reducción de la factura (no tenemos el precio real del kWh inyectado; sin aclararlo en el PDF); sacar inversión con IVA y equivalente en pesos de la comparativa; sacar la nota comparativa; sacar el ahorro anual en USD (diferencia chica frente a la diferencia de precio); renombrar la fila a "Factura promedio con el sistema sin inyección"; nombrar el crédito por inyección sólo dos veces.
5. **Días nublados.** El asesor quiso destacar el valor de la tercera batería más allá de los promedios. Se agregó el paso 6 de metodología con `reserva_amanecer()`: en 10 de 12 meses el banco amanece con 3–13 kWh (A) y 17–27 kWh (B); la batería extra suma ~14 kWh útiles, ~10 horas del consumo promedio. En junio y julio el banco se vacía todas las noches en las dos. No se prometió que cubra varios días.
6. **Redacción afirmativa.** El crédito por inyección "**reduce** los cargos fijos" (no "podría reducir"), una vez aprobada el alta. En negrita, al cierre del paso 5: el objetivo es llevar la factura a cero o lo más cerca posible. Se escribió "objetivo" y no "proyección" porque con nuestro criterio el crédito sobrante cubre ~20% de los cargos fijos en la A y ~80% en la B.
7. **Antecedente local.** Otro usuario de la misma cooperativa tenía el alta como Usuario-Generador casi terminada: se mencionó sin identificarlo ni nombrar la localidad, como forma de precisar pronto el valor real de la inyección.

**Lectura de la factura (cooperativa bonaerense).**
- Período de facturación ≠ mes de consumo: la factura "09/2026" leía del 28/06 al 27/07 → corrimiento de dos meses.
- Pares de valores iguales en el cuadro comparativo = lectura bimestral repartida.
- Tarifa validada contra el cuadro OCEBA Área Atlántica de julio 2026 (tramo R6 700–1.400 kWh: $246,9288; cargo fijo $27.397,41).
- CTT (Cargo de Transición Tarifaria) ~$15,45/kWh: proporcional, suma al costo del kWh.
- Multiplicador 1,36501 (IVA 21 + 5,5 + 0,001 + 6 + 4). Alumbrado público ($33.336) y servicios sociales ($16.100) fijos, exentos de IVA → dentro de `cargo_fijo_mensual` ($86.833).
- Inyección: 50% del promedio de R1–R7 = $115,52/kWh (sólo usado en la conversación, no en el PDF).

**Generación.** Planillas del simulador de Oriens (HSP × kWp × 30 × 0,90): el asesor pidió usarlas tal cual, sin descontar más y sin decir en la propuesta que son conservadoras.

**Decisiones de formato.** Título "Central solar híbrida – Gerardo Muglia"; sin localidad; sin teléfono al final (en este caso); "Cómo avanzamos" arranca en el relevamiento técnico; sin la nota del costo del trámite de alta.

**Pendientes que quedaron del lado del asesor:** qué hace la cooperativa con el saldo a favor anual y qué potencia de generación admite en T1R (menos de 10 kW) con 10,08 y 12,6 kWp sobre un inversor de 20 kW con limitador.

Config: `ejemplo_config_muglia.json` · generador de textos: `ejemplo_make_config_muglia.py` · PDF: `ejemplo_muglia.pdf`.
