# Patrón: armar el config calculando con el motor y generando los textos desde esos números.
# Uso (desde la carpeta de la skill):
#   python reference/ejemplo_make_config_muglia.py            -> escribe config.json
#   python scripts/build_propuesta_hibrido_flex.py config.json "Propuesta Oriens - Gerardo Muglia.pdf"
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import build_propuesta_hibrido_flex as B
from build_propuesta import ar
M = B.MESES
cons = dict(zip(M, [1273,978,979,996,997,1380,1379,847,847,776,777,1273]))
genA = dict(zip(M, [1719,1634,1457,1257,1051,910,986,1157,1407,1459,1618,1677]))
genB = dict(zip(M, [2149,2043,1821,1571,1314,1138,1232,1446,1759,1824,2023,2097]))
MULT = 1 + 0.21 + 0.055 + 0.00001 + 0.06 + 0.04
comp = lambda n_pan, n_est, n_bat: [
    ["Paneles solares", "Jinko Tiger Neo Mono N-Type Bifacial 630 Wp · garantía 12 años", str(n_pan)],
    ["Estructura", "Kit estructura coplanar de aluminio", str(n_est)],
    ["Inversor híbrido", "Deye trifásico 20 kW · picos 40 kW · 2 MPPT · 5 años de garantía · WiFi y limitador", "1"],
    ["Baterías", "Litio Pylontech Fidus · 16,076 kWh c/u · IP65 · 8.000 ciclos · 10 años de garantía", str(n_bat)],
    ["Mano de obra", "Ingeniería, puesta en marcha, MO especializada y garantía", "1"],
    ["Mat. eléctricos", "Materiales eléctricos y de ferretería", "1"],
    ["Flete", "Transporte de equipos y personas", "Bonificado"]]
cfg = {
 "titulo": "Central solar híbrida – Gerardo Muglia",
 "subtitulo": "Análisis del escenario actual y propuestas comparativas",
 "cliente": "Gerardo Muglia", "ubicacion": "", "fecha": "10 de septiembre de 2026",
 "telefono": "+54 9 11 2251-8959",
 "consumo": {"anual_kwh": sum(cons.values()), "mensual_kwh": cons},
 "metodologia": {"autoconsumo_dia_frac": 0.4, "bateria_dod": 0.9, "bateria_eficiencia": 0.96,
                 "mes_inicio_idx": 8, "carga_respaldo_kw": 12502 / 8760},
 "economia": {"costo_real_kwh": (246.9288 + 21305.98 / 1379) * MULT,
              "cargo_fijo_mensual": 27397.41 * MULT + 33335.75 + 16100, "tc": 1535},
 "escenarios": [
  {"nombre": "Alternativa A · 16 paneles · 2 baterías", "nombre_corto": "Alternativa A",
   "resumen": "16 paneles · 10,08 kWp · Inversor híbrido Deye 20 kW · 2 baterías Pylontech Fidus",
   "n_paneles": 16, "kwp": 10.08, "inversor_kw": 20, "generacion_mensual_kwh": genA,
   "bateria_kwh": 32.152, "bateria_kwh_nominal": "32,2", "bateria_label": "32,2 kWh · 2 × Pylontech Fidus",
   "inversion_usd": 19166.2, "inversion_usd_con_iva": 22634.7, "componentes": comp(16, 4, 2),
   "financiacion": [["Contado", "50% (USD 11.317)", "USD 11.317", "USD 22.635", "—"],
                    ["6 cuotas", "40% (USD 9.054)", "USD 2.330", "USD 23.034", "10 %"],
                    ["12 cuotas", "30% (USD 6.790)", "USD 1.408", "USD 23.683", "12 %"],
                    ["24 cuotas", "20% (USD 4.527)", "USD 869", "USD 25.393", "14 %"]]},
  {"nombre": "Alternativa B · 20 paneles · 3 baterías", "nombre_corto": "Alternativa B",
   "resumen": "20 paneles · 12,6 kWp · Inversor híbrido Deye 20 kW · 3 baterías Pylontech Fidus",
   "n_paneles": 20, "kwp": 12.6, "inversor_kw": 20, "generacion_mensual_kwh": genB,
   "bateria_kwh": 48.228, "bateria_kwh_nominal": "48,2", "bateria_label": "48,2 kWh · 3 × Pylontech Fidus",
   "inversion_usd": 23053.6, "inversion_usd_con_iva": 27295.6, "componentes": comp(20, 5, 3),
   "financiacion": [["Contado", "50% (USD 13.648)", "USD 13.648", "USD 27.296", "—"],
                    ["6 cuotas", "40% (USD 10.918)", "USD 2.810", "USD 27.777", "10 %"],
                    ["12 cuotas", "30% (USD 8.189)", "USD 1.698", "USD 28.560", "12 %"],
                    ["24 cuotas", "20% (USD 5.459)", "USD 1.048", "USD 30.622", "14 %"]]}]}

cfg['opciones'] = {'mostrar_recupero': False}
d = B.compute(cfg)
A, Bb = d["resultados"]
det = lambda r, m: next(x for x in r["bal"]["detalle"] if x["mes"] == m)
dias = {"Jun": 30, "Jul": 31, "Dic": 31, "Ene": 31}
bd = lambda r, m: det(r, m)["bateria"] / dias[m]
invA = f"{ar(bd(A,'Jun'),0)} a {ar(bd(A,'Jul'),0)}"
invB = f"{ar(bd(Bb,'Jun'),0)} a {ar(bd(Bb,'Jul'),0)}"
verano = ar(max(bd(A, 'Dic'), bd(A, 'Ene')), 0)
fijo_txt = ar(round(d["fijo"], -2), 0)
DIAS = [31,28,31,30,31,30,31,31,30,31,30,31]
def reservas(r):
    U = r["bateria_kwh"] * 0.9 * 0.96
    out = []
    for i, m in enumerate(M):
        c, g = cons[m], r["gen"][i]
        E, N = (g - c * 0.4) / DIAS[i], c * 0.6 / DIAS[i]
        out.append(max(0, U - N) if E >= N else 0)
    return out
resA, resB = reservas(A), reservas(Bb)
llenos = [m for m, a, b in zip(M, resA, resB) if a > 0 and b > 0]
vacios = [m for m in M if m not in llenos]
pos = lambda v: [x for x in v if x > 0]
rA = f"{ar(min(pos(resA)),0)} y {ar(max(resA),0)}"
rB = f"{ar(min(pos(resB)),0)} y {ar(max(resB),0)}"
extra = 16.076 * 0.9 * 0.96
hs_extra = extra / cfg["metodologia"]["carga_respaldo_kw"]
print("meses que llenan:", len(llenos), "vacios:", vacios, "reserva A", rA, "B", rB, "extra", round(extra,1), "hs", round(hs_extra,1))
pa_txt = ar(d["pa"], 0)
meses_red = [m for m in M if det(A, m)["red"] > 0.5 or det(Bb, m)["red"] > 0.5]
print("meses con compra a red:", meses_red, "| bat/dia inv A", invA, "B", invB, "verano", verano)

cfg.update({
 "texto_lectura_consumo":
  f"<p>El suministro está categorizado como <b>T1R · Residencial sin subsidio</b> en la cooperativa eléctrica. "
  f"Sumando los doce meses facturados hasta el período 09/2026, el consumo asciende a <b>{ar(d['cons_anual'],0)} kWh al año</b>, "
  f"unos {ar(round(d['cons_anual']/12,-1),0)} kWh por mes en promedio. Considerando el cargo variable de energía del tramo vigente, "
  f"el cargo de transición tarifaria y los impuestos que se pagan en proporción al consumo —incluido el IVA, que en este caso "
  f"no se computa como crédito fiscal—, cada kWh tiene un costo real de <b>${pa_txt}</b>. Ese es el valor que evita cada kWh "
  f"generado y consumido en la casa.</p>"
  f"<p>El consumo tiene dos picos en el año: el invierno, con unos <b>1.380 kWh por mes</b> en junio y julio, y el verano, "
  f"con unos <b>1.270 kWh</b> en diciembre y enero. En primavera baja a unos 780 kWh por mes. Además de la energía, la factura "
  f"incluye cargos que no dependen de los kWh consumidos —el cargo fijo con sus impuestos, el alumbrado público y los servicios "
  f"sociales—, que suman unos <b>${fijo_txt} por mes</b> y hoy se pagan igual con cualquiera de las dos alternativas.</p>"
  f"<p>Es en esos cargos donde la energía inyectada a la red cobra sentido. Una vez aprobada el alta como Usuario-Generador, "
  f"el crédito por el excedente que se vuelca a la red reduce los cargos fijos de cada mes y achica todavía más "
  f"la factura. Ese efecto <b>no está incluido en este análisis</b>, porque todavía no está precisado con exactitud cómo lo "
  f"reconoce la cooperativa. Lo vamos a poder precisar a la brevedad: otro usuario de la misma cooperativa tiene el trámite de "
  f"alta prácticamente terminado.</p>",
 "intro_presupuestos":
  "Las dos propuestas son centrales híbridas con inyección del excedente a la red y usan el mismo inversor híbrido Deye "
  "trifásico de 20 kW. Se diferencian en el tamaño del arreglo solar —16 o 20 paneles— y en la capacidad de almacenamiento: "
  "dos o tres baterías Pylontech Fidus.",
 "intro_comparativa":
  "La tabla resume, para cada alternativa, cuánta energía genera, qué parte del consumo de la casa cubre, cuánto se sigue "
  "comprando a la red, cuánto excedente queda disponible para inyectar y qué respaldo ofrece ante un corte de luz. La factura "
  "con el sistema incluye los cargos fijos completos.",
 "nota_comparativa":
  f"<b>Sobre la diferencia entre las dos opciones.</b> Las dos usan el mismo inversor; la alternativa B suma cuatro paneles y "
  f"una tercera batería. Los paneles adicionales generan {ar(Bb['gen_anual']-A['gen_anual'],0)} kWh más por año y se notan sobre todo "
  f"en invierno: en junio y julio la batería de la alternativa A recibe unos {invA} kWh por día y la de la B unos {invB}, y la "
  f"energía comprada a la red pasa de {ar(A['bal']['red'],0)} a {ar(Bb['bal']['red'],0)} kWh al año. En las noches de mayor consumo, "
  f"en diciembre y enero, la batería entrega unos {verano} kWh por día en las dos alternativas, dentro de la capacidad de ambos "
  f"bancos. En la B, la tercera batería queda como reserva adicional ante cortes de luz y ante rachas de días nublados "
  f"(ver el paso 6 de la metodología): 48,2 kWh nominales contra 32,2.",
 "intro_balance":
  "Reparto mes a mes de la energía generada en cada alternativa, en kWh. «Directo» es lo que la casa consume de día en el "
  "momento en que se genera; «Batería», lo que se guarda para usar de noche; «Inyecc.», el excedente potencial que se vuelca "
  "a la red; «Red», lo que se sigue comprando a la cooperativa.",
 "metodologia_sub": "En seis pasos.",
 "metodologia_html":
  f"<ol class=\"mlist\">"
  f"<li><b>Cuánto genera cada alternativa.</b> La generación mes a mes surge de la simulación de Oriens para cada arreglo: "
  f"<b>{ar(A['gen_anual'],0)} kWh/año</b> con los 16 paneles (10,08 kWp) de la alternativa A y <b>{ar(Bb['gen_anual'],0)} kWh/año</b> "
  f"con los 20 paneles (12,6 kWp) de la B, equivalentes al <b>{ar(A['cobertura_gen'],0)}%</b> y al <b>{ar(Bb['cobertura_gen'],0)}%</b> "
  f"del consumo anual.</li>"
  f"<li><b>Cómo se reparte cada kWh.</b> El cálculo se hace mes a mes. Se estima que el <span class=\"gold\">40% del consumo</span> "
  f"ocurre de día y el 60% de noche. La generación cubre primero el consumo diurno; el excedente carga la batería hasta donde "
  f"alcance el consumo nocturno y su capacidad; lo que sobra queda como inyección potencial a la red. Lo que la generación no "
  f"llega a cubrir se compra a la cooperativa.</li>"
  f"<li><b>La batería en invierno.</b> En junio y julio la generación es la más baja del año y el consumo, el más alto. Aun así "
  f"queda excedente diurno para cargar la batería: unos {invA} kWh por día en la alternativa A y unos {invB} en la B. En esos dos "
  f"meses se concentra toda la energía que se sigue comprando a la red.</li>"
  f"<li><b>Cuánto vale cada kWh.</b> Cada kWh que se consume en la casa —directo o desde la batería— evita pagar el costo real "
  f"de <span class=\"gold\">${pa_txt}/kWh</span>. La energía inyectada no se incluye en este cálculo.</li>"
  f"<li><b>Qué se sigue pagando.</b> La factura con el sistema incluye la energía que todavía se compra a la red y los cargos "
  f"que no dependen del consumo, unos ${fijo_txt} por mes. Con eso, la factura promedio pasa de <b>${ar(A['fact_mes_hoy'],0)}</b> a "
  f"<b>${ar(A['fact_mes_solar'],0)}</b> por mes en la alternativa A y a <b>${ar(Bb['fact_mes_solar'],0)}</b> en la B. Los importes "
  f"están calculados con la tarifa vigente y un tipo de cambio de $1.535 por dólar. <b>Con el crédito por la energía inyectada, "
  f"el objetivo es llevar la factura a cero o lo más cerca posible de cero.</b></li>"
  f"<li><b>Lo que los promedios no muestran: días nublados seguidos.</b> El cálculo usa promedios mensuales, pero puede haber "
  f"rachas de varios días con muy poca radiación. En esos días cuenta la energía guardada de los días de sol: la mayor parte del "
  f"año el banco amanece con una reserva de {rA.replace(' y ', ' a ')} kWh en la alternativa A y de {rB.replace(' y ', ' a ')} kWh en la B. "
  f"La tercera batería suma unos <span class=\"gold\">{ar(extra,0)} kWh útiles</span>, cerca de {ar(hs_extra,0)} horas del consumo "
  f"promedio de la casa, y los 20 paneles de la B generan un 25% más aun con poca radiación: más horas sin tomar energía de la "
  f"red y más respaldo si un corte de luz coincide con días nublados.</li></ol>",
 "notas_financiacion": [
  "Los valores expresados incluyen IVA.",
  "Financiación propia ORIENS Energía Solar, instrumentada mediante contrato de mutuo entre las partes y emisión de pagarés o e-cheqs electrónicos por cuota.",
  "Financiación en USD oficiales Banco Nación; el tipo de cambio se toma al valor del día de cada pago.",
  "Tipo de cambio de referencia de esta propuesta: $1.535 por dólar (BNA venta, 10 de septiembre de 2026).",
  "La TNA indicada corresponde al monto financiado de cada plan, una vez descontado el anticipo.",
  "Centrales llave en mano: incluyen asesoramiento, ingeniería, flete, instalación y puesta en marcha."],
 "proximos_pasos": [
  "Relevamiento técnico del sitio: verificación de la superficie de montaje, orientación e inclinación definitivas y del tablero de conexión.",
  "Provisión de equipos e instalación: 15 a 20 días corridos desde el pago del anticipo.",
  "Puesta en marcha, configuración del inversor híbrido y del monitoreo, y entrega de la documentación de garantías."]})
cfg["opciones"] = {"mostrar_recupero": False}   # al cliente no le interesa el recupero
cfg.pop("telefono", None)                        # el asesor sacó el teléfono en este caso
cfg.pop("nota_comparativa", None)                # y la nota comparativa
json.dump(cfg, open("config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("config.json OK")
