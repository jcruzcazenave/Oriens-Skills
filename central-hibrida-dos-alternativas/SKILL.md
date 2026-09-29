---
name: central-hibrida-dos-alternativas
description: Arma la propuesta PDF de Oriens para una central híbrida CON inyección a la red con dos o tres alternativas que difieren en batería y/o en cantidad de paneles, con o sin recupero según el cliente. Incluye el motor mes a mes con arrastre de crédito por inyección. USAR SIEMPRE que un asesor de Oriens pida "propuesta híbrida con dos alternativas", "comparame dos baterías", "una opción con más paneles y más baterías" o "presupuesto híbrido comparativo"; cuando haya dos o tres presupuestos del mismo cliente con inversor híbrido que difieran en batería, paneles o ambos; al actualizar una propuesta híbrida comparativa, recalcular o sacar su recupero; y al revisar sus supuestos (kWh inyectado, split diurno/nocturno, generación, lectura de la factura). Usar aunque no se diga "híbrido" si hay inversor híbrido, batería, inyección y más de una opción. NO usar para híbrido de un solo escenario, off-grid sin inyección, ni el plano de paneles.
---

# Central híbrida con dos alternativas

Genera el PDF comparativo de Oriens para un proyecto híbrido **con inyección**, donde el cliente elige entre dos o tres alternativas: distinta capacidad de batería sobre el mismo arreglo, o distinta cantidad de paneles **y** de baterías.

**Ningún cliente es igual.** La mayoría de las propuestas lleva el recupero de la inversión, pero hay clientes a los que no les interesa y el asesor pide sacarlo. El builder flexible cubre las dos formas; antes de armar, confirmar cuál corresponde (ver "Variantes por cliente"). Los casos ya resueltos, con lo que se aprendió en cada uno, están en `reference/aprendizajes_casos.md`: leerlo cuando el caso nuevo se parezca a alguno.

## Por qué existe esta skill

Los otros builders de Oriens no sirven para este caso:

| Builder | Qué hace | Por qué no alcanza acá |
|---|---|---|
| `build_propuesta.py` | Un solo escenario | No compara alternativas |
| `build_propuesta_offgrid.py` | Compara 2-3 baterías | **Sin inyección**: el excedente que no entra a la batería se pierde |
| `central-hibrida-...-sin-bateria` | Híbrido de un escenario | No tiene batería ni comparación |

En un híbrido con inyección, cada kWh generado tiene **tres destinos con tres valores distintos** (autoconsumo directo, batería, inyección), y el crédito por inyección se **arrastra de un mes al siguiente**. Con un modelo anual esto no se ve, y en consumos estacionales el resultado cambia por completo.

## Flujo de trabajo

### 1. Reunir insumos

Antes de calcular nada, hacen falta:

1. **Presupuestos de cada alternativa** en USD, subtotal sin IVA y total con IVA.
2. **Facturas del cliente**: 12 meses de consumo (el cuadro comparativo de la factura los trae) y el desglose completo de cargos e impuestos.
   Si las alternativas difieren en paneles, hace falta **una simulación de generación por alternativa**.
3. **Simulación de generación** o los datos para calcularla (kWp, ubicación, orientación, inclinación).
4. **Split diurno/nocturno** — preguntarlo, ver más abajo.
5. **Tipo de cambio** BNA venta del día.

### 2. Leer la factura correctamente

Ver `reference/metodologia_hibrido_comparativo.md` para el detalle. Los puntos que más se equivocan:

- **Usar el tramo tarifario vigente, no el promedio ponderado.** Las facturas suelen traer dos tramos (ej. 11 días a una tarifa y 19 a otra) porque hubo aumento a mitad de período. El modelo mira hacia adelante: corresponde el tramo nuevo. El ponderado subestima el ahorro desde el arranque.
- **Aplicar el mismo criterio al cargo fijo.** Si se toma el cargo variable del tramo nuevo, el cargo fijo también. (No cambia el ahorro —se cancela en los dos lados de la resta— pero sí la factura de referencia.)
- **Sumar al costo del kWh todo cargo proporcional al consumo**: el cargo de transporte, o el **CTT (Cargo de Transición Tarifaria, "CTT Art. 5 Res. 2018/186")** que traen las cooperativas bonaerenses. Sacar su valor por kWh dividiendo el importe por los kWh facturados (~$15/kWh en 2026).
- **Verificar si el IVA se recupera.** Un monotributista (27%) o un **consumidor final** residencial (21%) no lo computan como crédito fiscal: en ese caso el ahorro se mide **con** impuestos y la inversión también se computa **con** IVA. Los dos lados de la comparación, del mismo modo.
- **Mes de consumo ≠ período de facturación.** Mirar las fechas de lectura: en la Cooperativa de Las Flores la factura "período 09" lee del 28/06 al 27/07, o sea que refleja el consumo de **dos meses antes**. Asignar cada valor al mes calendario real; si no, los picos de consumo quedan desfasados contra la curva de generación.
- **Pares de valores iguales** en el cuadro comparativo (847/847, 1.273/1.273) indican lectura bimestral repartida en dos facturas. Usarlos tal cual.
- **Validar la tarifa contra el cuadro oficial.** En provincia de Buenos Aires, buscar el precio del tramo de la factura en los cuadros OCEBA por área (índice: `oceba.gba.gov.ar/nueva_web/s.php?i=17`; áreas Atlántica, Norte, Sur, Río de la Plata). El área cuyo tramo coincide exacto es la de la cooperativa, y de ese mismo cuadro salen los tramos para valorizar la inyección (paso 5).
- **Cargos fijos que no son energía**: alumbrado público y servicios sociales suelen ser fijos por mes y no llevan IVA ("importe exento"). Sumarlos a `cargo_fijo_mensual` para que la factura de referencia cierre contra la real. Si el alumbrado fuera un porcentaje de la energía, va al multiplicador.
- **Cerrar la factura**: `kWh × costo_real + cargo_fijo_mensual` tiene que dar el total de la factura con diferencia chica (la que deja el prorrateo de tramos).

### 3. Definir la generación — el supuesto más peligroso

**Primero, ver qué factor de pérdidas trae la planilla.** Hay dos tipos:

- **Planilla del simulador de Oriens** (`HSP × kWp × 30 días × 0,90`, fila "MES"): ya descuenta 10% de pérdidas. Los asesores lo consideran **conservador**: usar los valores tal cual, **sin descontar ningún porcentaje extra y sin aclarar en la propuesta que es conservador**. Verificarlo: enero da `HSP_ene × kWp × 30 × 0,90`.
- **Planilla sin pérdidas** (`HSP × kWp × días`, enero = `HSP_ene × kWp × 31`): sobreestima alrededor de un 25%. En ese caso, orden de preferencia:
  1. **PVGIS con las coordenadas reales del sitio** (`re.jrc.ec.europa.eu/pvg_tools/en/`), con la orientación e inclinación del relevamiento. PVGIS bloquea el acceso automatizado, así que hay que pedirle al asesor que lo corra y pase los doce valores.
  2. Si no hay PVGIS: reescalar la curva mensual de la planilla para que el total anual dé **1.425 kWh/kWp** (criterio Oriens, con 5% de pérdidas descontado). Dejar constancia de que es un valor de referencia, no una simulación del sitio.

Ante la duda sobre qué planilla es, preguntarle al asesor antes de corregir nada.

Si las alternativas difieren en paneles, cada una lleva su propia curva (`generacion_mensual_kwh` dentro del escenario). Con el mismo panel y la misma orientación, la curva de la alternativa grande es la chica × (paneles_B / paneles_A): chequearlo.

La forma mensual importa tanto como el total: define si en pleno invierno sobra generación para cargar la batería.

### 4. Preguntar el split diurno/nocturno

**No asumirlo.** Preguntar si el porcentaje diurno aplica todo el año o sólo a algunos meses. El default de Oriens es 50/50; si el asesor dice "40% diurno", confirmar si es anual o estacional — son dos modelos distintos. En residencias con consumo nocturno fuerte los asesores vienen usando 40% diurno / 60% nocturno anual.

Su impacto depende del sobredimensionamiento: en sistemas holgados casi no mueve el recupero (la batería absorbe el desplazamiento), en sistemas justos sí.

### 5. Valorizar la inyección — no inflarla

**Criterio Oriens:** el excedente vale el **50% del promedio, sin impuestos, de los cargos variables de TODOS los tramos** del cuadro tarifario de la categoría (ej. T1R tramos R1 a R7 del cuadro OCEBA del área), en pesos planos. Si la factura sólo muestra su propio tramo, buscar el cuadro completo (paso 2). Si la categoría tiene un único tramo, es la mitad de ese cargo. **No aplicarle el multiplicador impositivo** salvo que el asesor confirme expresamente que el crédito reduce la base imponible. Aplicarlo por las dudas infla el ahorro alrededor de un 30% y acorta el recupero medio año.

Confirmar con la distribuidora dos cosas antes de firmar, y dejarlas asentadas:
- el porcentaje efectivamente reconocido;
- si el crédito no usado **se arrastra** de un mes al siguiente.

El arrastre es decisivo en consumos estacionales: los meses de excedente acumulan el saldo que después absorbe el invierno.

### 6. Considerar el primer año sin inyección

El alta como Usuario-Generador demora entre 2 y 6 meses, a veces más. Por defecto usar `anios_sin_inyeccion: 1`: el año 1 ahorra **sólo por autoconsumo** y el crédito recién entra desde el año 2. Es conservador y verificable — si el trámite sale antes, el recupero mejora.

La comparativa muestra las dos cifras por separado ("Ahorro Año 1 · sin inyección" y "Ahorro anual desde el Año 2") para que el cliente vea el escalón sin sorpresas.

### 7. Verificar que la batería sirva en invierno ANTES de prometerlo

**Este es el chequeo que define si la propuesta tiene sentido.** En cada mes de invierno, comparar la generación contra el consumo *diurno solo*:

- Si `generación ≤ consumo diurno` → **no hay excedente y la batería aporta cero ese mes**. Las alternativas rinden idéntico. No se puede decir que la batería "ataca el invierno".
- Si hay excedente, medir cuántos kWh/día son: ese número, y no la capacidad nominal, es lo que la batería puede ciclar en invierno.

Es habitual que una batería de 16 kWh reciba los mismos 4 kWh/día que una de 5 en junio. Decirlo en la propuesta.

Comparar también el **uso diario máximo de la batería** (la noche de mayor consumo, normalmente diciembre/enero) contra la capacidad ciclable de cada banco. Si ya entra en el banco chico, en el grande la batería extra **no se usa para el consumo diario y funciona como respaldo**: describirlo así, sin inclinar la elección. Si la diferencia de invierno entre alternativas la explican los paneles extra y no la batería, decirlo.

### 7 bis. Chequear la saturación ANTES de armar el PDF

Cuando la generación supera al consumo anual, el crédito por inyección puede cubrir **toda la parte variable de la factura en todas las alternativas**. Entonces desde el año 2 todas ahorran exactamente lo mismo (el techo = consumo × costo_real), la diferencia entre alternativas queda en el año 1 y en el respaldo, y la opción cara sólo suma crédito que el cliente no llega a usar (`credito_muerto`). Si pasa, **marcárselo al asesor antes de armar el PDF**, con los números (ahorro por año, crédito sin usar, repago) y preguntar cómo sigue: presentar igual, revisar la configuración, o sacar el recupero (ver "Variantes por cliente").

### 8. Correr el builder

Usar el **builder flexible** para todas las propuestas nuevas:

```bash
python scripts/build_propuesta_hibrido_flex.py config.json "Propuesta Oriens - <Cliente>.pdf"
```

Acepta los mismos configs que `build_propuesta_hibrido.py` (reproduce sus números: probado con Van Waarde) y además: generación y arreglo por alternativa, recupero opcional, filas de la comparativa configurables y bloques opcionales. El builder original queda sólo por compatibilidad.

El script imprime por consola el balance de cada escenario (autoconsumo directo, aporte de batería, inyectado, comprado a red, factura con el sistema, ahorro y, si hay recupero, repago y crédito no utilizado). Revisar esa salida antes de mirar el PDF.

**Generar los textos desde el motor.** Las cifras de la prosa (generación, kWh/día de batería en invierno, factura con el sistema, reservas) salen de `compute()`: armar el config con un script que calcula y formatea con `ar()`, como `reference/ejemplo_make_config_muglia.py`. Así, cuando el asesor cambia un supuesto, se regenera todo y no sobrevive ningún número viejo.

El esquema del config está en `reference/config_schema.md`. Ejemplos reales completos: `reference/ejemplo_config_van_waarde.json` (mismo arreglo, con recupero; PDF en `reference/ejemplo_van_waarde.pdf`) y `reference/ejemplo_config_muglia.json` (distintos paneles y baterías, sin recupero; PDF en `reference/ejemplo_muglia.pdf`).

### 9. Auditar los números

Antes de entregar, correr las verificaciones de `reference/checklist_verificacion.md`. Como mínimo:

- Las dos identidades cierran en **cada** mes de **cada** alternativa:
  `autoconsumo + batería + compra a red = consumo` y `autoconsumo + batería + inyección = generación`.
- El ahorro reconstruido a mano (`autoconsumo × precio_auto + inyectado × precio_iny`) coincide con el del motor. Sin recupero, `precio_iny = 0`: ahorro = `autoconsumo × precio_auto` y factura con el sistema = `12 × cargo_fijo + compra_a_red × precio_auto`.
- Cada número citado en la prosa del PDF coincide con el calculado.
- **Barrer los valores viejos**: cuando se cambia un supuesto, los textos del config quedan desactualizados. Buscar las cifras anteriores en el JSON completo y confirmar que no sobrevive ninguna.

### 10. Guardar en Drive

Si el asesor lo pide, usar la skill `guardar-en-google`.

## El PDF: cuatro páginas

| Página | Contenido |
|---|---|
| 1 | Encabezado, lectura del consumo, presupuestos comparativos lado a lado |
| 2 | Comparativa en un vistazo + nota (opcional) + balance mensual |
| 3 | Gráfico generación vs consumo (una serie por alternativa si los arreglos difieren) + metodología |
| 4 | Anexo de financiación con TNA + notas + próximos pasos |

El bloque de condiciones de pago de la página 2 es **opcional**: si el config no trae `condiciones`, desaparece entero y la página arranca con la comparativa. Lo mismo `nota_comparativa`, `telefono`, `ubicacion` y `proximos_pasos`.

## Variantes por cliente

Se resuelven con `opciones` en el config, sin tocar el builder:

| Pedido del asesor | Cómo se configura |
|---|---|
| Propuesta estándar | `mostrar_recupero: true` (default). Filas: año 1 sin inyección, año 2+, reducción, repago |
| "Al cliente no le interesa cuándo recupera" | `mostrar_recupero: false`. La inyección se muestra sólo como energía (reparto de cada kWh, inyección potencial); la factura con el sistema y el ahorro se calculan **sin** inyección; la metodología explica el reparto de la energía en vez del recupero |
| Sacar o agregar filas de la comparativa | `filas_comparativa: [claves]` (catálogo en `config_schema.md`) |
| Alternativas con distinta cantidad de paneles | `n_paneles`, `kwp` y `generacion_mensual_kwh` dentro de cada escenario |

Decisiones que tomó el asesor en el caso sin recupero (Muglia), útiles como punto de partida si se repite:

- Sin recupero, el ahorro en USD y el porcentaje de reducción terminaron **fuera** de la comparativa: la diferencia de ahorro entre alternativas era chica frente a la diferencia de precio, y el porcentaje no reflejaba lo que pasa cuando se reconoce la inyección. Quedaron "Factura promedio actual" y "Factura promedio con el sistema sin inyección".
- La inversión con IVA y su equivalente en pesos también salieron de la comparativa: ya están en la página 1 y en la financiación.
- La nota comparativa se sacó; su contenido quedó en la metodología.
- El crédito por inyección se nombra **dos veces como máximo**: en la lectura del consumo (el crédito **reduce** los cargos fijos, en afirmativo, una vez aprobada el alta; sin cuantificar y aclarando que no está incluido en el análisis) y como cierre del paso "qué se sigue pagando", en negrita: el objetivo es llevar la factura a cero o lo más cerca posible.
- Se agregó un paso de metodología sobre **días nublados seguidos**, lo que los promedios no muestran. Usa `reserva_amanecer()` para dar, por alternativa, la reserva con la que amanece el banco y los kWh útiles de la batería extra en horas de consumo. No prometer que cubre varios días: la batería extra demora el uso de la red y es respaldo ante cortes.
- Si hay un antecedente de alta como Usuario-Generador en la misma cooperativa, se puede mencionar sin identificar a la persona ni la localidad ("otro usuario de la misma cooperativa").

## Reglas de redacción

**El documento al cliente es objetivo, no persuasivo.** No inducir la elección de una alternativa sobre la otra. Nada de "la razón para elegirla es X", ni "los USD N adicionales tardan M años en pagarse solos", ni argumentos sobre cuál conviene. La nota comparativa **describe** qué hace cada opción con la energía, con los números, y deja la conclusión al lector. El análisis de cuál conviene va en la conversación con el asesor, no en el PDF.

El asesor puede pedir un tono más comercial en algún punto (por ejemplo, el valor de la batería extra ante días nublados). Se hace **con información**: cifras de todas las alternativas, sin exagerar lo que cubre. Si una frase que pide el asesor afirma algo que el cálculo no sostiene (ej. "la proyección es factura cero" cuando una alternativa no llega), ajustar la palabra ("el objetivo es") y avisarle en la conversación.

**No mencionar dónde vive el cliente** ni caracterizar su zona ("suministro rural", "zona con cortes frecuentes"). Dejar `ubicacion` vacía y nombrar a la distribuidora en forma genérica ("la cooperativa eléctrica") si su nombre incluye la localidad.

**Título**: el asesor puede pedir el nombre del cliente en el título ("Central solar híbrida – Nombre Apellido").

**Teléfono**: por defecto va al final de la página 4 (`telefono: "+54 9 11 2251-8959"`) en lugar de redes, mail o web. Hay propuestas donde el asesor lo saca: omitir la clave.

**Próximos pasos**: en el último caso el asesor sacó "confirmación de la alternativa elegida y firma del contrato" y arrancó en el relevamiento técnico del sitio. Tampoco quiso la nota "el costo del trámite de alta como Usuario-Generador no está incluido".

**Respaldo ante cortes**: declarar siempre la **capacidad nominal** de la batería, no la útil, acompañada de las horas de autonomía. Los kWh útiles y la carga de respaldo asumida se configuran aparte (`respaldo_kwh_utiles`, `carga_respaldo_kw`) y no se imprimen.

**TNA de la financiación**: calcularla como TIR sobre el **monto efectivamente financiado** (contado menos anticipo), no sobre el total del equipo, y aclararlo en una nota. Verificar que dé el mismo valor en las dos alternativas: si difiere, hay un error en los datos de cuotas. Referencia de la financiación propia Oriens: 6 cuotas TNA 10%, 12 cuotas 12%, 24 cuotas 14%.

## Errores conocidos, de los caros

1. **Generación sin pérdidas** → sobreestima ~25% y puede hacer que el crédito por inyección cubra el 100% de la factura, con lo cual las dos alternativas dan idéntico ahorro y la comparación pierde sentido.
2. **Inyección con multiplicador impositivo** → infla el ahorro ~30%.
3. **Prometer batería en invierno sin verificar el excedente** → la promesa central de la propuesta no se cumple.
4. **Cambiar la capacidad de batería para redondearla en el PDF** → mueve el modelo. Usar `bateria_kwh_nominal` para lo que se muestra y `bateria_kwh` para lo que se calcula.
5. **Sobredimensionar contra el consumo anual** → si el sistema inyecta más de lo que el cliente compra en el año, averiguar qué hace la distribuidora con el saldo positivo y si acepta esa potencia instalada contra la demanda contratada (en T1R residencial, menos de 10 kW; el limitador del inversor ayuda pero hay que confirmarlo).
6. **Asignar el consumo al mes de facturación y no al de lectura** → desfasa dos meses los picos contra la generación.
7. **Recortar la generación del simulador de Oriens** → ya trae 10% de pérdidas y el asesor la considera conservadora.
8. **Dejar cifras de ahorro o repago al sacar el recupero** → barrer todo el config: filas, notas, metodología y títulos ("Cómo se calcula el recupero").

## Archivos

```
central-hibrida-dos-alternativas/
├── SKILL.md
├── scripts/
│   ├── build_propuesta_hibrido_flex.py ← el builder a usar (flexible)
│   ├── build_propuesta_hibrido.py   ← builder original + motor balance_anual()
│   ├── build_propuesta.py           ← provee ar(), usd() y LOGO
│   └── _style.css                   ← estilos compartidos de Oriens
├── reference/
│   ├── metodologia_hibrido_comparativo.md
│   ├── config_schema.md
│   ├── checklist_verificacion.md
│   ├── aprendizajes_casos.md        ← casos resueltos y lo aprendido en cada uno
│   ├── ejemplo_config_van_waarde.json
│   ├── ejemplo_van_waarde.pdf
│   ├── ejemplo_config_muglia.json
│   ├── ejemplo_make_config_muglia.py ← patrón: textos generados desde el motor
│   └── ejemplo_muglia.pdf
└── assets/                          ← imágenes de equipos
```

Dependencia: `weasyprint` (`pip install weasyprint --break-system-packages`).
