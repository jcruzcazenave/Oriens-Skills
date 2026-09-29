#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builder de la propuesta ON GRID de Oriens Energia Solar — un solo escenario.
Uso: python build_propuesta_ongrid.py config.json "Propuesta Cliente.pdf"

Todo sale del JSON: no hay datos de cliente en este archivo.
"""
import json, sys, os
from weasyprint import HTML, CSS

HERE = os.path.dirname(os.path.abspath(__file__))
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

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


def usd(v, dec=0):
    s = f"{v:,.{dec}f}".replace(",", ".")
    return "USD " + s


def num(v, dec=0):
    return f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


# ---------------- calculos ----------------
def calcular(cfg):
    """Deriva todos los numeros del proyecto. Nada se escribe a mano en el config."""
    d = {}
    sis = cfg["sistema"]
    d["kwp"] = sis["paneles"] * sis["wp"] / 1000.0

    cons = cfg["consumo_mensual"]
    gen = cfg["generacion_mensual"]
    fd = cfg["frac_diurno"]

    d["cons_anual"] = sum(cons)
    d["gen_anual"] = sum(gen)
    d["cons_mes_prom"] = d["cons_anual"] / 12.0
    d["cobertura"] = d["gen_anual"] / d["cons_anual"] * 100

    # mes a mes: lo que entra en autoconsumo es lo que cabe en el consumo diurno
    diurno = [c * fd for c in cons]
    aprov = cfg.get("aprovechamiento_diurno", 1.0)
    auto = [min(g, dd) * aprov for g, dd in zip(gen, diurno)]
    iny = [g - a for g, a in zip(gen, auto)]
    d["diurno"] = diurno
    d["auto"] = auto
    d["iny"] = iny
    d["auto_anual"] = sum(auto)
    d["iny_anual"] = sum(iny)
    d["frac_auto"] = d["auto_anual"] / d["gen_anual"] * 100
    d["frac_iny"] = 100 - d["frac_auto"]

    # ahorro año 1 a precio de hoy
    d["ahorro_auto"] = d["auto_anual"] * cfg["costo_kwh"]
    d["ahorro_iny"] = d["iny_anual"] * cfg.get("precio_inyeccion", 0)
    d["mant_usd"] = cfg.get("mantenimiento_usd_anual", 0)
    d["ahorro_ars"] = d["ahorro_auto"] + d["ahorro_iny"] - d["mant_usd"] * cfg["tc"]
    d["ahorro_usd"] = d["ahorro_ars"] / cfg["tc"]
    d["ahorro_mes"] = d["ahorro_ars"] / 12.0

    # factura actual estimada y post-solar
    d["factura_anual"] = cfg.get("factura_anual_ars") or 0
    if d["factura_anual"]:
        d["reduccion"] = d["ahorro_ars"] / d["factura_anual"] * 100
        d["factura_post"] = d["factura_anual"] - d["ahorro_ars"]

    # inversion
    d["inv_sin"] = cfg["subtotal_usd"]
    d["inv_con"] = cfg["total_usd"]
    d["inv_base"] = d["inv_con"] if cfg.get("base_repago", "con_iva") == "con_iva" else d["inv_sin"]
    d["inv_sin_ars"] = d["inv_sin"] * cfg["tc"]
    d["inv_con_ars"] = d["inv_con"] * cfg["tc"]

    # recupero: ahorro crece por tarifa+inflacion en USD, baja por degradacion del panel
    esc = cfg.get("escalada", 0.10)
    deg = cfg.get("degradacion", 0.005)
    filas, acum, repago = [], 0.0, None
    for i in range(1, cfg.get("anios_recupero", 12) + 1):
        bruto = (d["ahorro_auto"] + d["ahorro_iny"]) / cfg["tc"]
        a = bruto * ((1 + esc) ** (i - 1)) * ((1 - deg) ** (i - 1)) - d["mant_usd"]
        prev = acum
        acum += a
        hl = False
        if repago is None and acum >= d["inv_base"]:
            falta = d["inv_base"] - prev
            meses = max(1, min(12, round(falta / a * 12)))
            repago = (i - 1, meses)
            hl = True
        filas.append({"anio": i, "ahorro": a, "acum": acum, "hl": hl,
                      "neto": acum - d["inv_base"]})
    d["recupero"] = filas
    if repago:
        y, m = repago
        if y == 0:
            d["repago_txt"] = f"{m} meses"
        elif m == 12:
            d["repago_txt"] = f"{y + 1} años"
        else:
            d["repago_txt"] = f"{y} año{'s' if y > 1 else ''} {m} mes{'es' if m > 1 else ''}"
    else:
        d["repago_txt"] = "no se recupera en el plazo analizado"
    return d


# ---------------- grafico ----------------
LEYENDA_LINEA = ('<svg width="30" height="10" style="vertical-align:middle;margin-right:4px">'
                 '<line x1="1" y1="5" x2="29" y2="5" stroke="#5f5f5f" stroke-width="2" stroke-dasharray="5 3"/>'
                 '<circle cx="15" cy="5" r="2.6" fill="#5f5f5f"/></svg>')

CAP_GRAFICO_LINEA = ("Barras grises: consumo total del mes. Barras doradas: generación solar. La <b>línea punteada</b> "
    "que recorre las barras es el <b>consumo diurno</b>: mientras la barra dorada queda por debajo de la línea, "
    "toda la generación se autoconsume; cuando la supera, el excedente se inyecta a la red.")


def chart_svg(cfg, d):
    cons, gen, diur = cfg["consumo_mensual"], cfg["generacion_mensual"], d["diurno"]
    W, H, ml, mr, mt, mb = 1000, 232, 46, 10, 12, 30
    pw, ph = W - ml - mr, H - mt - mb
    top = max(max(cons), max(gen)) * 1.08
    step = pw / 12.0
    bw = step * 0.27

    def y(v):
        return mt + ph - (v / top) * ph

    out = []
    # grilla
    ticks = 5
    for i in range(ticks + 1):
        v = top / ticks * i
        yy = y(v)
        out.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml + pw}" y2="{yy:.1f}" stroke="#eeebe4" stroke-width="1"/>')
        out.append(f'<text x="{ml - 6}" y="{yy + 3:.1f}" text-anchor="end" class="ax">{num(v)}</text>')
    # barras
    pts = []
    for i in range(12):
        cx = ml + step * i + step / 2
        x1 = cx - bw
        x2 = cx + bw * 0.02
        h1 = ph - (y(cons[i]) - mt)
        h2 = ph - (y(gen[i]) - mt)
        out.append(f'<rect x="{x1:.1f}" y="{y(cons[i]):.1f}" width="{bw:.1f}" height="{h1:.1f}" rx="3" fill="#e8e3d8"/>')
        out.append(f'<rect x="{x2:.1f}" y="{y(gen[i]):.1f}" width="{bw:.1f}" height="{h2:.1f}" rx="3" fill="#d2a12a"/>')
        pts.append(f"{cx:.1f},{y(diur[i]):.1f}")
        out.append(f'<text x="{cx:.1f}" y="{mt + ph + 15}" text-anchor="middle" class="ax">{MESES[i]}</text>')
    # linea consumo diurno
    out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#5f5f5f" stroke-width="2" stroke-dasharray="5 3"/>')
    for p in pts:
        x, yy = p.split(",")
        out.append(f'<circle cx="{x}" cy="{yy}" r="2.6" fill="#5f5f5f"/>')
    out.append(f'<line x1="{ml}" y1="{mt + ph}" x2="{ml + pw}" y2="{mt + ph}" stroke="#ddd8ce" stroke-width="1"/>')
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">'
            f'<style>.ax{{font-family:Lato;font-size:11px;fill:#a3a3a3;}}</style>'
            + "".join(out) + "</svg>")


# ---------------- render ----------------
def render(cfg):
    d = calcular(cfg)
    sis = cfg["sistema"]

    # --- tabla de componentes
    items = ""
    for i, it in enumerate(cfg["items"], 1):
        items += (f'<tr><td class="c">{i}</td><td class="b">{it["item"]}</td>'
                  f'<td>{it["desc"]}</td><td class="r b">{it["cant"]}</td></tr>')
    ivas = ""
    for iv in cfg["iva"]:
        ivas += (f'<tr><td></td><td colspan="2" style="color:#8f8f8f">IVA ({num(iv["pct"], 1)}%)</td>'
                 f'<td class="r" style="color:#8f8f8f;white-space:nowrap">{usd(iv["monto"])}</td></tr>')

    # --- generacion mes a mes
    genrows = ""
    for i in range(12):
        cob = cfg["generacion_mensual"][i] / cfg["consumo_mensual"][i] * 100
        genrows += (f'<tr><td class="b">{MESES[i]}</td>'
                    f'<td class="r">{num(cfg["consumo_mensual"][i])}</td>'
                    f'<td class="r">{num(d["diurno"][i])}</td>'
                    f'<td class="r">{num(cfg["generacion_mensual"][i])}</td>'
                    f'<td class="r">{num(cob)} %</td></tr>')
    genrows += (f'<tr class="total"><td>Año</td><td class="r">{num(d["cons_anual"])}</td>'
                f'<td class="r">{num(sum(d["diurno"]))}</td><td class="r">{num(d["gen_anual"])}</td>'
                f'<td class="r">{num(d["cobertura"])} %</td></tr>')

    # --- recupero
    recrows = ""
    if cfg.get("mostrar_recupero", True):
        for f in d["recupero"]:
            cls = ' class="hl"' if f["hl"] else ""
            neto = ("+" if f["neto"] >= 0 else "−") + usd(abs(f["neto"])).replace("USD ", "")
            recrows += (f'<tr{cls}><td class="b">Año {f["anio"]}</td>'
                        f'<td class="r">{usd(f["ahorro"])}</td>'
                        f'<td class="r">{usd(f["acum"])}</td>'
                        f'<td class="r">{neto}</td></tr>')

    # --- financiacion
    finrows = ""
    for m in cfg["financiacion"]:
        finrows += (f'<tr><td class="b">{m["modalidad"]}</td><td>{m["adelanto"]}</td>'
                    f'<td class="r">{m["cuota"]}</td><td class="r b">{m["total"]}</td></tr>')

    incluye = "".join(f'<div class="blk"><p class="bt">{b["t"]}</p><p class="bd">{b["d"]}</p></div>'
                      for b in cfg["incluye"])
    cond = "".join(f'<div class="blk"><p class="bt">{b["t"]}</p><p class="bd">{b["d"]}</p></div>'
                   for b in cfg.get("condiciones", []))
    if cond:
        cond = '<p class="eyebrow">Condiciones de pago y alcance</p>' + cond + \
               '<p class="eyebrow" style="margin-top:12px">Resultados</p>'

    met = "".join(f'<li><b>{m["t"]}</b> {m["d"]}</li>' for m in cfg["metodologia"])
    notas = "".join(f"<li>{n}</li>" for n in cfg["notas_financiacion"])

    P = dict(cfg=cfg, d=d, sis=sis, LOGO=LOGO, items=items, ivas=ivas, genrows=genrows,
             recrows=recrows, finrows=finrows, incluye=incluye, cond=cond, met=met,
             notas=notas, svg=chart_svg(cfg, d))

    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Propuesta Oriens</title></head><body>
<div class="rh">{LOGO}</div>
<span class="cfoot">Propuesta para {cfg["cliente"]} · {cfg["ubicacion"]}</span>

<!-- ============ PAGINA 1: LECTURA DEL CONSUMO + PRESUPUESTO ============ -->
<div class="page">
  <p class="eyebrow">Propuesta integral</p>
  <h1>{cfg["titulo"]}</h1>
  <p class="sub">{cfg["subtitulo"]}</p>
  <hr>
  <p class="prep">Preparada para</p>
  <p class="prepline"><b>{cfg["cliente"]}</b> &nbsp;·&nbsp; {cfg["ubicacion"]} &nbsp;·&nbsp; {cfg["provincia"]} &nbsp;·&nbsp; {cfg["fecha"]}</p>

  <p class="eyebrow">Lectura del consumo</p>
  <h2>{cfg["h_consumo"]}</h2>
  <div class="lead">{cfg["perfil_html"]}{cfg["consumo_html"]}{cfg["objetivo_html"]}{cfg["recurso_html"]}</div>

  <p class="eyebrow" style="margin-top:12px">Presupuesto</p>
  <h2>{cfg["h_presupuesto"]}</h2>
  <div class="box">
    <p class="bx-eyebrow">{sis["etiqueta"]}</p>
    <h3>{sis["paneles"]} paneles · {num(d["kwp"], 2)} kWp</h3>
    <p class="h3s">{sis["inversor"]}</p>
    <table class="comp">
      <tr><th style="width:16px"></th><th>Item</th><th>Descripción</th><th class="r">Cant.</th></tr>
      {items}
      <tr class="total"><td></td><td colspan="2">Subtotal (sin IVA)</td><td class="r" style="white-space:nowrap">{usd(cfg["subtotal_usd"])}</td></tr>
      {ivas}
      <tr class="total2"><td></td><td colspan="2">Total</td><td class="r" style="white-space:nowrap">{usd(cfg["total_usd"])}</td></tr>
    </table>
  </div>
</div>

<!-- ============ PAGINA 2: QUE ES Y QUE INCLUYE ============ -->
<div class="page">
  <p class="eyebrow">La solución Oriens</p>
  <h1>{cfg["h_incluye"]}</h1>
  <p class="sub">{cfg["sub_incluye"]}</p>
  <hr>
  <p class="lead">{cfg["intro_incluye"]}</p>
  {incluye}
</div>

<!-- ============ PAGINA 3: CONDICIONES + RESULTADOS ============ -->
<div class="page">
  <p class="eyebrow">{cfg["eyebrow_resultados"]}</p>
  <h1>{cfg["h_condiciones"]}</h1>
  <p class="sub">{cfg["sub_condiciones"]}</p>
  <hr>
  {cond}
  <h2>{cfg["h_resultados"]}</h2>
  <p class="lead">{cfg["intro_resultados"]}</p>
  <div class="box">
    <table class="res">
      <tr><td>Configuración</td><td>{sis["paneles"]} paneles · {sis["inversor_corto"]}</td></tr>
      <tr><td>Potencia instalada</td><td>{num(d["kwp"], 2)} kWp</td></tr>
      <tr><td>Generación anual proyectada</td><td>{num(d["gen_anual"])} kWh</td></tr>
      <tr><td>Consumo anual del suministro</td><td>{num(d["cons_anual"])} kWh</td></tr>
      <tr><td>Cobertura del consumo anual</td><td>{num(d["cobertura"])} %</td></tr>
      <tr><td>Distribución autoconsumo / inyección</td><td>{num(d["frac_auto"])} % / {num(d["frac_iny"])} %</td></tr>
      <tr><td>Inversión (sin IVA)</td><td>{usd(d["inv_sin"])}</td></tr>
      <tr class="sub"><td></td><td>{ars(d["inv_sin_ars"])}</td></tr>
      <tr><td>Inversión total (con IVA)</td><td>{usd(d["inv_con"])}</td></tr>
      <tr class="sub"><td></td><td>{ars(d["inv_con_ars"])}</td></tr>
      <tr><td>Ahorro neto Año 1</td><td>{ars(d["ahorro_ars"])}</td></tr>
      <tr class="sub"><td></td><td>{usd(d["ahorro_usd"])} · {ars(d["ahorro_mes"])} por mes</td></tr>
      <tr><td>Reducción de la factura</td><td>{num(d["reduccion"])} %</td></tr>
      <tr class="big"><td>Repago estimado</td><td>{d["repago_txt"]}</td></tr>
    </table>
  </div>
  <div class="note">{cfg["nota_resultados"]}</div>
</div>

<!-- ============ PAGINA 4: GENERACION + METODOLOGIA ============ -->
<div class="page">
  <p class="eyebrow">Generación y metodología</p>
  <h1>{cfg["h_generacion"]}</h1>
  <hr>
  <p class="eyebrow">Generación proyectada</p>
  <p class="cap-s">{cfg["cap_grafico"]}</p>
  {P["svg"]}
  <div class="lgd">
    <span><i style="background:#e8e3d8"></i>Barra gris: consumo total</span>
    <span>{LEYENDA_LINEA}Línea punteada: consumo diurno ({num(cfg["frac_diurno"] * 100)} % del consumo del mes)</span>
    <span><i style="background:#d2a12a"></i>Barra dorada: generación solar</span>
  </div>
  <table class="mes" style="margin-top:7px">
    <tr><th>Mes</th><th class="r">Consumo</th><th class="r">Consumo diurno</th><th class="r">Generación</th><th class="r">Cobertura</th></tr>
    {genrows}
  </table>
  <p class="eyebrow" style="margin-top:10px">Metodología</p>
  <p class="cap-s">Cómo se calcula el recupero de inversión, en cinco pasos.</p>
  <ol class="met">{met}</ol>
</div>

<!-- ============ PAGINA 5: RECUPERO ============ -->
<div class="page">
  <p class="eyebrow">Recupero de la inversión</p>
  <h1>{cfg["h_recupero"]}</h1>
  <hr>
  <p class="lead">{cfg["intro_recupero"]}</p>
  <table>
    <tr><th>Período</th><th class="r">Ahorro del año</th><th class="r">Ahorro acumulado</th><th class="r">Resultado neto</th></tr>
    {recrows}
  </table>
  <div class="note">{cfg["nota_recupero"]}</div>

  <p class="eyebrow" style="margin-top:14px">Anexo · Financiación</p>
  <h2>{cfg["h_financiacion"]}</h2>
  <p class="cap-s">{cfg["cap_financiacion"]}</p>
  <table>
    <tr><th>Modalidad</th><th>Detalle</th><th class="r">Valor por cuota</th><th class="r">Total a abonar</th></tr>
    {finrows}
  </table>
  <ul class="notas">{notas}</ul>
</div>
</body></html>'''
    return html


def main():
    cfgpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "reference", "ejemplo_config_ongrid.json")
    out = sys.argv[2] if len(sys.argv) > 2 else "Propuesta_On_Grid.pdf"
    cfg = json.load(open(cfgpath, encoding="utf-8"))
    html = render(cfg)
    css = CSS(filename=os.path.join(HERE, "_style_ongrid.css"))
    HTML(string=html, base_url=HERE).write_pdf(out, stylesheets=[css])
    print("OK →", out)


if __name__ == "__main__":
    main()
