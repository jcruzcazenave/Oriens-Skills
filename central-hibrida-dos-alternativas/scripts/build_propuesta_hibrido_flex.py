# -*- coding: utf-8 -*-
"""
Builder FLEXIBLE de la propuesta híbrida comparativa de Oriens.

Cubre todo lo que cubre build_propuesta_hibrido.py y además:
  * Alternativas que difieren en PANELES y en baterías: cada escenario puede traer
    su propio "n_paneles", "kwp", "inversor_kw" y "generacion_mensual_kwh".
    Si no los trae, se usan "sistema_compartido" y "generacion.mensual_kwh".
  * Recupero opcional ("opciones.mostrar_recupero", default true).
    - true  -> modelo completo: año 1 sin inyección, crédito desde el año 2, repago.
    - false -> la inyección se muestra sólo como energía; la factura con el sistema y
               el ahorro se calculan SIN valorizar la inyección; no hay repago.
  * Filas de la comparativa configurables ("opciones.filas_comparativa").
  * Bloques opcionales: nota comparativa, condiciones, teléfono, ubicación.

Uso:
    python scripts/build_propuesta_hibrido_flex.py config.json "Propuesta Oriens - <Cliente>.pdf"
"""
import sys, os, json, math
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
sys.path.insert(0, HERE)
from build_propuesta import ar, usd, LOGO  # noqa: E402
from build_propuesta_hibrido import balance_anual, MESES, DIAS  # noqa: E402

CSS = open(os.path.join(HERE, "_style.css"), encoding="utf-8").read()


def kwp_txt(v):
    return ar(v, 2).rstrip("0").rstrip(",")


def payback_texto(pb):
    if pb is None:
        return "más de 15 años"
    yy = int(pb)
    mm = round((pb - yy) * 12)
    if mm == 12:
        yy, mm = yy + 1, 0
    return f"{yy} año{'s' if yy != 1 else ''}" + (f" {mm} mes{'es' if mm != 1 else ''}" if mm else "")


# --------------------------------------------------------------------------
# Cálculo
# --------------------------------------------------------------------------
def compute(cfg):
    op = cfg.get("opciones", {})
    recupero = op.get("mostrar_recupero", True)
    meta, eco = cfg["metodologia"], cfg["economia"]
    sis = cfg.get("sistema_compartido", {})
    gen_comun = cfg.get("generacion", {}).get("mensual_kwh")

    cons = [cfg["consumo"]["mensual_kwh"][m] for m in MESES]
    dia_def = meta.get("autoconsumo_dia_frac", 0.5)
    dia = [meta.get("autoconsumo_dia_frac_mensual", {}).get(m, dia_def) for m in MESES]
    dod, efic = meta.get("bateria_dod", 0.90), meta.get("bateria_eficiencia", 0.96)
    mes_ini = meta.get("mes_inicio_idx", 8)
    carga = meta.get("carga_respaldo_kw", 0.5)

    pa, fijo, tc = eco["costo_real_kwh"], eco["cargo_fijo_mensual"], eco["tc"]
    pi = eco.get("valor_inyeccion_kwh", 0.0) if recupero else 0.0
    sin_iny = eco.get("anios_sin_inyeccion", 1) if recupero else 0
    aumento, degrad = eco.get("aumento_anual", 0.10), eco.get("degradacion", 0.005)
    mant = eco.get("mantenimiento", 0.0)

    res = []
    for e in cfg["escenarios"]:
        g_cfg = e.get("generacion_mensual_kwh") or gen_comun
        gen = [g_cfg[m] for m in MESES]
        n_pan = e.get("n_paneles", sis.get("n_paneles"))
        kwp = e.get("kwp", sis.get("kwp"))
        inv_kw = e.get("inversor_kw", sis.get("inversor_kw"))
        bat = e["bateria_kwh"]

        b = balance_anual(gen, cons, dia, bat, dod, efic, pa, pi, fijo, mes_ini)
        b_a1 = balance_anual(gen, cons, dia, bat, dod, efic, pa, 0.0, fijo, mes_ini) if sin_iny else b

        inv_sin = e["inversion_usd"]
        inv_con = e.get("inversion_usd_con_iva", inv_sin * (1 + e.get("iva_frac", 0.21)))
        base_inv = inv_con if eco.get("inversion_con_iva", True) else inv_sin
        inv_ars = base_inv * tc

        pb_txt = None
        if recupero:
            acum, pb = 0.0, None
            for y in range(1, 16):
                by = balance_anual(gen, cons, dia, bat, dod, efic, pa, 0.0 if y <= sin_iny else pi,
                                   fijo, mes_ini, deg=(1 - degrad) ** (y - 1), esc=(1 + aumento) ** (y - 1))
                neto = by["ahorro"] - mant * inv_ars
                prev, acum = acum, acum + neto
                if pb is None and prev < inv_ars <= acum:
                    pb = (y - 1) + (inv_ars - prev) / neto
            pb_txt = payback_texto(pb)

        autoc = b["directo"] + b["bateria"]
        util = e.get("respaldo_kwh_utiles", bat * dod)
        res.append(dict(e, gen=gen, gen_anual=sum(gen), n_paneles=n_pan, kwp=kwp, inversor_kw=inv_kw,
                        bal=b, bal_a1=b_a1, autoc=autoc,
                        cobertura_gen=sum(gen) / sum(cons) * 100,
                        cubierto_pct=autoc / sum(cons) * 100,
                        autoc_frac_gen=autoc / sum(gen) * 100,
                        iny_frac_gen=b["inyectado"] / sum(gen) * 100,
                        inv_sin=inv_sin, inv_con=inv_con, inv_ars=inv_ars,
                        ahorro_ars=b["ahorro"], ahorro_usd=b["ahorro"] / tc,
                        ahorro_pct=b["ahorro"] / b["sin_solar"] * 100,
                        ahorro_a1_ars=b_a1["ahorro"], ahorro_a1_usd=b_a1["ahorro"] / tc,
                        ahorro_a1_pct=b_a1["ahorro"] / b_a1["sin_solar"] * 100,
                        fact_mes_hoy=b["sin_solar"] / 12, fact_mes_solar=b["factura"] / 12,
                        payback_txt=pb_txt, respaldo_kwh=util, autonomia_hs=util / carga))
    gen_iguales = all(r["gen"] == res[0]["gen"] for r in res)
    return dict(cons=cons, cons_anual=sum(cons), tc=tc, pa=pa, pi=pi, fijo=fijo, recupero=recupero,
                gen_iguales=gen_iguales, resultados=res)


def reserva_amanecer(cfg, r):
    """kWh que quedan en la batería al amanecer, mes a mes (régimen estable con promedios).
    Si el excedente diurno alcanza para cubrir la noche, el banco se llena cada tarde y amanece con
    (capacidad ciclable − consumo nocturno); si no alcanza, se vacía todas las noches (reserva 0).
    Sirve para describir el valor de una batería extra ante rachas nubladas: la diferencia entre
    alternativas es la capacidad ciclable adicional, y sólo existe en los meses que llenan."""
    meta = cfg["metodologia"]
    dod, efic = meta.get("bateria_dod", 0.90), meta.get("bateria_eficiencia", 0.96)
    dia_def = meta.get("autoconsumo_dia_frac", 0.5)
    U = r["bateria_kwh"] * dod * efic
    out = {}
    for i, m in enumerate(MESES):
        c = cfg["consumo"]["mensual_kwh"][m]
        f = meta.get("autoconsumo_dia_frac_mensual", {}).get(m, dia_def)
        exced, noche = (r["gen"][i] - c * f) / DIAS[i], c * (1 - f) / DIAS[i]
        out[m] = max(0.0, U - noche) if exced >= noche else 0.0
    return out


# --------------------------------------------------------------------------
# Filas de la comparativa (catálogo)
# --------------------------------------------------------------------------
FILAS = {
    "configuracion": ("Configuración", lambda r: f"{r['n_paneles']} paneles · {kwp_txt(r['kwp'])} kWp · Inversor híbrido {r['inversor_kw']} kW"),
    "almacenamiento": ("Almacenamiento", lambda r: r["bateria_label"]),
    "generacion_anual": ("Generación anual estimada", lambda r: f"{ar(r['gen_anual'],0)} kWh"),
    "generacion_vs_consumo": ("Generación / consumo anual", lambda r: f"{ar(r['cobertura_gen'],0)} %"),
    "consumo_cubierto": ("Consumo cubierto con energía solar", lambda r: f"{ar(r['cubierto_pct'],0)} %"),
    "autoconsumo_inyeccion": ("Autoconsumo / inyección", lambda r: f"{ar(r['autoc_frac_gen'],0)} % / {ar(r['iny_frac_gen'],0)} %"),
    "red_kwh": ("Energía que sigue comprando a la red", lambda r: f"{ar(r['bal']['red'],0)} kWh / año"),
    "inyeccion_kwh": ("Inyección potencial a la red", lambda r: f"{ar(r['bal']['inyectado'],0)} kWh / año"),
    "inversion_con_iva": ("Inversión (con IVA)", lambda r: usd(r["inv_con"])),
    "inversion_pesos": ("Equivalente en pesos", lambda r: f"${ar(r['inv_ars'],0)}"),
    "factura_actual": ("Factura promedio actual", lambda r: f"${ar(r['fact_mes_hoy'],0)} / mes"),
    "factura_con_sistema": ("Factura promedio con el sistema", lambda r: f"${ar(r['fact_mes_solar'],0)} / mes"),
    "factura_con_sistema_sin_iny": ("Factura promedio con el sistema sin inyección", lambda r: f"${ar(r['fact_mes_solar'],0)} / mes"),
    "ahorro_anual_factura": ("Ahorro anual en la factura", lambda r: f'<span class="gold">{usd(r["ahorro_usd"])}</span> · ${ar(r["ahorro_ars"],0)}'),
    "reduccion_factura": ("Reducción de la factura", lambda r: f"{ar(r['ahorro_pct'],0)} %"),
    "ahorro_a1": ("Ahorro Año 1 · sin inyección", lambda r: f"{usd(r['ahorro_a1_usd'])} · ${ar(r['ahorro_a1_ars'],0)}"),
    "ahorro_desde_a2": ("Ahorro anual desde el Año 2", lambda r: f"{usd(r['ahorro_usd'])} · ${ar(r['ahorro_ars'],0)}"),
    "reduccion_a1_a2": ("Reducción de la factura anual", lambda r: f"{ar(r['ahorro_a1_pct'],0)} % → {ar(r['ahorro_pct'],0)} %"),
    "repago": ("Repago estimado", lambda r: f'<span class="gold">{r["payback_txt"]}</span>'),
    # Siempre capacidad NOMINAL + horas de autonomía (la útil se configura aparte y no se imprime).
    "respaldo": ("Respaldo ante cortes de luz", lambda r: f"{r.get('bateria_kwh_nominal') or ar(r['bateria_kwh'],1)} kWh · ~{ar(r['autonomia_hs'],0)} hs de autonomía"),
}
FILAS_CON_RECUPERO = ["configuracion", "almacenamiento", "generacion_anual", "generacion_vs_consumo",
                      "autoconsumo_inyeccion", "red_kwh", "inversion_con_iva", "inversion_pesos",
                      "ahorro_a1", "ahorro_desde_a2", "reduccion_a1_a2", "repago", "respaldo"]
FILAS_SIN_RECUPERO = ["configuracion", "almacenamiento", "generacion_anual", "generacion_vs_consumo",
                      "consumo_cubierto", "red_kwh", "inyeccion_kwh", "factura_actual",
                      "factura_con_sistema_sin_iny", "respaldo"]


# --------------------------------------------------------------------------
# Gráfico y tabla mensual
# --------------------------------------------------------------------------
def chart_svg(d):
    W, H = 700, 245
    ml, mr, mt, mb = 46, 10, 26, 30
    pw, ph = W - ml - mr, H - mt - mb
    R = d["resultados"]
    series = [("Consumo facturado", d["cons"])]
    if d["gen_iguales"]:
        series.append(("Generación solar", R[0]["gen"]))
    else:
        series += [(f"Generación {r['nombre_corto']}", r["gen"]) for r in R]
    crudo = max(max(v) for _, v in series) * 1.08
    paso = 250 if crudo <= 1500 else 500
    nlin = math.ceil(crudo / paso)
    mx = nlin * paso
    step = pw / 12.0
    nb = len(series)
    bw = step * (0.72 / nb)
    yy = lambda v: mt + ph - (v / mx) * ph
    grid = "".join(f'<line x1="{ml}" y1="{yy(paso*k):.1f}" x2="{W-mr}" y2="{yy(paso*k):.1f}" stroke="#eeebe5"/>'
                   f'<text x="{ml-6}" y="{yy(paso*k)+3:.1f}" text-anchor="end" class="ax">{ar(paso*k,0)}</text>'
                   for k in range(nlin + 1))
    colores = ["#3a3a3a", "#f2c96b", "#c99320", "#8a6a16"]
    bars = ""
    for i, m in enumerate(MESES):
        x0 = ml + step * i + step / 2 - (nb * bw + (nb - 1) * 2) / 2
        for j, (_, v) in enumerate(series):
            x = x0 + j * (bw + 2)
            bars += f'<rect x="{x:.1f}" y="{yy(v[i]):.1f}" width="{bw:.1f}" height="{mt+ph-yy(v[i]):.1f}" rx="2" fill="{colores[j]}"/>'
        bars += f'<text x="{ml+step*i+step/2:.1f}" y="{H-9}" text-anchor="middle" class="mo">{m}</text>'
    legend, x = "", ml
    for j, (lab, _) in enumerate(series):
        legend += (f'<rect x="{x}" y="6" width="9" height="9" rx="2" fill="{colores[j]}"/>'
                   f'<text x="{x+13}" y="14" class="lg">{lab}</text>')
        x += 13 + len(lab) * 4.3 + 18
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">
<style>.ax{{font-family:Lato;font-size:8px;fill:#a8a8a8;}}.mo{{font-family:Lato;font-size:8.5px;fill:#8a8a8a;}}
.lg{{font-family:Lato;font-size:8.5px;fill:#6b6b6b;}}</style>{grid}{bars}{legend}</svg>'''


def tabla_mensual(d):
    R = d["resultados"]
    cols = [("directo", "Directo"), ("bateria", "Batería"), ("inyectado", "Inyecc."), ("red", "Red")]
    if not d["gen_iguales"]:
        cols = [("gen", "Gener.")] + cols
    fijas = [("Mes", None), ("Consumo", "cons")] + ([("Gener.", "gen0")] if d["gen_iguales"] else [])
    h1 = "<tr>" + "<th></th>" * len(fijas) + "".join(
        f'<th class="r grp" colspan="{len(cols)}">{r["nombre_corto"]}</th>' for r in R) + "</tr>"
    h2 = "<tr><th>Mes</th>" + "".join(f'<th class="r">{t}</th>' for t, _ in fijas[1:]) + "".join(
        f'<th class="r{" sep" if k == 0 else ""}">{lab}</th>' for _ in R for k, (_, lab) in enumerate(cols)) + "</tr>"
    body = ""
    for i, m in enumerate(MESES):
        body += f'<tr><td class="b">{m}</td><td class="r">{ar(d["cons"][i],0)}</td>'
        if d["gen_iguales"]:
            body += f'<td class="r">{ar(R[0]["gen"][i],0)}</td>'
        for r in R:
            x = next(t for t in r["bal"]["detalle"] if t["mes"] == m)
            body += "".join(f'<td class="r{" sep" if k == 0 else ""}">{ar(x[c],0)}</td>' for k, (c, _) in enumerate(cols))
        body += "</tr>"
    body += f'<tr class="total"><td>Total</td><td class="r">{ar(d["cons_anual"],0)}</td>'
    if d["gen_iguales"]:
        body += f'<td class="r">{ar(R[0]["gen_anual"],0)}</td>'
    for r in R:
        body += "".join(f'<td class="r{" sep" if k == 0 else ""}">{ar(r["bal"][c],0)}</td>' for k, (c, _) in enumerate(cols))
    body += "</tr>"
    return f'<table class="mens"><thead>{h1}{h2}</thead><tbody>{body}</tbody></table>'


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def render(cfg, d):
    op = cfg.get("opciones", {})
    R = d["resultados"]
    cliente = cfg["cliente"]
    n_pal = {2: "dos", 3: "tres"}.get(len(R), str(len(R)))
    extra_css = f"""
@page {{
  @bottom-left {{ content:"ORIENS ENERGÍA SOLAR"; font-family:Lato; font-size:7.5px; color:#b3b3b3; letter-spacing:.4px; }}
  @bottom-right {{ content:"Propuesta integral para {cliente} · " counter(page) " / 4"; font-family:Lato; font-size:7.5px; color:#b3b3b3; }}
}}
.cols{{display:flex;gap:14px;align-items:stretch;}}
.cols>div{{flex:1;min-width:0;}}
.esc-card{{border:1px solid #ece9e2;border-radius:14px;padding:13px 15px;background:#fdfdfc;height:100%;}}
.esc-name{{font-family:Poppins;font-weight:700;font-size:10.5px;letter-spacing:1.2px;text-transform:uppercase;color:#c99320;margin-bottom:2px;}}
.esc-sub{{font-size:9px;color:#6b6b6b;margin-bottom:8px;font-style:italic;}}
.esc-tot td{{font-family:Poppins;font-weight:700;color:#242424;border-top:2px solid #d6d2ca;border-bottom:none;padding-top:7px;font-size:11px;}}
.esc-card td{{font-size:8.8px;padding:4px 5px;}}
.esc-card th{{font-size:7px;padding:4px 5px;}}
.mlist{{margin:4px 0 0 16px;padding:0;}}
.mlist li{{font-size:9.3px;color:#4b4b4b;margin-bottom:8px;line-height:1.6;}}
.gold{{color:#c99320;font-weight:700;}}
.fin-h{{font-family:Poppins;font-weight:700;font-size:9.5px;letter-spacing:1.6px;text-transform:uppercase;color:#c99320;margin:14px 0 2px;}}
.notas li{{font-size:8.8px;color:#6b6b6b;margin-bottom:3px;}}
.cond-item{{margin-bottom:6px;}} .cond-item b{{font-size:9.5px;}} .cond-item p{{font-size:9px;margin:1px 0 0;}}
table.cmp td{{font-size:8.8px;padding:4px 6px;}}
table.mens td{{font-size:7.9px;padding:2.6px 3px;}}
table.mens th{{font-size:6.4px;padding:3px 3px;letter-spacing:.4px;}}
table.mens th.grp{{text-align:center;color:#c99320;border-bottom:1px solid #ebb236;}}
table.mens .sep{{border-left:1px solid #ece9e2;}}
table.mens tr.total td{{font-size:8.2px;padding-top:6px;}}
.pasos li{{font-size:9.2px;color:#4b4b4b;margin-bottom:5px;}}
.contacto{{margin-top:22px;padding:12px 16px;border:1px solid #ece9e2;border-radius:12px;background:#fdfdfc;}}
.contacto b{{font-family:Poppins;font-size:10px;color:#242424;}}
.contacto span{{font-family:Poppins;font-weight:700;font-size:13px;color:#c99320;margin-left:8px;}}
"""
    # ---------- Página 1 ----------
    cards = []
    for r in R:
        rows = "".join(f'<tr><td class="b">{it}</td><td>{ds}</td><td class="r">{ct}</td></tr>' for it, ds, ct in r["componentes"])
        cards.append(f"""<div><div class="esc-card">
      <div class="esc-name">{r['nombre']}</div><div class="esc-sub">{r['resumen']}</div>
      <table><thead><tr><th>Ítem</th><th>Descripción</th><th class="r">Cant.</th></tr></thead>
        <tbody>{rows}
        <tr><td class="b">Subtotal (sin IVA)</td><td colspan="2" class="r">{usd(r['inv_sin'])}</td></tr>
        <tr><td class="b">IVA (21% + 10,5%)</td><td colspan="2" class="r">{usd(r['inv_con']-r['inv_sin'])}</td></tr>
        <tr class="esc-tot"><td>Total</td><td colspan="2" class="r">{usd(r['inv_con'])}</td></tr>
        </tbody></table></div></div>""")
    prep = " · ".join(x for x in [f"<b>{cliente}</b>", cfg.get("ubicacion", ""), cfg.get("fecha", "")] if x)
    page1 = f"""<div class="page">
  <div class="prep">Propuesta integral</div>
  <h1>{cfg.get('titulo', 'Central solar híbrida')}</h1>
  <p class="sub">{cfg.get('subtitulo', 'Análisis del escenario actual y propuestas comparativas')}</p><hr>
  <div class="prep">Preparada para</div><div class="prepline">{prep}</div>
  <div class="eyebrow" style="margin-top:8px;">Lectura del consumo</div>
  <h2>Cómo se está consumiendo hoy</h2>{cfg['texto_lectura_consumo']}
  <div class="eyebrow" style="margin-top:10px;">Presupuestos</div>
  <h2>Proponemos {n_pal} alternativas</h2>
  <p class="esc-sub" style="margin-bottom:9px;">{cfg['intro_presupuestos']}</p>
  <div class="cols">{''.join(cards)}</div>
</div>"""
    # ---------- Página 2 ----------
    claves = op.get("filas_comparativa") or (FILAS_CON_RECUPERO if d["recupero"] else FILAS_SIN_RECUPERO)
    faltan = [k for k in claves if k not in FILAS]
    if faltan:
        raise SystemExit(f"Filas desconocidas en opciones.filas_comparativa: {faltan}. Válidas: {list(FILAS)}")
    if not d["recupero"] and any(k in ("repago", "ahorro_a1", "ahorro_desde_a2", "reduccion_a1_a2") for k in claves):
        raise SystemExit("Hay filas de recupero en la comparativa pero opciones.mostrar_recupero es false.")
    cmp_rows = "".join(f'<tr><td class="b">{FILAS[k][0]}</td>' + "".join(f'<td class="r">{FILAS[k][1](r)}</td>' for r in R) + "</tr>"
                       for k in claves)
    cmp_head = "".join(f'<th class="r">{r["nombre_corto"]}</th>' for r in R)
    cond = cfg.get("condiciones", [])
    cond_html = ""
    if cond:
        cond_html = ('<div class="eyebrow">Condiciones de pago y alcance</div>'
                     + "".join(f'<div class="cond-item"><b>{h}</b><p>{t}</p></div>' for h, t in cond))
    nota = cfg.get("nota_comparativa")
    nota_html = f'<div class="note">{nota}</div>' if nota else ""
    intro_bal = cfg.get("intro_balance",
                        "Reparto mes a mes de la energía generada en cada alternativa, en kWh. «Directo» es lo que la casa "
                        "consume de día en el momento en que se genera; «Batería», lo que se guarda para usar de noche; "
                        "«Inyecc.», el excedente que se vuelca a la red; «Red», lo que se sigue comprando a la distribuidora.")
    page2 = f"""<div class="page">
  {cond_html}
  <div class="eyebrow"{' style="margin-top:12px;"' if cond else ''}>Comparativa</div>
  <h2>Las {n_pal} opciones en un vistazo</h2>
  <p>{cfg['intro_comparativa']}</p>
  <table class="cmp"><thead><tr><th></th>{cmp_head}</tr></thead><tbody>{cmp_rows}</tbody></table>
  {nota_html}
  <div class="eyebrow" style="margin-top:12px;">Balance mensual</div>
  <h2>Adónde va cada kWh</h2>
  <p class="esc-sub">{intro_bal}</p>
  {tabla_mensual(d)}
</div>"""
    # ---------- Página 3 ----------
    if d["gen_iguales"]:
        sub_gen = f"Generación solar mes a mes del arreglo —común a las {n_pal} alternativas— contrastada con el consumo de los últimos 12 meses leído de las facturas."
    else:
        sub_gen = "Generación solar mes a mes de cada alternativa, contrastada con el consumo de los últimos 12 meses leído de las facturas."
    titulo_met = cfg.get("metodologia_titulo") or ("Cómo se calcula el recupero de inversión" if d["recupero"]
                                                   else "Cómo se calcula el reparto de la energía y la factura")
    page3 = f"""<div class="page">
  <div class="eyebrow">Generación y metodología</div>
  <h2>Generación esperada y cómo se reparte la energía</h2>
  <div class="eyebrow" style="margin-top:12px;">Generación proyectada</div>
  <p class="esc-sub">{sub_gen}</p>
  {chart_svg(d)}
  <div class="eyebrow" style="margin-top:12px;">Metodología</div>
  <h2>{titulo_met}</h2>
  <p class="esc-sub">{cfg.get('metodologia_sub', 'En cinco pasos.')}</p>
  {cfg['metodologia_html']}
</div>"""
    # ---------- Página 4 ----------
    fin = []
    for r in R:
        rows = "".join(f'<tr><td class="b">{f[0]}</td><td>{f[1]}</td><td class="r">{f[4]}</td>'
                       f'<td class="r">{f[2]}</td><td class="r b">{f[3]}</td></tr>' for f in r["financiacion"])
        fin.append(f"""<div class="fin-h">{r['nombre_corto']} · {usd(r['inv_con'])}</div>
    <table><thead><tr><th>Modalidad</th><th>Adelanto</th><th class="r">TNA</th><th class="r">Valor por cuota</th><th class="r">Total USD</th></tr></thead>
    <tbody>{rows}</tbody></table>""")
    pasos = cfg.get("proximos_pasos", [])
    pasos_html = (f'<div class="eyebrow" style="margin-top:18px;">Próximos pasos</div><h2>Cómo avanzamos</h2>'
                  f'<ol class="pasos">{"".join(f"<li>{p}</li>" for p in pasos)}</ol>') if pasos else ""
    tel = cfg.get("telefono")
    tel_html = f'<div class="contacto"><b>Consultas</b><span>{tel}</span></div>' if tel else ""
    page4 = f"""<div class="page">
  <div class="eyebrow">Anexo · Financiación</div>
  <h2>Planes de pago disponibles</h2>
  <p class="esc-sub">Planes calculados para esta propuesta, en dólares oficiales (Banco Nación venta). El total incluye IVA.</p>
  {''.join(fin)}
  <div class="eyebrow" style="margin-top:16px;">Notas y condiciones</div>
  <ul class="notas">{''.join(f"<li>{t}</li>" for t in cfg['notas_financiacion'])}</ul>
  {pasos_html}
  {tel_html}
</div>"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}{extra_css}</style></head><body>
<div class="rh">{LOGO}</div>{page1}{page2}{page3}{page4}</body></html>"""


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    d = compute(cfg)
    HTML(string=render(cfg, d), base_url=ASSETS + "/").write_pdf(sys.argv[2])
    for r in d["resultados"]:
        b = r["bal"]
        linea = (f"{r['nombre_corto']}: gen={r['gen_anual']:.0f} directo={b['directo']:.0f} bat={b['bateria']:.0f} "
                 f"iny={b['inyectado']:.0f} red={b['red']:.0f} cubierto={r['cubierto_pct']:.1f}% | "
                 f"factura ${r['fact_mes_hoy']:,.0f}/mes -> ${r['fact_mes_solar']:,.0f}/mes | ahorro USD {r['ahorro_usd']:,.0f}")
        if d["recupero"]:
            linea += f" (año 1 USD {r['ahorro_a1_usd']:,.0f}) | repago {r['payback_txt']} | crédito sin usar ${b['credito_muerto']:,.0f}"
        print(linea + f" | autonomía {r['autonomia_hs']:.1f} hs")
    print("OK ->", sys.argv[2])
