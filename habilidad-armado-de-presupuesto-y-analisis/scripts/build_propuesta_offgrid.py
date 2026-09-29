# -*- coding: utf-8 -*-
"""
Builder de la Propuesta Integral Off-Grid Oriens (PDF de 3 páginas, con 2-3 escenarios
comparados lado a lado: mismo arreglo solar, distinta batería).

Uso:
    python build_propuesta_offgrid.py config.json salida.pdf
Si no se pasan argumentos, usa el ejemplo (Ferrero) en reference/ejemplo_config_offgrid.json.

Este es un builder DISTINTO de build_propuesta.py: mismo estilo de marca (misma
_style.css, mismo logo), pero estructura de documento distinta — pensado para
proyectos OFF-GRID (sin inyección a red) donde se quiere mostrar 2 o 3 alternativas
de batería una al lado de la otra en la misma propuesta. Para proyectos con un solo
escenario (on-grid, híbrido con inyección, o off-grid de una sola alternativa) usá
build_propuesta.py en cambio. Ver SKILL.md → "Qué builder / ejemplo usar".

El config es un JSON con toda la data del proyecto. Ver reference/ejemplo_config_offgrid.json
y reference/metodologia_offgrid.md para el detalle de cada campo y las fórmulas.
"""
import sys, json, os
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

# Reusa los helpers de formato y el logo del builder principal para no duplicar código
# y para que ambos documentos usen exactamente el mismo estilo de marca.
sys.path.insert(0, HERE)
from build_propuesta import ar, usd, LOGO  # noqa: E402

CSS = open(os.path.join(HERE, "_style.css"), encoding="utf-8").read()


def compute(cfg):
    fac = cfg["factura"]
    sis = cfg["sistema_compartido"]
    meta = cfg["metodologia"]

    consumo_anual = fac["consumo_anual_kwh"]
    gen_anual = sis["generacion_anual_kwh"]
    costo_real = meta["costo_real_kwh"]
    tc = meta["tc"]
    tope = meta.get("tope_usd_kwh", 0.18)
    aumento = meta.get("aumento_anual", 0.10)
    degrad = meta.get("degradacion", 0.005)
    mant = meta.get("mantenimiento", 0.01)
    # Default 50/50 día/noche salvo que el config lo aclare distinto (política Oriens:
    # no asumir un split más favorable/desfavorable sin que el asesor lo confirme).
    dia_frac = meta.get("autoconsumo_dia_frac", 0.5)
    noche_frac = 1 - dia_frac
    reserva = meta.get("reserva_bateria_kwh", 4)
    usd_kwh_1 = costo_real / tc

    directo_anual = dia_frac * consumo_anual
    noche_anual = noche_frac * consumo_anual

    resultados = []
    for esc in cfg["escenarios"]:
        bat_kwh = esc["bateria_kwh"]
        ciclable_diario = max(bat_kwh - reserva, 0)
        ciclable_anual = ciclable_diario * 365
        autoc_noche = min(ciclable_anual, noche_anual)
        autoc_total = directo_anual + autoc_noche
        autoc_pct = autoc_total / consumo_anual * 100
        cobertura_noche_pct = (autoc_noche / noche_anual * 100) if noche_anual else 0.0

        inv = esc["inversion_usd"]
        iva = esc.get("iva", cfg.get("iva_default", 0.21))
        total_iva = inv * (1 + iva)

        acc = 0.0
        payback_year = None
        payback_months = None
        rec = []
        for y in range(1, 13):
            auto_y = autoc_total * ((1 - degrad) ** (y - 1))
            precio_y = min(usd_kwh_1 * ((1 + aumento) ** (y - 1)), tope)
            bruto = auto_y * precio_y
            neto = bruto - mant * inv
            prev = acc
            acc += neto
            rec.append((y, auto_y, precio_y, bruto, neto, acc))
            if payback_year is None and prev < inv <= acc:
                payback_year = y
                payback_months = (y - 1) + (inv - prev) / neto
        if payback_months is None:
            payback_txt = "más de 12 años"
        else:
            yrs = int(payback_months)
            mos = round((payback_months - yrs) * 12)
            if mos == 12:
                yrs += 1
                mos = 0
            payback_txt = f"{yrs} año{'s' if yrs != 1 else ''}" + (f" {mos} mes{'es' if mos != 1 else ''}" if mos else "")

        resultados.append(dict(esc,
            ciclable_diario=ciclable_diario, autoc_noche=autoc_noche, autoc_total=autoc_total,
            autoc_pct=autoc_pct, cobertura_noche_pct=cobertura_noche_pct,
            inv=inv, iva=iva, total_iva=total_iva, inv_ars=inv * tc,
            ahorro_neto_1=rec[0][4], ahorro_neto_1_ars=rec[0][4] * tc,
            payback_txt=payback_txt, rec=rec))

    return dict(consumo_anual=consumo_anual, gen_anual=gen_anual, costo_real=costo_real, tc=tc,
                dia_frac=dia_frac, noche_frac=noche_frac, reserva=reserva, degrad=degrad,
                aumento=aumento, mant=mant, tope=tope, directo_anual=directo_anual,
                noche_anual=noche_anual, resultados=resultados)


def img_src(p):
    if os.path.isabs(p) and os.path.exists(p):
        return p
    cand = os.path.join(ASSETS, p)
    return cand if os.path.exists(cand) else p


def build(cfg, out):
    d = compute(cfg)
    HTML(string=render(cfg, d), base_url=ASSETS + "/").write_pdf(out)
    return d


def render(cfg, d):
    fac = cfg["factura"]
    sis = cfg["sistema_compartido"]
    meta = cfg["metodologia"]
    n_esc = len(d["resultados"])
    cliente = cfg["cliente"]

    extra_css = f"""
@page {{
  @bottom-left {{ content:"ORIENS ENERGÍA SOLAR"; font-family:Lato; font-size:7.5px; color:#b3b3b3; letter-spacing:.4px; }}
  @bottom-right {{ content:"Propuesta integral para {cliente} · Pág. " counter(page) " / 3"; font-family:Lato; font-size:7.5px; color:#b3b3b3; }}
}}
.factbl td.k{{color:#8f8f8f;width:40%;}}
.factbl td.v{{font-weight:700;color:#242424;}}
.cols{{display:flex;gap:14px;align-items:stretch;}}
.cols>div{{flex:1;min-width:0;}}
.esc-card{{border:1px solid #ece9e2;border-radius:14px;padding:13px 15px;background:#fdfdfc;height:100%;}}
.esc-name{{font-family:Poppins;font-weight:700;font-size:11.5px;letter-spacing:1.2px;text-transform:uppercase;color:#c99320;margin-bottom:2px;}}
.esc-sub{{font-size:9px;color:#6b6b6b;margin-bottom:8px;}}
.esc-tot td{{font-family:Poppins;font-weight:700;color:#242424;border-top:2px solid #d6d2ca;border-bottom:none;padding-top:7px;}}
.cond-item{{margin-bottom:9px;}}
.cond-item b{{display:block;font-family:Poppins;font-size:9.3px;color:#242424;margin-bottom:2px;}}
.cond-item p{{margin:0;font-size:9px;color:#585858;}}
.mlist{{margin:4px 0 0 16px;padding:0;}}
.mlist li{{font-size:9.3px;color:#4b4b4b;margin-bottom:9px;line-height:1.55;}}
"""

    # ---------- Página 1: Lectura del consumo + Datos de la factura ----------
    texto_lectura = cfg.get("texto_lectura_consumo", f"""
      <p>El suministro está categorizado como <b>{fac.get('tarifa','')}</b>. En el período facturado
      ({fac.get('periodo','')}) se consumieron <b>{ar(fac['consumo_periodo_kwh'],0)} kWh</b>. Tomando los
      últimos 12 meses informados en la factura, el consumo promedio se ubica en <b>{ar(fac['consumo_prom_mensual_kwh'],0)}
      kWh por mes</b>, equivalente a <b>{ar(fac['consumo_anual_kwh'],0)} kWh anuales</b>. Esa es la base sobre la
      cual se dimensiona la propuesta solar.</p>
      <p>El cargo variable del período fue de <b>${ar(fac['valor_kwh_variable'],2)} / kWh</b>, al que se le suman
      los impuestos y contribuciones provinciales no recuperables que se terminan pagando como costo hundido.
      Computando ese efecto, el costo real de cada kWh consumido asciende a <b>${ar(fac['costo_real_kwh'],0)} / kWh</b>.
      Es el valor que la generación solar permite evitar por cada kWh autoconsumido.</p>""")

    fact_rows = [
        ("Titular del suministro", fac.get("titular", cliente)),
        ("Domicilio del suministro", fac.get("domicilio", cfg.get("ubicacion", ""))),
        ("Distribuidora", fac.get("distribuidora", "")),
        ("Tarifa / segmento", fac.get("tarifa", "")),
        ("Período facturado", fac.get("periodo", "")),
        ("Consumo del período", f"{ar(fac['consumo_periodo_kwh'],0)} kWh" + (f" · {ar(fac['consumo_periodo_kwh_dia'],1)} kWh / día" if fac.get('consumo_periodo_kwh_dia') else "")),
        ("Promedio mensual estimado", f"{ar(fac['consumo_prom_mensual_kwh'],0)} kWh / mes · ≈ {ar(fac['consumo_anual_kwh'],0)} kWh / año"),
        ("Valor del kWh (cargo variable)", f"${ar(fac['valor_kwh_variable'],2)} / kWh"),
        ("Costo fijo del período", f"${ar(fac.get('costo_fijo_periodo',0),0)}"),
        ("Total impuestos directos", f"${ar(fac.get('impuestos_directos',0),0)} · proporcionales al consumo · no recuperables"),
        ("Total impuestos indirectos", f"${ar(fac.get('impuestos_indirectos',0),0)} · IVA y fees fijos"),
        ("Costo real del kWh consumido", f"${ar(fac['costo_real_kwh'],0)} / kWh"),
        ("Total facturado del período", f"${ar(fac.get('total_facturado_periodo',0),0)}"),
    ]
    fact_html = "".join(f'<tr><td class="k">{k}</td><td class="v">{v}</td></tr>' for k, v in fact_rows)

    page1 = f"""<div class="page">
  <div class="prep">Proyecto de energía solar</div>
  <h1>{cfg.get('titulo','PROPUESTA INTEGRAL OFF-GRID')}</h1>
  <p class="sub">{cfg.get('subtitulo','Central solar fotovoltaica · Análisis del escenario actual')}</p>
  <hr>
  <div class="prep">Preparada para</div>
  <div class="prepline"><b>{cliente}</b> · {cfg.get('ubicacion','')} · {cfg.get('fecha','')}</div>
  <div class="eyebrow" style="margin-top:8px;">Lectura del consumo</div>
  <h2>Cómo se está consumiendo hoy</h2>
  {texto_lectura}
  <div class="eyebrow" style="margin-top:10px;">Datos de la factura</div>
  <h2>Tabulación del período</h2>
  <table class="factbl">{fact_html}</table>
</div>"""

    # ---------- Página 2: Presupuestos comparativos + Condiciones ----------
    esc_cards = []
    for r in d["resultados"]:
        comp_rows = "".join(f'<tr><td class="b">{it}</td><td>{desc}</td><td class="r">{cant}</td></tr>'
                             for (it, desc, cant) in r["componentes"])
        esc_cards.append(f"""<div><div class="esc-card">
      <div class="esc-name">{r['nombre']}</div>
      <div class="esc-sub">{r.get('resumen','')}</div>
      <table>
        <thead><tr><th>Ítem</th><th>Descripción</th><th class="r">Cant.</th></tr></thead>
        <tbody>{comp_rows}
        <tr><td class="b">Subtotal (sin IVA)</td><td colspan="2" class="r">{usd(r['inv'])}</td></tr>
        <tr><td class="b">IVA ({int(round(r['iva']*100))}%)</td><td colspan="2" class="r">{usd(r['inv']*r['iva'])}</td></tr>
        <tr class="esc-tot"><td>Total</td><td colspan="2" class="r">{usd(r['total_iva'])}</td></tr>
        </tbody>
      </table>
    </div></div>""")

    n_alt = "Dos" if n_esc == 2 else ("Tres" if n_esc == 3 else str(n_esc))
    intro_presup = cfg.get("intro_presupuestos", f"""Las alternativas son centrales solares <b>off-grid</b> — funcionan en paralelo a su
      suministro eléctrico actual, sin inyectar excedentes a la red. Comparten el mismo arreglo fotovoltaico
      ({sis['n_paneles']} paneles · {ar(sis.get('kwp', sis['n_paneles']*sis['panel_wp']/1000.0),1)} kWp) y el mismo inversor. La única diferencia
      entre las alternativas es la capacidad de batería instalada, lo cual define cuánto del consumo nocturno se
      puede cubrir con energía solar y cuántas horas de autonomía se tienen ante un corte de luz.""")

    cond = cfg.get("condiciones_offgrid", {})
    cond_items = [
        ("Modalidad de pago", cond.get("modalidad_pago",
            "50% de adelanto al firmar contrato y 50% como complemento luego de la instalación, sin interés. "
            "Alternativamente, financiación propia Oriens en cuotas en USD: 6 cuotas (40% de adelanto · TNA 5%), "
            "12 cuotas (30% de adelanto · TNA 10%) o 24 cuotas (20% de adelanto · TNA 14%).")),
        ("Qué incluye", cond.get("que_incluye",
            "Todas nuestras centrales son llave en mano: incluye asesoramiento, ingeniería, flete, instalación y "
            "puesta en marcha. Nada está subcontratado, somos 100% Oriens en toda la cadena. Antes del cierre se "
            "realiza un relevamiento técnico previo del sitio.")),
        ("Garantías", cond.get("garantias",
            "Garantía internacional de los productos: 5 años en inversor, 10 años en baterías y garantía estándar "
            "del fabricante en paneles, sumada a garantía propia de instalación.")),
        ("Plazo de instalación", cond.get("plazo", "15 a 20 días corridos contados desde el pago del anticipo.")),
        ("Configuración off-grid", cond.get("config_texto",
            "Esta configuración funciona en paralelo a su suministro eléctrico actual y no inyecta energía a la "
            "red. El sistema solar alimenta el autoconsumo de la casa (en forma directa durante el día y desde la "
            "batería el resto del tiempo) y, cuando hay un corte, sostiene el funcionamiento con la energía "
            "almacenada. Al no requerir alta como Usuario-Generador ante la distribuidora, no hay trámite "
            "adicional ni costo asociado a la habilitación.")),
        ("Cumplimiento normativo", cond.get("normativa",
            "Todas las instalaciones cumplen normas IRAM aplicables a instalaciones eléctricas residenciales y a "
            "sistemas solares autónomos.")),
    ]
    cond_html = "".join(f'<div class="cond-item"><b>{h}</b><p>{t}</p></div>' for h, t in cond_items)

    page2 = f"""<div class="page">
  <div class="eyebrow">Presupuestos</div>
  <h2>{n_alt} alternativas off-grid sobre el mismo arreglo solar</h2>
  <p>{intro_presup}</p>
  <div class="cols">{''.join(esc_cards)}</div>
  <div class="eyebrow" style="margin-top:14px;">Condiciones de pago y alcance</div>
  {cond_html}
</div>"""

    # ---------- Página 3: Comparativa + Metodología ----------
    def esc_col(r):
        return f"""<th class="r">{r['nombre'].replace('Sistema Off-Grid ','').replace('Sistema ','')}</th>"""

    kwp = sis.get("kwp", sis["n_paneles"] * sis["panel_wp"] / 1000.0)
    rows_cmp = [
        ("Configuración", lambda r: f"{sis['n_paneles']} paneles · Inversor {sis['inversor_kw']} kW"),
        ("Almacenamiento", lambda r: f"{ar(r['bateria_kwh'],2).rstrip('0').rstrip(',') } kWh" + (f" · {r['n_baterias']} batería(s)" if r.get('n_baterias') else "")),
        ("Capacidad de generación anual estimada", lambda r: f"{ar(d['gen_anual'],0)} kWh"),
        ("Autoconsumo estimado del consumo medido", lambda r: f"{ar(r['autoc_pct'],0)}%"),
        ("Inversión (sin IVA)", lambda r: usd(r['inv'])),
        ("Equivalente en pesos", lambda r: f"${ar(r['inv_ars'],0)}"),
        ("Ahorro neto Año 1", lambda r: usd(r['ahorro_neto_1'])),
        ("Equivalente en pesos", lambda r: f"${ar(r['ahorro_neto_1_ars'],0)}"),
        ("Repago estimado", lambda r: r['payback_txt']),
        ("Autonomía ante cortes de luz", lambda r: r.get('autonomia_hs', '—') if isinstance(r.get('autonomia_hs'), str) else f"~{r.get('autonomia_hs','—')} hs"),
    ]
    cmp_html = "".join(
        f'<tr><td class="b">{label}</td>' + "".join(f'<td class="r">{fn(r)}</td>' for r in d["resultados"]) + '</tr>'
        for label, fn in rows_cmp
    )
    cmp_head = "".join(f'<th class="r">{r["nombre"]}</th>' for r in d["resultados"])

    # Metodología, punto 3 con el detalle por escenario
    partes_autoc = " y ".join(
        f"{ar(r['ciclable_diario'],1)} kWh en la opción de {ar(r['bateria_kwh'],2).rstrip('0').rstrip(',')} kWh "
        f"(cubre el {ar(r['cobertura_noche_pct'],0)}% del consumo nocturno)"
        for r in d["resultados"]
    )
    resultado_autoc = " · ".join(
        f"{r['nombre'].split(' ')[-2] if 'kWh' in r['nombre'] else r['nombre']} {ar(r['autoc_total'],0)} kWh/año ({ar(r['autoc_pct'],0)}%)"
        for r in d["resultados"]
    )
    resultado_payback = " · ".join(f"{r['nombre']} {r['payback_txt']}" for r in d["resultados"])

    metodologia_html = f"""<ol class="mlist">
      <li><b>Cuánto genera el sistema.</b> Se estiman {ar(d['gen_anual'],0)} kWh / año (el arreglo solar es el
      mismo: {sis['n_paneles']} paneles · {ar(kwp,1)} kWp), considerando la ubicación específica, paneles orientados
      {meta.get('orientacion','al norte')} con {ar(meta.get('inclinacion_deg',15),0)}° de inclinación y un
      {ar(meta.get('perdidas_frac',0.10)*100,0)}% de pérdidas por suciedad, temperatura y conversión. Cada año la
      generación cae {ar(d['degrad']*100,1)}% por degradación natural de los paneles.</li>
      <li><b>Cuánto vale ese kWh.</b> El único kWh que tiene valor económico en este esquema es el autoconsumido:
      vale lo que cuesta hoy comprarlo a {fac.get('distribuidora','la distribuidora')}, ${ar(d['costo_real'],0)} / kWh
      (cargo variable + impuestos directos no recuperables). Al no haber inyección a la red, la generación que no se
      autoconsume ni se almacena queda como excedente perdido.</li>
      <li><b>Cuánto se autoconsume realmente.</b> El consumo medido es de {ar(d['consumo_anual']/365,1)} kWh / día, del
      cual aproximadamente un {ar(d['dia_frac']*100,0)}% ocurre en horas de sol (autoconsumo directo) y el
      {ar(d['noche_frac']*100,0)}% restante en horas sin sol (debe venir de la batería). Considerando una reserva fija
      de {ar(d['reserva'],0)} kWh siempre disponible en la batería para sostener cortes prolongados, la capacidad
      ciclable diaria es de {partes_autoc}. Sumando ambos componentes se llega a un autoconsumo total de: {resultado_autoc}.</li>
      <li><b>Cómo crece el ahorro en el tiempo.</b> La proyección considera un aumento anual de tarifa eléctrica +
      inflación en USD del {ar(d['aumento']*100,0)}% anual (escenario base). Cada año la luz cuesta más, por lo que
      cada kWh evitado vale más en pesos.</li>
      <li><b>Cuándo se recupera la inversión.</b> Se suma año a año el ahorro neto (ahorro bruto menos
      {ar(d['mant']*100,0)}% de mantenimiento anual sobre la inversión inicial). El año en que el acumulado iguala la
      inversión es el recupero. Resultado: {resultado_payback}. A partir de ahí el sistema sigue generando ahorro por
      más de 15 años (vida útil de paneles ~25 años).</li>
      <li><b>Por qué la inversión se computa sin IVA.</b> El kWh que se compra a la distribuidora incluye IVA y la
      inversión solar también lo incluye. Como ambos lados del cálculo llevan el mismo impuesto, se compensan entre
      sí y se trabaja sin IVA en los dos extremos para no distorsionar el resultado.</li>
    </ol>"""

    intro_cmp = cfg.get("intro_comparativa", f"""Todas son centrales solares off-grid (sin inyección a red) con la misma generación. Revisá la fila de
      autoconsumo y repago de cada alternativa para elegir el balance de inversión vs. cobertura que más te convenga.""")

    page3 = f"""<div class="page">
  <div class="eyebrow">Comparativa</div>
  <h2>Las {n_alt.lower() if n_esc in (2,3) else n_esc} opciones en un vistazo</h2>
  <p>{intro_cmp}</p>
  <table>
    <thead><tr><th></th>{cmp_head}</tr></thead>
    <tbody>{cmp_html}</tbody>
  </table>
  <div class="eyebrow" style="margin-top:16px;">Metodología</div>
  <h2>Cómo se calcula el recupero de inversión</h2>
  {metodologia_html}
</div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}{extra_css}</style></head><body>
<div class="rh">{LOGO}</div>
{page1}
{page2}
{page3}
</body></html>"""


if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "reference", "ejemplo_config_offgrid.json")
    out = sys.argv[2] if len(sys.argv) > 2 else "Propuesta Off-Grid Oriens.pdf"
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    d = build(cfg, out)
    resumen = " | ".join(f"{r['nombre']}: autoconsumo {ar(r['autoc_pct'],0)}% · repago {r['payback_txt']}" for r in d["resultados"])
    print(f"OK -> {out} | {resumen}")
