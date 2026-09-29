# Checklist de verificación

Correr antes de entregar. El patrón del script está en el ejemplo de abajo.

## Datos de entrada
- [ ] Los 12 consumos coinciden con el cuadro comparativo de la factura, están asignados al mes calendario de lectura (no al período de facturación) y suman el anual declarado.
- [ ] El tramo de la factura coincide con el cuadro oficial (OCEBA por área, en PBA) y los tramos para la inyección salen de ese mismo cuadro.
- [ ] `kWh × costo_real_kwh + cargo_fijo_mensual` reproduce el total de la última factura con diferencia chica.
- [ ] Los 12 valores de generación de **cada** alternativa suman el anual declarado y dan el rendimiento por kWp esperado; se sabe qué factor de pérdidas trae la planilla.
- [ ] El multiplicador impositivo reconstruido componente por componente coincide con `total_factura / energía_neta`.
- [ ] `costo_real_kwh` = (cargo variable del tramo vigente + transporte o CTT por kWh) × multiplicador.
- [ ] `valor_inyeccion_kwh` = promedio de los cargos variables de todos los tramos / 2, **sin** multiplicador.
- [ ] Subtotales y totales con IVA coinciden con los presupuestos.

## Motor
- [ ] En **cada** mes de **cada** alternativa: `autoconsumo + batería + compra a red = consumo`.
- [ ] En **cada** mes de **cada** alternativa: `autoconsumo + batería + inyección = generación`.
- [ ] Con recupero: ahorro año 2+ = `autoconsumo × precio_auto + inyectado × precio_iny`; ahorro año 1 = `autoconsumo × precio_auto` (si `anios_sin_inyeccion = 1`).
- [ ] Sin recupero: ahorro = `autoconsumo × precio_auto` y factura con el sistema = `12 × cargo_fijo + compra_a_red × precio_auto`.
- [ ] Autoconsumo% + inyección% = 100.
- [ ] Inversión en pesos = USD × TC.

## Coherencia interna
- [ ] En invierno, verificar si hay excedente: comparar generación contra consumo diurno mes a mes.
- [ ] `credito_muerto` (crédito no utilizado al cierre): si es alto, el sistema está sobredimensionado y parte del ahorro puede ser ficticio.
- [ ] Saturación: si todas las alternativas ahorran lo mismo desde el año 2, avisarle al asesor antes de armar el PDF.
- [ ] Uso diario máximo de la batería vs capacidad ciclable de cada banco: si entra en el chico, la batería extra es respaldo.
- [ ] Generación anual vs consumo anual: si inyecta más de lo que compra, revisar con la distribuidora.
- [ ] TNA idéntica entre alternativas.

## Textos
- [ ] Cada cifra citada en la prosa coincide con la calculada.
- [ ] Ningún valor viejo sobrevive: buscar en el JSON completo las cifras de versiones anteriores.
- [ ] La cantidad de pasos de la metodología coincide con el subtítulo.
- [ ] Ninguna frase induce a elegir una alternativa (salvo el tono comercial que pida el asesor, siempre con cifras de todas).
- [ ] No se menciona la zona donde vive el cliente (tampoco en `ubicacion` ni en el nombre de la distribuidora).
- [ ] Sin recupero: no queda ninguna cifra de repago ni la palabra "recupero" en títulos, filas o metodología.
- [ ] El crédito por inyección no se repite más de lo necesario (en el caso Muglia, dos menciones).

## Ejemplo de script

```python
import json, sys
sys.path.insert(0, 'scripts')
import build_propuesta_hibrido_flex as B

cfg = json.load(open('config.json', encoding='utf-8'))
d = B.compute(cfg)
PA = cfg['economia']['costo_real_kwh']
PI = cfg['economia'].get('valor_inyeccion_kwh', 0.0)

for r in d['resultados']:
    b = r['bal']
    auto = b['directo'] + b['bateria']
    for x in b['detalle']:
        assert abs(x['directo'] + x['bateria'] + x['red'] - x['cons']) < 0.5, x['mes']
        assert abs(x['directo'] + x['bateria'] + x['inyectado'] - x['gen']) < 0.5, x['mes']
    pi = PI if d['recupero'] else 0.0
    assert abs(b['ahorro'] - (auto * PA + b['inyectado'] * pi)) < 1
    assert abs(r['ahorro_a1_ars'] - auto * PA) < 1
    assert abs(b['factura'] - (12 * d['fijo'] + b['red'] * PA)) < 1 or d['recupero']
    print(r['nombre_corto'], 'OK', r['payback_txt'], f"credito muerto ${b['credito_muerto']:,.0f}")
```
