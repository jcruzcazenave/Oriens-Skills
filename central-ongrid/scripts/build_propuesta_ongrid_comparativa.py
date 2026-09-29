#!/usr/bin/env python3
"""Propuesta On Grid de Oriens con 2 o 3 alternativas (comparativa).

Uso:
    python build_propuesta_ongrid_comparativa.py config.json "Propuesta Cliente.pdf"

Reutiliza el motor de cálculo, el gráfico y el estilo del builder de una
alternativa. Todo dato de cliente sale del JSON (ver
reference/ejemplo_config_comparativa_alaux.json).

Orden de páginas (criterio del asesor, caso Alaux):
  1. Portada + lectura del consumo + presupuestos lado a lado
  2. Resultados proyectados (tabla comparativa + nota + gráficos por alternativa)
  3. Generación mes a mes + metodología
  4. Qué es y qué incluye
  5. Fichas técnicas con fotos
  6. Financiación + Cómo avanzamos (visita técnica previa) + resumen
Opcional (mostrar_tabla_recupero: true): página de recupero año por año,
insertada antes de la financiación.

Textos: se pueden usar tokens {rep1}, {rep2}, {repopt1}, {tot1}, {sub1},
{cob1}, {gen1}, {dif_sub_12}, {dif_gen_12_pct}, etc. (1..N según alternativa)
que se completan con los resultados calculados.
"""
import copy
import json
import os
import sys

from weasyprint import CSS, HTML

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_propuesta_ongrid import (CAP_GRAFICO_LINEA, LEYENDA_LINEA, LOGO,  # noqa: E402
                                    MESES, ars, calcular, chart_svg, num, usd)

ASSETS = os.path.join(os.path.dirname(HERE), "assets")

EXTRA_CSS = '''
@page { @bottom-right { content: var(--pie); } }
.two{display:flex;gap:10px;}
.two .box.alt{flex:1;padding:10px 11px;margin:6px 0 0;}
.two h3{font-size:13.5px;margin:0 0 1px;}
.two .h3s{font-size:8.6px;margin:0 0 4px;}
.two table.comp td{font-size:8.2px;padding:3px 4px;line-height:1.3;}
.two table.comp th{font-size:7px;padding:3px 4px;}
.two table.comp tr.total td,.two table.comp tr.total2 td{font-size:9.2px;}
.lead p{font-size:10px;margin-bottom:6px;}
table.cmp td{font-size:9.3px;padding:3.5px 7px;} table.cmp th{font-size:7.6px;}
table.cmp tr.big td{font-family:Poppins;font-weight:700;color:#c99320;font-size:11.5px;}
table.rec td, table.fin td{font-size:8.8px;padding:4px 5px;}
table.rec th, table.fin th{font-size:7px;padding:4px 5px;}
svg.chart{width:100%;height:30mm;display:block;} .page .note{margin-top:6px;}
.ficha{display:flex;gap:16px;align-items:center;border:1px solid #ece9e2;border-radius:13px;padding:12px 14px;margin:0 0 10px;background:#fff;}
.fimg{width:150px;flex:0 0 150px;text-align:center;} .fimg img{max-width:150px;max-height:135px;}
.ftx{flex:1;} .ftx h3{font-family:Poppins;font-size:13px;margin:0 0 4px;color:#242424;}
table.fs td{font-size:9px;padding:3px 6px;} table.fs td:first-child{color:#9a9a9a;width:38%;}
'''

SUPUESTOS = ["consumo_mensual", "frac_diurno", "costo_kwh", "precio_inyeccion", "factura_anual_ars",
             "base_repago", "escalada", "degradacion", "anios_recupero", "aprovechamiento_diurno",
             "mantenimiento_usd_anual", "tc"]


def calcular_alternativas(cfg):
    for a in cfg["alternativas"]:
        c = {k: cfg[k] for k in SUPUESTOS if k in cfg}
        c.update(sistema=dict(paneles=a["paneles"], wp=a["wp"]), generacion_mensual=a["generacion_mensual"],
                 subtotal_usd=a["subtotal_usd"], total_usd=a["total_usd"])
        a["_cfg"], a["_d"] = c, calcular(c)
        c_opt = dict(c, escalada=cfg.get("escalada_optimista", 0.10))
        a["_rep_opt"] = calcular(c_opt)["repago_txt"]


def tokens(cfg):
    t = {}
    alts = cfg["alternativas"]
    for i, a in enumerate(alts, 1):
        d = a["_d"]
        t.update({f"rep{i}": d["repago_txt"], f"repopt{i}": a["_rep_opt"], f"tot{i}": usd(a["total_usd"]),
                  f"sub{i}": usd(a["subtotal_usd"]), f"cob{i}": num(d["cobertura"]), f"gen{i}": num(d["gen_anual"]),
                  f"ahorro{i}": usd(d["ahorro_usd"]), f"iny{i}": num(d["frac_iny"]), f"n{i}": a["paneles"],
                  f"kwp{i}": num(d["kwp"], 2)})
    for i in range(len(alts)):
        for j in range(i + 1, len(alts)):
            a, b = alts[i], alts[j]
            t[f"dif_sub_{i+1}{j+1}"] = usd(b["subtotal_usd"] - a["subtotal_usd"])
            t[f"dif_gen_{i+1}{j+1}_pct"] = num((b["_d"]["gen_anual"] / a["_d"]["gen_anual"] - 1) * 100)
    t["consumo_anual"] = num(sum(cfg["consumo_mensual"]))
    t["frac_diurno_pct"] = num(cfg["frac_diurno"] * 100)
    return t


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def fmt(s, T):
    return s.format_map(_Safe(T)) if isinstance(s, str) else s


def box(a):
    d = a["_d"]
    rows = "".join(f'<tr><td class="b">{it["item"]}</td><td>{it["desc"]}</td><td class="r b">{it["cant"]}</td></tr>'
                   for it in a["items"])
    ivas = "".join(f'<tr><td colspan="2" style="color:#8f8f8f">IVA ({num(v["pct"], 1)}%)</td>'
                   f'<td class="r" style="color:#8f8f8f;white-space:nowrap">{usd(v["monto"], 1)}</td></tr>' for v in a["iva"])
    nro = f' · Presupuesto N° {a["presupuesto_nro"]}' if a.get("presupuesto_nro") else ""
    return f'''<div class="box alt"><p class="bx-eyebrow">{a["nombre"]} · {a["tag"]}</p>
<h3>{a["paneles"]} paneles · {num(d["kwp"], 2)} kWp</h3><p class="h3s">{num(d["gen_anual"])} kWh/año{nro}</p>
<table class="comp"><tr><th>Item</th><th>Descripción</th><th class="r">Cant.</th></tr>{rows}
<tr class="total"><td colspan="2">Subtotal (sin IVA)</td><td class="r" style="white-space:nowrap">{usd(a["subtotal_usd"], 1)}</td></tr>{ivas}
<tr class="total2"><td colspan="2">Total</td><td class="r" style="white-space:nowrap">{usd(a["total_usd"], 1)}</td></tr></table></div>'''


def build(cfg, out):
    calcular_alternativas(cfg)
    T = tokens(cfg)
    alts = cfg["alternativas"]
    N = len(alts)
    cons = cfg["consumo_mensual"]
    fd = cfg["frac_diurno"]

    def crow(lbl, f, cls=""):
        return f'<tr{cls}><td>{lbl}</td>' + "".join(f'<td class="r">{f(a)}</td>' for a in alts) + '</tr>'

    comp = "".join([
        crow("Potencia instalada", lambda a: f'{num(a["_d"]["kwp"], 2)} kWp'),
        crow("Generación anual proyectada", lambda a: f'{num(a["_d"]["gen_anual"])} kWh'),
        crow(f"Cobertura del consumo anual ({T['consumo_anual']} kWh)", lambda a: f'{num(a["_d"]["cobertura"])} %'),
        crow("Energía autoconsumida", lambda a: f'{num(a["_d"]["auto_anual"])} kWh · {num(a["_d"]["frac_auto"])} %'),
        crow("Energía inyectada a la red", lambda a: f'{num(a["_d"]["iny_anual"])} kWh · {num(a["_d"]["frac_iny"])} %'),
        crow("Inversión (sin IVA)", lambda a: usd(a["subtotal_usd"])),
        crow("Inversión total (con IVA)", lambda a: usd(a["total_usd"])),
        crow("Ahorro neto año 1", lambda a: f'{usd(a["_d"]["ahorro_usd"])} · {ars(a["_d"]["ahorro_mes"])}/mes'),
        crow("Reducción de la factura", lambda a: f'{num(a["_d"]["reduccion"])} %'),
        crow("Repago estimado", lambda a: a["_d"]["repago_txt"], ' class="big"'),
    ])
    hdr_cmp = "<tr><th></th>" + "".join(f'<th class="r">{a["nombre"]} · {a["tag"]}</th>' for a in alts) + "</tr>"

    misma_gen = len({tuple(a["generacion_mensual"]) for a in alts}) == 1
    galts = alts[:1] if misma_gen else alts
    charts = "".join(f'<p class="cap-s" style="margin-top:4px">{a["nombre"]} · {a["paneles"]} paneles</p>{chart_svg(a["_cfg"], a["_d"])}'
                     for a in galts) if not misma_gen else (f'<p class="cap-s" style="margin-top:4px">{cfg.get("cap_grafico_unico", "Ambas alternativas")}</p>' + chart_svg(alts[0]["_cfg"], alts[0]["_d"]).replace('class="chart"', 'class="chart" style="height:55mm"', 1))
    lgd = (f'<div class="lgd"><span><i style="background:#e8e3d8"></i>Barra gris: consumo total</span>'
           f'<span>{LEYENDA_LINEA}Línea punteada: consumo diurno ({T["frac_diurno_pct"]} % del consumo del mes)</span>'
           f'<span><i style="background:#d2a12a"></i>Barra dorada: generación solar</span></div>')

    gh = "<tr><th>Mes</th><th class=\"r\">Consumo</th><th class=\"r\">Consumo diurno</th>" + "".join(
        f'<th class="r">Generación {a["paneles"]} paneles</th><th class="r">Cobertura</th>' for a in galts) + "</tr>"
    grows = ""
    for i in range(12):
        grows += f'<tr><td class="b">{MESES[i]}</td><td class="r">{num(cons[i])}</td><td class="r">{num(cons[i] * fd)}</td>'
        grows += "".join(f'<td class="r">{num(a["generacion_mensual"][i])}</td><td class="r">{num(a["generacion_mensual"][i] / cons[i] * 100)} %</td>' for a in galts)
        grows += "</tr>"
    grows += f'<tr class="total"><td>Año</td><td class="r">{num(sum(cons))}</td><td class="r">{num(sum(cons) * fd)}</td>'
    grows += "".join(f'<td class="r">{num(a["_d"]["gen_anual"])}</td><td class="r">{num(a["_d"]["cobertura"])} %</td>' for a in galts) + "</tr>"

    inc = "".join(f'<div class="blk"><p class="bt">{fmt(b["t"], T)}</p><p class="bd">{fmt(b["d"], T)}</p></div>' for b in cfg["incluye"])
    mets = "".join(f'<li><b>{fmt(m["t"], T)}</b> {fmt(m["d"], T)}</li>' for m in cfg["metodologia"])
    pasos = "".join(f'<li><b>{fmt(p["t"], T)}.</b> {fmt(p["d"], T)}</li>' for p in cfg["pasos"])

    def ficha(f):
        img = os.path.join(ASSETS, f["img"]) if not os.path.isabs(f["img"]) else f["img"]
        specs = "".join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in f["specs"])
        return (f'<div class="ficha"><div class="fimg"><img src="file://{img}"></div><div class="ftx">'
                f'<p class="eyebrow">{f["tipo"]}</p><h3>{f["titulo"]}</h3><table class="fs">{specs}</table></div></div>')
    fichas = "".join(ficha(f) for f in cfg["fichas"])

    fh = "<tr><th>Modalidad</th><th>Detalle</th>" + "".join(
        f'<th class="r">Cuota · Alt. {i}</th><th class="r">Total · Alt. {i}</th>' for i in range(1, N + 1)) + "</tr>"
    frows = ""
    for k, base in enumerate(alts[0]["financiacion"]):
        frows += f'<tr><td class="b">{base["modalidad"]}</td><td>{base["detalle"]}</td>'
        frows += "".join(f'<td class="r">{a["financiacion"][k]["cuota"]}</td><td class="r b">{a["financiacion"][k]["total"]}</td>' for a in alts)
        frows += "</tr>"
    notas = "".join(f"<li>{fmt(n, T)}</li>" for n in cfg["notas_financiacion"])

    lectura = "".join(f"<p>{fmt(p, T)}</p>" for p in cfg["lectura_html"])

    pag_rec = ""
    if cfg.get("mostrar_tabla_recupero", False):
        rh = "<tr><th></th>" + "".join(f'<th class="r" colspan="3">{a["nombre"]} · {usd(a["subtotal_usd"])}</th>' for a in alts) + "</tr>"
        rh += "<tr><th>Período</th>" + '<th class="r">Ahorro</th><th class="r">Acumulado</th><th class="r">Neto</th>' * N + "</tr>"
        rr = ""
        for fs in zip(*[a["_d"]["recupero"] for a in alts]):
            rr += f'<tr><td class="b">Año {fs[0]["anio"]}</td>'
            for f in fs:
                neto = ("+" if f["neto"] >= 0 else "−") + usd(abs(f["neto"])).replace("USD ", "")
                st = ' style="background:#fbf3df;font-weight:700;color:#242424"' if f["hl"] else ""
                rr += f'<td class="r"{st}>{usd(f["ahorro"])}</td><td class="r"{st}>{usd(f["acum"])}</td><td class="r"{st}>{neto}</td>'
            rr += "</tr>"
        pag_rec = f'''
<div class="page"><p class="eyebrow">Recupero de la inversión</p><h1>Recupero año por año</h1><hr>
 <table class="rec">{rh}{rr}</table>
 <div class="note">{fmt(cfg.get("nota_recupero", ""), T)}</div></div>'''

    P = {}
    P["portada"] = f'''
<div class="page">
 <p class="eyebrow">Propuesta integral</p>
 <h1>{cfg.get("titulo", "Central solar fotovoltaica")}</h1>
 <p class="sub">{fmt(cfg["subtitulo"], T)}</p>
 <hr>
 <p class="prep">Preparada para</p>
 <p class="prepline"><b>{cfg["cliente"]}</b> &nbsp;·&nbsp; {cfg["ubicacion"]} &nbsp;·&nbsp; {cfg["provincia"]} &nbsp;·&nbsp; {cfg["fecha"]}</p>
 <p class="eyebrow">Lectura del consumo</p>
 <h2>{cfg.get("h_consumo", "Cómo se está consumiendo hoy")}</h2>
 <div class="lead">{lectura}</div>
 <p class="eyebrow" style="margin-top:10px">Presupuestos</p>
 <h2>{fmt(cfg.get("h_presupuestos", "Alternativas sobre el mismo inversor"), T)}</h2>
 <div class="two">{"".join(box(a) for a in alts)}{(chr(60)+'/div><div class="note" style="margin-top:6px">' + fmt(cfg["nota_presupuestos"], T)) if cfg.get("nota_presupuestos") else ""}</div>
</div>'''
    P["resultados"] = f'''
<div class="page">
 <p class="eyebrow">Comparativa</p>
 <h1>Resultados proyectados</h1>
 <p class="sub">Qué produce cada alternativa y en cuánto se recupera la inversión</p>
 <hr>
 <p class="lead">{fmt(cfg["intro_resultados"], T)}</p>
 <div class="box"><table class="res cmp">{hdr_cmp}{comp}</table></div>
 <div class="note">{fmt(cfg["nota_resultados"], T)}</div>
 <p class="eyebrow" style="margin-top:12px">Generación vs. consumo</p>
 <p class="cap-s">{CAP_GRAFICO_LINEA}</p>
 {charts}
 {lgd}
</div>'''
    P["generacion"] = f'''
<div class="page">
 <p class="eyebrow">Generación y metodología</p>
 <h1>Generación mes a mes y cómo se calcula el repago</h1>
 <hr>
 <p class="cap-s">{fmt(cfg.get("cap_tabla_gen", ""), T)}</p>
 <table class="mes">{gh}{grows}</table>
 <p class="eyebrow" style="margin-top:12px">Metodología</p>
 <p class="cap-s">Cómo se calcula el recupero de inversión, en cinco pasos.</p>
 <ol class="met">{mets}</ol>
</div>'''
    P["incluye"] = f'''
<div class="page">
 <p class="eyebrow">La solución Oriens</p>
 <h1>Qué es y qué incluye</h1>
 <p class="sub">Una central lista para producir, llave en mano y 100% Oriens</p>
 <hr>
 <p class="lead">Más que vender equipos, entregamos una central solar lista para generar energía. La solución Oriens es integral y llave en mano: nos ocupamos de todo el proceso, de principio a fin, con personal propio.</p>
 {inc}
 <div class="note" style="margin-top:12px">{fmt(cfg["nota_alternativas"], T)}</div>
</div>'''
    P["fichas"] = f'''
<div class="page">
 <p class="eyebrow">Fichas técnicas</p>
 <h1>Componentes del sistema</h1>
 <p class="sub">{fmt(cfg.get("sub_fichas", "Los mismos equipos en todas las alternativas: sólo cambia la cantidad de paneles y de kits de estructura"), T)}</p>
 <hr>
 {fichas}
 <div class="note" style="margin-top:10px">{fmt(cfg.get("nota_fichas", ""), T)}</div>
</div>'''
    P["financiacion"] = f'''
<div class="page">
 <p class="eyebrow">Anexo · Financiación</p>
 <h1>Planes de pago disponibles</h1>
 <hr>
 <p class="cap-s">Financiación propia Oriens, en dólares oficiales Banco Nación. Valores con IVA.</p>
 <table class="fin">{fh}{frows}</table>
 <ul class="notas">{notas}</ul>
 <p class="eyebrow" style="margin-top:16px">Condiciones y siguientes pasos</p>
 <h2>Cómo avanzamos</h2>
 <ol class="met">{pasos}</ol>
 <div class="note">{fmt(cfg["resumen_html"], T)}</div>
</div>'''

    body = P["portada"] + P["resultados"] + P["generacion"] + P["incluye"] + P["fichas"] + pag_rec + P["financiacion"]
    html = f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><div class="rh">{LOGO}</div>{body}</body></html>'
    pie = cfg.get("pie", f"Propuesta On Grid · {cfg['cliente']}").replace('"', "'")
    css_extra = EXTRA_CSS.replace("var(--pie)", f'"{pie}"')
    HTML(string=html, base_url=HERE).write_pdf(out, stylesheets=[CSS(filename=os.path.join(HERE, "_style_ongrid.css")),
                                                                  CSS(string=css_extra)])
    for i, a in enumerate(alts, 1):
        d = a["_d"]
        print(f"Alt {i}: {a['paneles']} paneles · gen {num(d['gen_anual'])} kWh · cob {num(d['cobertura'])}% · "
              f"iny {num(d['frac_iny'])}% · ahorro {usd(d['ahorro_usd'])} · repago {d['repago_txt']} (opt {a['_rep_opt']})")
    print("OK →", out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: build_propuesta_ongrid_comparativa.py config.json salida.pdf")
    build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
