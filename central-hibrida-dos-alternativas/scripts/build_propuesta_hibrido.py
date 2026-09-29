# -*- coding: utf-8 -*-
"""
Builder de la Propuesta Integral HÍBRIDA de Oriens (PDF de 4 páginas, con 2-3
escenarios de batería comparados lado a lado sobre el mismo arreglo solar y el
mismo inversor híbrido, CON inyección del excedente a la red).

Uso:
    python build_propuesta_hibrido.py config.json salida.pdf

Diferencias con los otros dos builders de la skill:

  - build_propuesta.py          -> un solo escenario (industrial on-grid o
                                   residencial híbrido). No compara alternativas.
  - build_propuesta_offgrid.py  -> compara 2-3 baterías pero SIN inyección: el
                                   excedente que no entra en la batería se pierde.
  - build_propuesta_hibrido.py  -> compara 2-3 baterías CON inyección. El kWh tiene
                                   dos precios distintos (autoconsumido vs. inyectado)
                                   y el modelo es mensual, no anual.

El motor económico hace un balance MES A MES con arrastre de crédito, que es lo
que un modelo anual no puede capturar en un híbrido:

  1. Autoconsumo directo   = min(generación, consumo diurno del mes)
  2. Excedente             = generación - autoconsumo directo
  3. Descarga de batería   = min(excedente, consumo nocturno, capacidad ciclable)
  4. Inyección             = excedente - descarga de batería
  5. Compra a la red       = consumo - autoconsumo directo - descarga de batería

La factura de cada mes es cargo fijo + max(0, costo de lo comprado - crédito
acumulado por inyección). El crédito sobrante se arrastra al mes siguiente. Ese
arrastre es decisivo cuando el consumo es muy estacional: el crédito que se
genera en verano es el que paga el invierno.
"""
import sys, json, os
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

sys.path.insert(0, HERE)
from build_propuesta import ar, usd, LOGO  # noqa: E402

CSS = open(os.path.join(HERE, "_style.css"), encoding="utf-8").read()

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------
def balance_anual(gen, cons, dia_frac, bat_kwh, dod, efic, precio_auto,
                  precio_iny, cargo_fijo, mes_inicio=8, deg=1.0, esc=1.0):
    """Balance mes a mes con arrastre de crédito. Devuelve totales del año."""
    ciclable_dia = bat_kwh * dod * efic
    saldo = 0.0
    factura = 0.0
    T = dict(directo=0.0, bateria=0.0, inyectado=0.0, red=0.0, gen=0.0)
    detalle = []
    orden = [(mes_inicio + k) % 12 for k in range(12)]
    for i in orden:
        G = gen[i] * deg
        C = cons[i]
        Cd = C * dia_frac[i]
        Cn = C - Cd
        directo = min(G, Cd)
        excedente = max(0.0, G - Cd)
        descarga = min(excedente, Cn, ciclable_dia * DIAS[i])
        inyectado = excedente - descarga
        red = C - directo - descarga
        costo = red * precio_auto * esc
        credito = inyectado * precio_iny * esc + saldo
        pago = cargo_fijo * esc + max(0.0, costo - credito)
        saldo = max(0.0, credito - costo)
        factura += pago
        T["directo"] += directo
        T["bateria"] += descarga
        T["inyectado"] += inyectado
        T["red"] += red
        T["gen"] += G
        detalle.append(dict(mes=MESES[i], gen=G, cons=C, directo=directo,
                            bateria=descarga, inyectado=inyectado, red=red,
                            pago=pago, saldo=saldo))
    sin_solar = sum(cons) * precio_auto * esc + cargo_fijo * 12 * esc
    return dict(factura=factura, sin_solar=sin_solar, ahorro=sin_solar - factura,
                credito_muerto=saldo, detalle=detalle, **T)


def compute(cfg):
    sis = cfg["sistema_compartido"]
    meta = cfg["metodologia"]
    eco = cfg["economia"]

    cons = [cfg["consumo"]["mensual_kwh"][m] for m in MESES]
    gen = [cfg["generacion"]["mensual_kwh"][m] for m in MESES]

    dia_default = meta.get("autoconsumo_dia_frac", 0.5)
    dia_frac = [meta.get("autoconsumo_dia_frac_mensual", {}).get(m, dia_default)
                for m in MESES]

    dod = meta.get("bateria_dod", 0.90)
    efic = meta.get("bateria_eficiencia", 0.96)
    tc = eco["tc"]
    aumento = eco.get("aumento_anual", 0.10)
    degrad = eco.get("degradacion", 0.005)
    mant = eco.get("mantenimiento", 0.0)
    pa = eco["costo_real_kwh"]
    pi = eco["valor_inyeccion_kwh"]
    fijo = eco["cargo_fijo_mensual"]
    mes_inicio = meta.get("mes_inicio_idx", 8)

    # Años iniciales en los que el excedente todavía NO se remunera (típicamente
    # mientras se tramita el alta como Usuario-Generador ante la distribuidora).
    # Durante esos años el excedente se vuelca igual pero no genera crédito.
    sin_iny = eco.get("anios_sin_inyeccion", 0)

    resultados = []
    for esc_cfg in cfg["escenarios"]:
        bat = esc_cfg["bateria_kwh"]
        # Régimen pleno (con inyección remunerada), a precios de hoy
        b1 = balance_anual(gen, cons, dia_frac, bat, dod, efic, pa, pi, fijo, mes_inicio)
        # Año 1 tal como se va a facturar realmente
        b_a1 = (balance_anual(gen, cons, dia_frac, bat, dod, efic, pa, 0.0, fijo, mes_inicio)
                if sin_iny else b1)

        inv_sin = esc_cfg["inversion_usd"]
        iva_frac = esc_cfg.get("iva_frac", 0.21)
        inv_con = esc_cfg.get("inversion_usd_con_iva", inv_sin * (1 + iva_frac))
        # El IVA no se recupera (ver nota del config): se compara inversión con IVA
        # contra ahorro con IVA, ambos lados del mismo modo.
        base_inv = inv_con if eco.get("inversion_con_iva", True) else inv_sin
        inv_ars = base_inv * tc

        acum = 0.0
        payback = None
        serie = []
        for y in range(1, 16):
            pi_y = 0.0 if y <= sin_iny else pi
            by = balance_anual(gen, cons, dia_frac, bat, dod, efic, pa, pi_y, fijo,
                               mes_inicio, deg=(1 - degrad) ** (y - 1),
                               esc=(1 + aumento) ** (y - 1))
            neto = by["ahorro"] - mant * inv_ars
            prev = acum
            acum += neto
            serie.append((y, neto, acum))
            if payback is None and prev < inv_ars <= acum:
                payback = (y - 1) + (inv_ars - prev) / neto
        if payback is None:
            payback_txt = "más de 15 años"
        else:
            yy = int(payback)
            mm = round((payback - yy) * 12)
            if mm == 12:
                yy, mm = yy + 1, 0
            payback_txt = f"{yy} año{'s' if yy != 1 else ''}" + (f" {mm} mes{'es' if mm != 1 else ''}" if mm else "")

        autoc_total = b1["directo"] + b1["bateria"]
        resultados.append(dict(esc_cfg,
            bal=b1,
            autoc_total=autoc_total,
            autoc_pct=autoc_total / sum(cons) * 100,
            autoc_frac_gen=autoc_total / b1["gen"] * 100,
            iny_frac_gen=b1["inyectado"] / b1["gen"] * 100,
            red_pct=b1["red"] / sum(cons) * 100,
            inv_sin=inv_sin, inv_con=inv_con, inv_ars=inv_ars,
            bal_a1=b_a1,
            ahorro_ars=b1["ahorro"], ahorro_usd=b1["ahorro"] / tc,
            ahorro_pct=b1["ahorro"] / b1["sin_solar"] * 100,
            ahorro_a1_ars=b_a1["ahorro"], ahorro_a1_usd=b_a1["ahorro"] / tc,
            ahorro_a1_pct=b_a1["ahorro"] / b_a1["sin_solar"] * 100,
            factura_nueva=b1["factura"],
            payback_txt=payback_txt, serie=serie,
            respaldo_kwh=esc_cfg.get("respaldo_kwh_utiles", bat * dod),
            autonomia_hs=esc_cfg.get("respaldo_kwh_utiles", bat * dod) / meta.get("carga_respaldo_kw", 0.5)))

    return dict(cons=cons, gen=gen, dia_frac=dia_frac, tc=tc, pa=pa, pi=pi,
                fijo=fijo, cons_anual=sum(cons), gen_anual=sum(gen),
                cobertura=sum(gen) / sum(cons) * 100, aumento=aumento,
                sin_iny=sin_iny,
                degrad=degrad, dod=dod, efic=efic, resultados=resultados,
                sin_solar=resultados[0]["bal"]["sin_solar"])


# --------------------------------------------------------------------------
# Gráfico
# --------------------------------------------------------------------------
def chart_svg(d):
    W, H = 700, 245
    ml, mr, mt, mb = 46, 10, 26, 30
    pw, ph = W - ml - mr, H - mt - mb
    import math
    crudo = max(max(d["gen"]), max(d["cons"])) * 1.08
    paso_lindo = 250 if crudo <= 2000 else 500
    mx = math.ceil(crudo / (4 * paso_lindo)) * 4 * paso_lindo
    step = pw / 12.0
    bw = step * 0.30

    def yy(v):
        return mt + ph - (v / mx) * ph

    grid = ""
    n_lines = 4
    for k in range(n_lines + 1):
        v = mx / n_lines * k
        y = yy(v)
        grid += f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" stroke="#eeebe5" stroke-width="1"/>'
        grid += f'<text x="{ml-6}" y="{y+3:.1f}" text-anchor="end" class="ax">{ar(v,0)}</text>'

    bars = ""
    for i, m in enumerate(MESES):
        gx = ml + step * i
        x1 = gx + step / 2 - bw - 1.5
        x2 = gx + step / 2 + 1.5
        cv, gv = d["cons"][i], d["gen"][i]
        bars += (f'<rect x="{x1:.1f}" y="{yy(cv):.1f}" width="{bw:.1f}" '
                 f'height="{(mt+ph-yy(cv)):.1f}" rx="2.5" fill="#3a3a3a"/>')
        bars += (f'<rect x="{x2:.1f}" y="{yy(gv):.1f}" width="{bw:.1f}" '
                 f'height="{(mt+ph-yy(gv)):.1f}" rx="2.5" fill="#ebb236"/>')
        bars += f'<text x="{gx+step/2:.1f}" y="{H-9}" text-anchor="middle" class="mo">{m}</text>'

    legend = (f'<rect x="{ml}" y="6" width="9" height="9" rx="2" fill="#3a3a3a"/>'
              f'<text x="{ml+13}" y="14" class="lg">Consumo facturado</text>'
              f'<rect x="{ml+128}" y="6" width="9" height="9" rx="2" fill="#ebb236"/>'
              f'<text x="{ml+141}" y="14" class="lg">Generación solar estimada</text>')

    return f'''<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">
<style>.ax{{font-family:Lato;font-size:8px;fill:#a8a8a8;}}
.mo{{font-family:Lato;font-size:8.5px;fill:#8a8a8a;}}
.lg{{font-family:Lato;font-size:8.5px;fill:#6b6b6b;}}</style>
{grid}{bars}{legend}</svg>'''


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def tabla_mensual(d):
    R = d["resultados"]
    head = '<tr><th>Mes</th><th class="r">Consumo</th><th class="r">Generación</th>'
    for r in R:
        head += f'<th class="r" colspan="3">{r["nombre_corto"]}</th>'
    head += '</tr><tr><th></th><th></th><th></th>'
    for _ in R:
        head += '<th class="r">Autoc.</th><th class="r">Inyect.</th><th class="r">A la red</th>'
    head += '</tr>'
    body = ""
    for i, m in enumerate(MESES):
        body += f'<tr><td class="b">{m}</td><td class="r">{ar(d["cons"][i],0)}</td><td class="r">{ar(d["gen"][i],0)}</td>'
        for r in R:
            det = next(x for x in r["bal"]["detalle"] if x["mes"] == m)
            body += (f'<td class="r">{ar(det["directo"]+det["bateria"],0)}</td>'
                     f'<td class="r">{ar(det["inyectado"],0)}</td>'
                     f'<td class="r">{ar(det["red"],0)}</td>')
        body += '</tr>'
    body += f'<tr class="total"><td>Total</td><td class="r">{ar(d["cons_anual"],0)}</td><td class="r">{ar(d["gen_anual"],0)}</td>'
    for r in R:
        b = r["bal"]
        body += (f'<td class="r">{ar(b["directo"]+b["bateria"],0)}</td>'
                 f'<td class="r">{ar(b["inyectado"],0)}</td>'
                 f'<td class="r">{ar(b["red"],0)}</td>')
    body += '</tr>'
    return f'<table class="mens"><thead>{head}</thead><tbody>{body}</tbody></table>'


def render(cfg, d):
    sis = cfg["sistema_compartido"]
    meta = cfg["metodologia"]
    fac = cfg["factura"]
    cliente = cfg["cliente"]
    R = d["resultados"]
    n = len(R)
    n_pal = {2: "dos", 3: "tres"}.get(n, str(n))

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
.cond-item{{margin-bottom:9px;}}
.cond-item b{{display:block;font-family:Poppins;font-size:9.3px;color:#242424;margin-bottom:2px;}}
.cond-item p{{margin:0;font-size:9px;color:#585858;}}
.mlist{{margin:4px 0 0 16px;padding:0;}}
.mlist li{{font-size:9.4px;color:#4b4b4b;margin-bottom:9px;line-height:1.6;}}
.gold{{color:#c99320;font-weight:700;}}
.fin-h{{font-family:Poppins;font-weight:700;font-size:9.5px;letter-spacing:1.6px;text-transform:uppercase;color:#c99320;margin:14px 0 2px;}}
.notas li{{font-size:8.8px;color:#6b6b6b;margin-bottom:3px;}}
table.mens td{{font-size:8.3px;padding:3px 4px;}}
table.mens th{{font-size:6.6px;padding:3px 4px;letter-spacing:.5px;}}
table.mens tr.total td{{font-size:8.6px;padding-top:6px;}}
.pasos li{{font-size:9.2px;color:#4b4b4b;margin-bottom:5px;}}
"""

    # ---------------- Página 1 ----------------
    cards = []
    for r in R:
        rows = "".join(f'<tr><td class="b">{it}</td><td>{ds}</td><td class="r">{ct}</td></tr>'
                       for (it, ds, ct) in r["componentes"])
        cards.append(f"""<div><div class="esc-card">
      <div class="esc-name">{r['nombre']}</div>
      <div class="esc-sub">{r.get('resumen','')}</div>
      <table>
        <thead><tr><th>Ítem</th><th>Descripción</th><th class="r">Cant.</th></tr></thead>
        <tbody>{rows}
        <tr><td class="b">Subtotal (sin IVA)</td><td colspan="2" class="r">{usd(r['inv_sin'])}</td></tr>
        <tr><td class="b">IVA (21% + 10,5%)</td><td colspan="2" class="r">{usd(r['inv_con']-r['inv_sin'])}</td></tr>
        <tr class="esc-tot"><td>Total</td><td colspan="2" class="r">{usd(r['inv_con'])}</td></tr>
        </tbody>
      </table>
    </div></div>""")

    page1 = f"""<div class="page">
  <div class="prep">Propuesta integral</div>
  <h1>{cfg.get('titulo','Central solar híbrida')}</h1>
  <p class="sub">{cfg.get('subtitulo','Análisis del escenario actual y propuestas comparativas')}</p>
  <hr>
  <div class="prep">Preparada para</div>
  <div class="prepline"><b>{cliente}</b> · {cfg.get('ubicacion','')} · {cfg.get('fecha','')}</div>
  <div class="eyebrow" style="margin-top:8px;">Lectura del consumo</div>
  <h2>Cómo se está consumiendo hoy</h2>
  {cfg['texto_lectura_consumo']}
  <div class="eyebrow" style="margin-top:10px;">Presupuestos</div>
  <h2>Proponemos {n_pal} alternativas</h2>
  <p class="esc-sub" style="margin-bottom:9px;">{cfg['intro_presupuestos']}</p>
  <div class="cols">{''.join(cards)}</div>
</div>"""

    # ---------------- Página 2 ----------------
    # Bloque de condiciones: opcional. Si el config no trae "condiciones" (o viene
    # vacío), la página 2 arranca directamente con la comparativa.
    cond = cfg.get("condiciones", [])
    if cond:
        cond_html = (f'<div class="eyebrow">Condiciones y comparativa</div>'
                     f'<h2>Condiciones y las {n_pal} opciones</h2>'
                     f'<p class="sub" style="font-size:10.5px;margin-bottom:9px;">Modalidad de pago, alcance y comparativa de resultados</p>'
                     f'<div class="eyebrow" style="margin-top:4px;">Condiciones de pago y alcance</div>'
                     + "".join(f'<div class="cond-item"><b>{h}</b><p>{t}</p></div>' for h, t in cond)
                     + '<div class="eyebrow" style="margin-top:12px;">Comparativa</div>')
    else:
        cond_html = '<div class="eyebrow">Comparativa</div>'

    filas = [
        ("Configuración", lambda r: f"{sis['n_paneles']} paneles · Inversor híbrido {sis['inversor_kw']} kW"),
        ("Almacenamiento", lambda r: r["bateria_label"]),
        ("Generación anual estimada", lambda r: f"{ar(d['gen_anual'],0)} kWh"),
        ("Cobertura del consumo anual", lambda r: f"{ar(d['cobertura'],0)} %"),
        ("Autoconsumo / inyección", lambda r: f"{ar(r['autoc_frac_gen'],0)} % / {ar(r['iny_frac_gen'],0)} %"),
        ("Energía que sigue comprando a la red", lambda r: f"{ar(r['bal']['red'],0)} kWh / año"),
        ("Inversión (con IVA)", lambda r: usd(r["inv_con"])),
        ("Equivalente en pesos", lambda r: f"${ar(r['inv_ars'],0)}"),
        ("Ahorro Año 1 · sin inyección", lambda r: f"{usd(r['ahorro_a1_usd'])} · ${ar(r['ahorro_a1_ars'],0)}"),
        ("Ahorro anual desde el Año 2", lambda r: f"{usd(r['ahorro_usd'])} · ${ar(r['ahorro_ars'],0)}"),
        ("Reducción de la factura anual", lambda r: f"{ar(r['ahorro_a1_pct'],0)} % → {ar(r['ahorro_pct'],0)} %"),
        ("Repago estimado", lambda r: f'<span class="gold">{r["payback_txt"]}</span>'),
        # Siempre se declara la capacidad NOMINAL de la batería, no la útil.
        # Las horas salen de la energía realmente disponible sobre la carga de respaldo.
        # Siempre se declara la capacidad NOMINAL de la batería, no la útil. El dato que
        # se muestra ("bateria_kwh_nominal") se separa del que entra al modelo, para poder
        # redondearlo en el documento sin mover ni un kWh del balance energético.
        ("Respaldo ante cortes de luz", lambda r: f"{r.get('bateria_kwh_nominal') or ar(r['bateria_kwh'],1)} kWh · ~{ar(r['autonomia_hs'],0)} hs de autonomía"),
    ]
    cmp_rows = "".join(
        f'<tr><td class="b">{lab}</td>' + "".join(f'<td class="r">{fn(r)}</td>' for r in R) + "</tr>"
        for lab, fn in filas)
    cmp_head = "".join(f'<th class="r">{r["nombre_corto"]}</th>' for r in R)

    page2 = f"""<div class="page">
  {cond_html}
  <h2>Las {n_pal} opciones en un vistazo</h2>
  <p>{cfg['intro_comparativa']}</p>
  <table>
    <thead><tr><th></th>{cmp_head}</tr></thead>
    <tbody>{cmp_rows}</tbody>
  </table>
  <div class="note">{cfg['nota_comparativa']}</div>
  <div class="eyebrow" style="margin-top:14px;">Balance mensual</div>
  <h2>Adónde va cada kWh</h2>
  <p class="esc-sub">Reparto mes a mes de la energía generada en cada alternativa. "A la red" es lo que se sigue comprando a la cooperativa.</p>
  {tabla_mensual(d)}
</div>"""

    # ---------------- Página 3 ----------------
    page3 = f"""<div class="page">
  <div class="eyebrow">Generación y metodología</div>
  <h2>Generación esperada y cómo se calcula el repago</h2>
  <div class="eyebrow" style="margin-top:12px;">Generación proyectada</div>
  <p class="esc-sub">Generación solar mes a mes del arreglo —común a las {n_pal} alternativas— contrastada con el consumo de los últimos 12 meses leído de las facturas.</p>
  {chart_svg(d)}
  <div class="eyebrow" style="margin-top:12px;">Metodología</div>
  <h2>Cómo se calcula el recupero de inversión</h2>
  <p class="esc-sub">En cinco pasos.</p>
  {cfg['metodologia_html']}
</div>"""

    # ---------------- Página 4 ----------------
    # Cada fila de financiación es (modalidad, adelanto, cuota, total) y opcionalmente
    # una quinta posición con la TNA del plan. Si ninguna fila la trae, la columna no se dibuja.
    fin_blocks = []
    hay_tna = any(len(f) > 4 for r in R for f in r["financiacion"])
    for r in R:
        rows = ""
        for f in r["financiacion"]:
            mod, ade, cuo, tot = f[0], f[1], f[2], f[3]
            tna = f[4] if len(f) > 4 else "—"
            rows += (f'<tr><td class="b">{mod}</td><td>{ade}</td>'
                     + (f'<td class="r">{tna}</td>' if hay_tna else "")
                     + f'<td class="r">{cuo}</td><td class="r b">{tot}</td></tr>')
        fin_blocks.append(f"""<div class="fin-h">{r['nombre_corto']} · {usd(r['inv_con'])}</div>
    <table>
      <thead><tr><th>Modalidad</th><th>Adelanto</th>{'<th class="r">TNA</th>' if hay_tna else ''}<th class="r">Valor por cuota</th><th class="r">Total USD</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>""")

    notas = "".join(f"<li>{t}</li>" for t in cfg["notas_financiacion"])
    page4 = f"""<div class="page">
  <div class="eyebrow">Anexo · Financiación</div>
  <h2>Planes de pago disponibles</h2>
  <p class="esc-sub">Planes calculados para esta propuesta, en dólares oficiales (Banco Nación venta). El total incluye IVA.</p>
  {''.join(fin_blocks)}
  <div class="eyebrow" style="margin-top:16px;">Notas y condiciones</div>
  <ul class="notas">{notas}</ul>
  <div class="eyebrow" style="margin-top:18px;">Próximos pasos</div>
  <h2>Cómo avanzamos</h2>
  <ol class="pasos">{''.join(f"<li>{p}</li>" for p in cfg.get("proximos_pasos", []))}</ol>
</div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}{extra_css}</style></head><body>
<div class="rh">{LOGO}</div>
{page1}{page2}{page3}{page4}
</body></html>"""


def build(cfg, out):
    d = compute(cfg)
    HTML(string=render(cfg, d), base_url=ASSETS + "/").write_pdf(out)
    return d


if __name__ == "__main__":
    cfg_path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "Propuesta Hibrida Oriens.pdf"
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    d = build(cfg, out)
    for r in d["resultados"]:
        b = r["bal"]
        print(f"{r['nombre_corto']}: directo={b['directo']:.0f} bat={b['bateria']:.0f} "
              f"iny={b['inyectado']:.0f} red={b['red']:.0f} | ahorro ${b['ahorro']:,.0f} "
              f"({r['ahorro_pct']:.0f}%) | repago {r['payback_txt']} | credito muerto ${b['credito_muerto']:,.0f}")
    print(f"OK -> {out}")
