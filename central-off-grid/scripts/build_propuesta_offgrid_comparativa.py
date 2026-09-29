#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builder de la propuesta OFF GRID de Oriens Energia Solar — 1 a 3 alternativas
comparadas. Sistema en paralelo a la red, SIN inyeccion de excedente.

Uso:
    python build_propuesta_offgrid_comparativa.py config.json "salida.pdf"

Todo sale del JSON: no hay datos de cliente ni numeros escritos a mano aca.
Las alternativas pueden diferir en cantidad de paneles, en bateria, o en ambas.
Ver reference/metodologia_offgrid_comparativa.md para las formulas.
"""
import json, sys, os

from weasyprint import HTML, CSS

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

LOGO = '''<svg viewBox="0 0 340 66" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="gold" x1="0" y1="1" x2="1" y2="0">
<stop offset="0" stop-color="#E1A027"/><stop offset="0.5" stop-color="#F0C24B"/><stop offset="1" stop-color="#F6D673"/></linearGradient></defs>
<g transform="translate(35,33)">
<circle cx="0" cy="0" r="22.5" fill="none" stroke="url(#gold)" stroke-width="6"/>
<circle cx="1.5" cy="-0.8" r="25" fill="none" stroke="#E7B23C" stroke-width="2.4" opacity="0.9"/>
<circle cx="-1.2" cy="1.2" r="18.6" fill="none" stroke="#F4D373" stroke-width="1.8" opacity="0.75"/>
</g>
<text x="76" y="40" font-family="Poppins" font-weight="400" font-size="31" letter-spacing="7" fill="#3d3d3d">ORIENS</text>
<text x="80" y="57" font-family="Poppins" font-weight="500" font-size="10.5" letter-spacing="7.5" fill="#8f8f8f">ENERGIA SOLAR</text>
</svg>'''


# ---------------- formato ----------------
def ars(v, dec=0):
    s = f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return "$" + s


def usd(v, dec=1):
    s = f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return "USD " + s


def num(v, dec=0):
    return f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def pct(v, dec=0):
    return num(v * 100, dec) + " %"


# ---------------- tarifa ----------------
def tramo_de(consumo, tramos):
    for t in tramos:
        if t["hasta"] is None or consumo <= t["hasta"] - 0.01:
            return t
    return tramos[-1]


def factura(consumo, tar):
    """Factura mensual a partir del consumo facturado (kWh).

    modo 'bloque': TODO el consumo se cobra al precio del tramo alcanzado y el cargo
    fijo es el de ese tramo (asi facturan la mayoria de las cooperativas).
    modo 'plano': un unico precio y un unico cargo fijo.
    """
    if tar.get("modo", "bloque") == "plano":
        precio, cf = tar["precio_kwh"], tar.get("cargo_fijo", 0.0)
    else:
        t = tramo_de(consumo, tar["tramos"])
        precio, cf = t["precio_kwh"], t["cargo_fijo"]
    sub = consumo * precio + cf + consumo * tar.get("cargo_variable_kwh", 0.0)
    return sub * (1 + tar.get("leyes_frac", 0.0) + tar.get("iva_frac", 0.0))


# ---------------- calculos ----------------
def generacion_de(sis, alt):
    """Generacion mensual de una alternativa: propia, o escalada desde la base
    por cantidad de paneles."""
    if alt.get("generacion_mensual_kwh"):
        return list(alt["generacion_mensual_kwh"])
    base = sis["generacion_base"]
    k = alt["paneles"] / base["paneles"]
    return [g * k for g in base["mensual_kwh"]]


def calcular(cfg):
    con, sis, sup = cfg["consumo"], cfg["sistema"], cfg["supuestos"]
    tar = con["tarifa"]
    dia_frac = sup.get("autoconsumo_dia_frac", 0.5)
    efic = sup.get("bateria_eficiencia", 0.9)
    reserva = sup.get("reserva_bateria_kwh", 0.0)
    tc = sup["tc"]
    ev_kwh_100 = cfg.get("futuro", {}).get("consumo_ev_kwh_100km", 17)

    cons = con["meses_kwh"]
    cons_anual = sum(cons)
    fact_sin = [factura(c, tar) for c in cons]
    fact_sin_anual = sum(fact_sin)

    alts = []
    for a in cfg["alternativas"]:
        gen = generacion_de(sis, a)
        bat_util = max(a.get("bateria_util_kwh", 0.0) - reserva, 0.0)
        filas, autoc, fact_con_anual, excedente = [], 0.0, 0.0, 0.0
        for i in range(12):
            c, g, d = cons[i], gen[i], DIAS[i]
            dia = dia_frac * c
            noche = c - dia
            directo = min(dia, g)
            sobra = g - directo
            aporte = min(noche, bat_util * efic * d, sobra * efic) if bat_util > 0 else 0.0
            carga = aporte / efic if efic else 0.0
            facturado = max(c - directo - aporte, 0.0)
            f_con = factura(facturado, tar)
            autoc += directo + aporte
            excedente += sobra - carga
            fact_con_anual += f_con
            filas.append(dict(mes=MESES[i], consumo=c, gen=g, directo=directo, bateria=aporte,
                              facturado=facturado, f_sin=fact_sin[i], f_con=f_con,
                              excedente=sobra - carga))
        ahorro = fact_sin_anual - fact_con_anual
        alts.append(dict(
            cfg=a, filas=filas, gen=gen, gen_anual=sum(gen), paneles=a["paneles"],
            kwp=a["paneles"] * sis["panel_wp"] / 1000,
            autoconsumo=autoc, cobertura=autoc / cons_anual if cons_anual else 0,
            facturado_anual=cons_anual - autoc, fact_con_anual=fact_con_anual,
            excedente=excedente, km_ev=excedente / ev_kwh_100 * 100 if ev_kwh_100 else 0,
            ahorro_anual=ahorro, ahorro_mensual=ahorro / 12,
            ahorro_frac=ahorro / fact_sin_anual if fact_sin_anual else 0,
            ahorro_usd=ahorro / tc,
            respaldo=bool(a.get("bateria_kwh")),
        ))
    return dict(cons=cons, cons_anual=cons_anual, fact_sin=fact_sin,
                fact_sin_anual=fact_sin_anual, fact_sin_mensual=fact_sin_anual / 12,
                alts=alts, dia_frac=dia_frac, efic=efic, tc=tc)


# ---------------- html ----------------
def render(cfg, d):
    doc, cli, sis, con = cfg["documento"], cfg["cliente"], cfg["sistema"], cfg["consumo"]
    alts = d["alts"]
    A = alts[0]
    resp = cfg.get("respaldo")
    fut = cfg.get("futuro") if doc.get("mostrar_futuro", True) else None
    ver_ahorro = doc.get("mostrar_ahorro", True)
    ver_mes = doc.get("mostrar_mes_a_mes", True)
    ver_comp = doc.get("mostrar_comparativa", True)

    rh = (f'<div class="rh"><div><div class="rht">{doc["titulo"]}</div>'
          f'<div class="rhc">{cli["nombre"]}</div></div>{LOGO}</div>')

    # ---- pagina 1 ----
    cards = ""
    for a in alts:
        ac = a["cfg"]
        cls = "card gold" if a is alts[-1] else "card"
        cards += f'''<div class="{cls}"><span class="tag"></span>
<div class="ttl">Alternativa {ac["id"]} — {ac["nombre"]}</div>
<div class="pr">{usd(ac["total_usd"], 1)}</div>
<div class="small">total contado, IVA incluido</div>
<div class="txt">{ac["resumen"]}</div>
<div style="margin-top:8px">
<div class="kv"><span>Respaldo ante cortes</span><b>{"Sí" if a["respaldo"] else "No"}</b></div>
<div class="kv"><span>Paneles solares</span><b>{a["paneles"]} × {sis["panel_wp"]} Wp</b></div>
<div class="kv"><span>Potencia solar</span><b>{num(a["kwp"], 2)} kWp</b></div>
</div></div>'''

    p1 = f'''{rh}<div class="page">
<div class="eyebrow">{doc["eyebrow"]}</div>
<h1>{doc["titulo"]}</h1>
<div class="sub">{doc["subtitulo"]}</div>
<div class="prep">Preparada para</div>
<div class="prepline"><b>{cli["nombre"]}</b><span>{cli["ubicacion"]}</span><span>{cli["fecha"]}</span></div>
<div class="eyebrow">El proyecto</div>
<h2>Dos alternativas, una misma base</h2>
<p>{doc["intro"]}</p>
<div class="stats">
<div class="stat"><div class="big">{num(sis["inversor_kw"], 1)} kW</div><div class="cap">inversor off grid</div></div>
<div class="stat"><div class="big">{num(A["cfg"]["bateria_kwh"], 2)} kWh</div><div class="cap">batería de litio</div></div>
<div class="stat"><div class="big">{" o ".join(str(a["paneles"]) for a in alts)}</div><div class="cap">paneles, según alternativa</div></div>
<div class="stat gold"><div class="big">{" o ".join(num(a["kwp"], 2) for a in alts)} kWp</div><div class="cap">potencia solar</div></div>
</div>
<hr>
<div class="eyebrow">Punto de partida</div>
<h2>Su consumo hoy</h2>
<p>Analizamos {con["periodo_analizado"]} de su suministro de {con["distribuidora"]}
({con["tipo_usuario"]}). El consumo es estacional, con pico en verano, y la tarifa tiene cargo
fijo por tramo: los meses de mayor uso se pagan mucho más caro.</p>
<div class="stats">
<div class="stat"><div class="big">{num(d["cons_anual"])} kWh</div><div class="cap">consumo anual</div></div>
<div class="stat"><div class="big">{num(d["cons_anual"] / 12)} kWh</div><div class="cap">promedio mensual</div></div>
<div class="stat"><div class="big">{ars(d["fact_sin_mensual"])}</div><div class="cap">factura promedio mensual</div></div>
<div class="stat gold"><div class="big">{ars(d["fact_sin_anual"])}</div><div class="cap">factura anual actual</div></div>
</div>
<hr>
<div class="eyebrow">Las alternativas</div>
<h2>Qué resuelve cada una</h2>
<div class="cards">{cards}</div>
</div>'''

    # ---- pagina 2: respaldo + futuro ----
    esen = "".join(f"<li>{x}</li>" for x in resp["esenciales"]) if resp else ""
    difer = "".join(f"<li>{x}</li>" for x in resp["diferibles"]) if resp else ""
    p_resp = f'''<div class="eyebrow">El motivo de la consulta</div>
<h2>Qué pasa durante un corte de luz</h2>
<p>{resp["motivo"]} Con batería, el sistema toma el relevo de forma automática: cuando se corta
el suministro, las cargas esenciales siguen alimentadas y la casa no se entera. Este
comportamiento es <b>idéntico en las dos alternativas</b>, porque depende del inversor y de la
batería, no de la cantidad de paneles.</p>
<p>{resp["autonomia_ejemplo"]} El límite real no es la energía almacenada sino la potencia
simultánea: la batería entrega hasta {num(resp["descarga_max_kw"], 1)} kW. Por eso el respaldo se
organiza sobre un tablero de cargas esenciales.</p>
<div class="two">
<div><div class="box"><h3>Queda respaldado</h3><ul>{esen}</ul></div></div>
<div><div class="box"><h3>Queda fuera del respaldo</h3><ul>{difer}</ul></div></div>
</div>
<div class="note"><b>Se define en el relevamiento.</b> {resp["nota"]}</div>''' if resp else ""

    fut_rows = "".join(
        f'<div><div class="g1">Alternativa {a["cfg"]["id"]} · {a["cfg"]["nombre"]}</div>'
        f'<div class="g2">{num(a["excedente"])} kWh/año disponibles</div>'
        f'<div class="g3">→ ~{num(round(a["km_ev"], -2))} km de auto eléctrico</div></div>'
        for a in alts)
    p_fut = f'''<div class="eyebrow">Margen para lo que viene</div>
<h2>Energía propia disponible para nuevos consumos</h2>
<p>{fut["texto"]}</p>
<div class="grow">{fut_rows}</div>
<div class="note"><b>Una condición.</b> {fut["condicion"]}</div>''' if fut else ""

    p2_cuerpo = p_resp + ("<hr>" + p_fut if p_fut else "")

    # ---- pagina 3: comparativa + mes a mes ----
    def frow(label, fn):
        return f'<tr><td>{label}</td>' + "".join(f'<td class="b r">{fn(a)}</td>' for a in alts) + '</tr>'

    heads = "".join(f'<th class="r">{a["cfg"]["id"]} · {a["cfg"]["nombre"]}</th>' for a in alts)
    filas_ahorro = ""
    if ver_ahorro:
        filas_ahorro = (
            frow("Generación anual", lambda a: num(a["gen_anual"]) + " kWh")
            + frow("Energía solar usada por la casa", lambda a: num(a["autoconsumo"]) + " kWh/año")
            + frow("Cobertura del consumo actual", lambda a: pct(a["cobertura"]))
            + frow("Factura anual estimada", lambda a: ars(a["fact_con_anual"]))
            + '<tr class="hl"><td>Ahorro anual estimado</td>'
            + "".join(f'<td class="r">{ars(a["ahorro_anual"])}</td>' for a in alts) + '</tr>'
            + frow("Energía para nuevos consumos", lambda a: num(a["excedente"]) + " kWh/año")
            + frow("Inversión (contado, IVA incl.)", lambda a: usd(a["cfg"]["total_usd"], 1)))
    comp = f'''<table class="comp"><tr><th>&nbsp;</th>{heads}</tr>
{frow("Paneles solares", lambda a: f'{a["paneles"]} × {sis["panel_wp"]} Wp')}
{frow("Potencia solar instalada", lambda a: num(a["kwp"], 2) + " kWp")}
{frow("Inversor", lambda a: f'Off grid {num(sis["inversor_kw"], 1)} kW')}
{frow("Almacenamiento", lambda a: a["cfg"]["bateria_desc"])}
{frow("Respaldo ante cortes", lambda a: "Sí · cargas esenciales" if a["respaldo"] else "No")}
{filas_ahorro}
</table>'''

    genrows = "".join(
        f'<tr><td class="b">{MESES[i]}</td><td class="r">{num(d["cons"][i])}</td>'
        + "".join(f'<td class="r">{num(a["filas"][i]["gen"])}</td>'
                  f'<td class="r">{num(a["filas"][i]["excedente"])}</td>' for a in alts)
        + f'<td class="r">{num(A["filas"][i]["facturado"])}</td>'
          f'<td class="r">{ars(A["filas"][i]["f_con"])}</td>'
          f'<td class="r muted">{ars(d["fact_sin"][i])}</td></tr>'
        for i in range(12))
    sh1 = "".join(f'<th class="r" colspan="2">{a["cfg"]["id"]} · {a["paneles"]} paneles</th>' for a in alts)
    sh2 = "".join('<th class="r">generación</th><th class="r">excedente</th>' for _ in alts)

    bloque_mes = f'''<div class="note"><b>Por qué el ahorro es el mismo.</b> Sin inyección a la red, la casa sólo puede
aprovechar la energía que consume en el momento y la que entra en la batería
({num(A["cfg"]["bateria_util_kwh"], 2)} kWh útiles por noche). Ese tope se alcanza ya con
{alts[0]["paneles"]} paneles, así que los paneles adicionales no bajan más la factura de hoy:
generan el margen para los consumos de mañana.</div>
<div class="eyebrow">Mes a mes</div>
<h2>Generación, excedente y factura estimada</h2>
<table>
<tr><th rowspan="2">Mes</th><th class="r" rowspan="2">Consumo<br>kWh</th>{sh1}
<th class="r" colspan="2">Con la central</th><th class="r" rowspan="2">Factura<br>sin central</th></tr>
<tr>{sh2}<th class="r">kWh red</th><th class="r">factura</th></tr>
{genrows}
<tr class="total"><td>Año</td><td class="r">{num(d["cons_anual"])}</td>
{"".join(f'<td class="r">{num(a["gen_anual"])}</td><td class="r">{num(a["excedente"])}</td>' for a in alts)}
<td class="r">{num(A["facturado_anual"])}</td><td class="r">{ars(A["fact_con_anual"])}</td>
<td class="r">{ars(d["fact_sin_anual"])}</td></tr>
</table>
<div class="small">{doc["nota_generacion"]} El reparto del consumo se toma {pct(d["dia_frac"])}
diurno y {pct(1 - d["dia_frac"])} nocturno, y la batería se considera con {pct(d["efic"])} de
eficiencia de carga y descarga. Las columnas de red y factura son iguales en las dos alternativas.</div>
''' if ver_mes else ""

    comparativa = f'''<div class="eyebrow">Comparativa</div>
<h2>Las dos alternativas, lado a lado</h2>
<p>El inversor, la batería y la instalación son idénticos, y también lo es el respaldo ante los
cortes. La diferencia está en la cantidad de paneles: cuánta energía propia genera la casa.</p>
{comp}
{bloque_mes}'''

    if not ver_comp:
        comparativa = ""

    # ---- pagina 4: como funciona + condiciones ----
    nodos = [("Sol", "radiación"), ("Paneles", "generan energía"), ("Inversor", "convierte a 220 V"),
             ("Batería", "almacena"), ("Consumo", "su casa")]
    flow = '<div class="ar">→</div>'.join(
        f'<div class="n"><div class="t">{t}</div><div class="s">{s}</div></div>' for t, s in nodos)
    cond = "".join(f'<tr><td class="b" style="width:26%">{k}</td><td>{v}</td></tr>'
                   for k, v in cfg["condiciones"])

    bloque_funciona = f'''<div class="eyebrow">Cómo funciona</div>
<h2>Su sistema, explicado simple</h2>
<p>El equipo trabaja en paralelo al suministro de la red y no inyecta excedente: prioriza siempre
la energía solar, después la de la batería, y sólo toma de la red lo que falte. No hace falta
trámite de Usuario-Generador ni cambio de medidor.</p>
<div class="flow">{flow}</div>
<div class="two">
<div>
<div class="box"><h3>Generación</h3><p>Los paneles bifaciales de {sis["panel_wp"]} W captan luz por
sus dos caras y producen energía incluso con cielo parcialmente nublado.</p></div>
<div class="box"><h3>Conversión y control</h3><p>El inversor off grid de {num(sis["inversor_kw"], 1)} kW
transforma la energía a 220 V y prioriza el uso solar antes que la red.</p></div>
</div>
<div>
<div class="box"><h3>De día</h3><p>Lo que la casa consume mientras hay sol sale de los paneles, y
el sobrante carga la batería.</p></div>
<div class="box"><h3>De noche y en los cortes</h3><p>La energía guardada durante el día alimenta la
casa a la noche y sostiene las cargas esenciales cuando se corta el suministro.</p></div>
</div>
</div>
<hr>
<div class="eyebrow">Condiciones y alcance</div>
<h2>Cómo trabajamos</h2>
<table>{cond}</table>'''

    # ---- armado de paginas intermedias ----
    if ver_comp and (ver_mes or ver_ahorro):
        p2 = f'''{rh}<div class="page">{p2_cuerpo}</div>'''
        p3 = f'''{rh}<div class="page">{comparativa}</div>'''
        p4 = f'''{rh}<div class="page">{bloque_funciona}</div>'''
    elif ver_comp:
        p2 = f'''{rh}<div class="page">{p2_cuerpo}<hr>{comparativa}</div>'''
        p3 = ""
        p4 = f'''{rh}<div class="page">{bloque_funciona}</div>'''
    else:
        p2 = f'''{rh}<div class="page">{p2_cuerpo}<hr>{bloque_funciona}</div>'''
        p3 = p4 = ""

    # ---- pagina 5: presupuestos ----
    presu = ""
    for idx, a in enumerate(alts):
        ac = a["cfg"]
        items = "".join(f'<tr><td class="b">{i[0]}</td><td>{i[1]}</td><td class="c">{i[2]}</td></tr>'
                        for i in ac["items"])
        fin = "".join(f'<tr><td class="b">{r[0]}</td><td>{r[1]}</td><td class="r">{r[2]}</td>'
                      f'<td class="r b">{r[3]}</td></tr>' for r in ac["financiacion"])
        presu += f'''<div class="eyebrow">Alternativa {ac["id"]} — {ac["nombre"]}</div>
<h2>Detalle de la central <span class="muted">· Presup. N° {ac["presupuesto_nro"]}</span></h2>
<table><tr><th>Ítem</th><th>Descripción</th><th class="c">Cant.</th></tr>
{items}
<tr class="sub"><td></td><td class="r">Subtotal (sin IVA)</td><td class="c">{usd(ac["subtotal_usd"], 1)}</td></tr>
<tr class="sub"><td></td><td class="r">IVA (21% + 10,5%)</td><td class="c">{usd(ac["iva_usd"], 1)}</td></tr>
<tr class="total2"><td></td><td class="r">Total</td><td class="c">{usd(ac["total_usd"], 1)}</td></tr>
</table>
<table><tr><th>Modalidad</th><th>Adelanto</th><th class="r">Valor cuota</th><th class="r">Total USD</th></tr>
{fin}</table>
<div class="small">Financiación propia Oriens en dólares oficiales (BNA venta), instrumentada por
contrato de mutuo y e-cheqs o pagarés por cuota.</div>
{"<hr>" if idx < len(alts) - 1 else ""}'''

    p5 = f'''{rh}<div class="page">
<div class="eyebrow">Presupuesto</div>
<h2>Qué incluye cada alternativa</h2>
{presu}</div>'''

    # ---- pagina 6: fichas ----
    fichas = ""
    for f in cfg["fichas"]:
        sp = f["specs"]
        rows = ""
        for j in range(0, len(sp), 2):
            par = sp[j:j + 2]
            cells = "".join(f'<td class="k">{k}</td><td class="v">{v}</td>' for k, v in par)
            if len(par) == 1:
                cells += '<td class="k"></td><td class="v"></td>'
            rows += f"<tr>{cells}</tr>"
        img = f'<div class="fimg"><img src="{os.path.join(ASSETS, f["img"])}"></div>' if f.get("img") else ""
        fichas += f'''<div class="{"ficha" if f.get("img") else "ficha noimg"}">{img}<div class="fbody">
<div class="fcat">{f["cat"]}</div><div class="fname">{f["name"]}</div>
<div class="fsub">{f["sub"]}</div><table class="ft">{rows}</table></div></div>'''

    p6 = f'''{rh}<div class="page">
<div class="eyebrow">Ficha técnica · componentes</div>
<h2>Los productos de su central</h2>
<p>Equipos de primeras marcas, con garantía internacional. Estas son sus especificaciones.</p>
{fichas}
<div class="close"><div class="t">Empezá a controlar tu energía.</div>
<div class="c">www.oriens.com.ar · contacto@oriens.com.ar · @oriens.energia</div></div>
</div>'''

    return ("<!doctype html><html><head><meta charset='utf-8'></head><body>"
            f"{p1}{p2}{p3}{p4}{p5}{p6}</body></html>")


def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else "propuesta.pdf"
    d = calcular(cfg)
    pie = f'ORIENS ENERGÍA SOLAR · Propuesta OFF GRID para {cfg["cliente"]["nombre"]}'
    css = open(os.path.join(HERE, "_style_offgrid.css"), encoding="utf-8").read()
    css = css.replace("var(--pie)", f'"{pie}"')
    HTML(string=render(cfg, d), base_url=HERE).write_pdf(out, stylesheets=[CSS(string=css)])
    print(f"OK → {out}")
    print(f'  factura actual: {ars(d["fact_sin_anual"])}/año ({ars(d["fact_sin_mensual"])}/mes)')
    for a in d["alts"]:
        print(f'  {a["cfg"]["id"]} ({a["paneles"]} paneles): gen {num(a["gen_anual"])} kWh · '
              f'cobertura {pct(a["cobertura"], 1)} · ahorro {ars(a["ahorro_anual"])} · '
              f'excedente {num(a["excedente"])} kWh ({num(a["km_ev"])} km EV)')


if __name__ == "__main__":
    main()
