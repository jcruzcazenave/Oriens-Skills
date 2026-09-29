# -*- coding: utf-8 -*-
"""
Builder de la Propuesta Industrial Oriens (PDF de 5 páginas).
Uso:
    python build_propuesta.py config.json salida.pdf
Si no se pasan argumentos, usa el ejemplo (JG Envases) en reference/ejemplo_config.json.

El config es un JSON con toda la data del proyecto. Ver reference/ejemplo_config.json
y reference/metodologia.md para el detalle de cada campo y los supuestos económicos.
"""
import sys, json, os
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

def ar(n, dec=0):
    return f"{n:,.{dec}f}".replace(",", "·").replace(".", ",").replace("·", ".")
def usd(n):
    return "USD " + ar(n, 0)

MES_ORDER = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
MES_NOM = {"Ene":"Enero","Feb":"Febrero","Mar":"Marzo","Abr":"Abril","May":"Mayo","Jun":"Junio",
           "Jul":"Julio","Ago":"Agosto","Sep":"Septiembre","Oct":"Octubre","Nov":"Noviembre","Dic":"Diciembre"}

# ---------- CATÁLOGO DE EQUIPOS (presets reutilizables) ----------
# Una ficha del config puede ser un dict completo o un preset {"preset": "...", ...}.
# Los presets garantizan que un mismo equipo use SIEMPRE la misma imagen y descripción.
def _mil(n):
    return f"{int(n):,}".replace(",", ".")

def catalogo_ficha(spec):
    """Resuelve una ficha: si trae 'preset', la expande desde el catálogo."""
    if "preset" not in spec:
        return spec
    p = spec["preset"]

    if p == "panel_jinko":
        # Paneles Jinko Tiger Neo bifacial N-type. Misma imagen y descripción;
        # sólo cambia la potencia (Wp) si se indica.
        wp = spec.get("wp", 620)
        return {"img": "img_panel.png", "name": "Panel solar",
                "sub": f"Jinko Tiger Neo {wp} Wp · bifacial N-type",
                "specs": [["Tecnología", "N-type monocristalina TOPCon"],
                          ["Potencia (Pmax)", f"{wp} Wp · hasta ~{round(wp*1.105)} Wp bifacial"],
                          ["Eficiencia", "≈ 22,5 %"],
                          ["Dimensiones / peso", "2.382 × 1.134 × 30 mm · ~32 kg"],
                          ["Garantía", "12 años producto · 30 años lineal"]]}

    if p == "panel_amerisolar":
        # Panel Amerisolar Mono PERC 144 celdas, All Black. Usado en proyectos off-grid
        # residenciales (ej. Ferrero). Misma imagen y descripción; sólo cambia la potencia.
        wp = spec.get("wp", 550)
        return {"img": "img_panel_amerisolar.png", "name": "Panel solar",
                "sub": f"Amerisolar Mono PERC {wp} Wp · 144 celdas · All Black",
                "specs": [["Tecnología", "Mono PERC · 144 celdas · All Black"],
                          ["Potencia (Pmax)", f"{wp} Wp"],
                          ["Eficiencia", "≈ 21 %"],
                          ["Garantía", "Garantía estándar del fabricante"]]}

    if p == "inversor_growatt":
        # Growatt MAX On Grid trifásico. Misma imagen y descripción; sólo cambia la
        # potencia. Potencias soportadas del catálogo: 50, 80, 100, 125 kW.
        kw = spec["kw"]
        modelo = spec.get("modelo", f"MAX {kw}KTL3-LV")
        va = _mil(kw * 1110)          # VA aparente ≈ kW × 1,11 (ratio de placa)
        dc = round(kw * 1.5)          # FV máx recomendada ≈ kW × 1,5
        return {"img": "img_inversor.png", "name": "Inversor",
                "sub": f"Growatt {modelo} · On Grid trifásico",
                "specs": [["Potencia AC / FV máx.", f"{kw} kW ({va} VA) · {dc} kW DC"],
                          ["Eficiencia", "99 % máx. · 98,5 % europea"],
                          ["MPPT", "7 seguidores · fuse-free · monitoreo por string"],
                          ["Protección", "IP65 · SPD Tipo II AC/DC · AFCI opcional"],
                          ["Garantía", "5 años · extensible a 10"]]}

    if p == "inversor_growatt_chico":
        # Growatt On Grid mono/trifásico hasta 10 kW (residencial chico).
        kw = spec.get("kw", 10)
        return {"img": "img_inversor_growatt_10.png", "name": "Inversor",
                "sub": f"Growatt On Grid mono/trifásico · hasta {kw} kW",
                "specs": [["Potencia AC máx.", f"{kw} kW"],
                          ["Tipo", "On Grid monofásico o trifásico"],
                          ["Monitoreo", "WiFi / app Growatt"],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "inversor_deye_hibrido":
        # Deye híbrido (con batería), monofásico o trifásico, hasta 20 kW inclusive.
        kw = spec.get("kw", 15)
        modelo = spec.get("modelo", f"SUN-{kw}K-SG05LP3-EU-SM2")
        return {"img": "img_inversor_deye.png", "name": "Inversor",
                "sub": f"Deye {modelo} · Híbrido mono/trifásico",
                "specs": [["Potencia AC", f"{kw} kW"],
                          ["Modo de operación", "Híbrido (con batería) y On-Grid"],
                          ["Compatibilidad batería", "Baterías Deye de baja tensión (48V)"],
                          ["Monitoreo", "WiFi / app Deye"],
                          ["Garantía", "5 años"]],
                "rango": "hasta 20 kW inclusive (mono/trifásico)"}

    if p == "inversor_deye_hibrido_grande":
        # Deye híbrido trifásico de mayor potencia: 50 a 125 kW.
        kw = spec.get("kw", 50)
        return {"img": "img_inversor_deye_50_125.png", "name": "Inversor",
                "sub": f"Deye híbrido trifásico · {kw} kW",
                "specs": [["Potencia AC", f"{kw} kW · trifásico"],
                          ["Modo de operación", "Híbrido (con batería) y On-Grid"],
                          ["Rango de la serie", "50 a 125 kW"],
                          ["Garantía", "5 años"]]}

    if p == "inversor_deye_offgrid":
        # Deye off-grid monofásico (sin conexión a red), típicamente 6 kW.
        kw = spec.get("kw", 6)
        return {"img": "img_inversor_deye.png", "name": "Inversor",
                "sub": f"Deye Off-Grid monofásico · {kw} kW",
                "specs": [["Potencia", f"{kw} kW · monofásico"],
                          ["Modo de operación", "Off-Grid (sin conexión a red)"],
                          ["Garantía", "5 años"]]}

    if p == "inversor_huawei":
        # Huawei On Grid. Dos variantes de imagen según rango de potencia.
        kw = spec.get("kw", 20)
        grande = kw > 20
        img = "img_inversor_huawei_20_150.png" if grande else "img_inversor_huawei_20.png"
        rango = "20 a 150 kW" if grande else "hasta 20 kW"
        return {"img": img, "name": "Inversor",
                "sub": f"Huawei On Grid · {rango}",
                "specs": [["Potencia AC", f"{kw} kW"],
                          ["Tipo", "On Grid trifásico"],
                          ["Rango de la serie", rango],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "bateria_deye":
        # Batería Deye de baja tensión (línea SE-F). Default 16 kWh (SE-F16-L).
        kwh = spec.get("kwh", 16)
        modelo = spec.get("modelo", f"SE-F{kwh}-L" if kwh == 16 else f"SE-F{kwh} PLUS-L")
        return {"img": "img_bateria_deye.png", "name": "Batería",
                "sub": f"Deye {modelo} · baja tensión · {kwh} kWh",
                "specs": [["Capacidad", f"{kwh} kWh"],
                          ["Tensión", "Baja tensión (48V)"],
                          ["Química", "LiFePO4"],
                          ["Uso", "Respaldo y desplazamiento de consumo (peak shaving)"],
                          ["Garantía", "10 años"]]}

    if p == "bateria_pylontech_fidus":
        # Batería Pylontech Fidus, 16 kWh, formato todo-en-uno.
        return {"img": "img_bateria_pylontech_fidus.png", "name": "Batería",
                "sub": "Pylontech Fidus · 16 kWh",
                "specs": [["Capacidad", "16 kWh"],
                          ["Química", "LiFePO4"],
                          ["Formato", "Todo en uno, con ruedas de traslado"],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "bateria_pylontech_uf5000":
        # Batería Pylontech UF5000, 5 kWh, formato rack.
        return {"img": "img_bateria_pylontech_uf5000.png", "name": "Batería",
                "sub": "Pylontech UF5000 · 5 kWh",
                "specs": [["Capacidad", "5 kWh"],
                          ["Química", "LiFePO4"],
                          ["Formato", "Rack 19\""],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "estr_coplanar":
        # Estructura coplanar de aluminio sobre chapa. Misma imagen y descripción.
        n = spec.get("paneles")
        return {"img": "img_estr_chapa.png", "name": "Estructura · cubierta de chapa",
                "sub": "Coplanar de aluminio" + (f" · {n} paneles" if n else ""),
                "specs": [["Material", "Aluminio anodizado · tornillería inoxidable"],
                          ["Montaje", "Coplanar sobre cubierta metálica (chapa)"],
                          ["Ventajas", "Baja carga de viento · sin lastre · anticorrosión"],
                          ["Compatibilidad", "Chapa trapezoidal / sinusoidal de galpones"]]}

    if p == "estr_techo_plano":
        # Estructura triangular de aluminio con lastres de hormigón. Misma imagen y desc.
        n = spec.get("paneles")
        return {"img": "img_estr_plano.png", "name": "Estructura · techo plano",
                "sub": "Triangular de aluminio con lastres" + (f" · {n} paneles" if n else ""),
                "specs": [["Material", "Triángulos de aluminio regulables (Chiko)"],
                          ["Montaje", "Apoyada sobre lastres de hormigón"],
                          ["Ventaja clave", "Sin perforar losa ni membrana"],
                          ["Inclinación", "Ángulo regulable para optimizar generación"]]}

    if p == "estr_piso":
        # Estructura de piso, para terrenos/parques solares (sin techo).
        n = spec.get("paneles")
        return {"img": "img_estr_piso.png", "name": "Estructura · piso",
                "sub": "Estructura de piso de aluminio/acero" + (f" · {n} paneles" if n else ""),
                "specs": [["Montaje", "Sobre el terreno, con hincado o bases de hormigón"],
                          ["Uso típico", "Parques solares / terrenos amplios"],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "estr_tejas":
        # Estructura para techo de tejas (ganchos + riel).
        n = spec.get("paneles")
        return {"img": "img_estr_tejas.png", "name": "Estructura · techo de tejas",
                "sub": "Ganchos para teja + riel de aluminio" + (f" · {n} paneles" if n else ""),
                "specs": [["Montaje", "Ganchos bajo teja + riel de aluminio"],
                          ["Ventaja clave", "No requiere romper tejas"],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    if p == "estr_miniriel":
        # Estructura para chapa con mini-riel (perfil bajo).
        n = spec.get("paneles")
        return {"img": "img_estr_miniriel.png", "name": "Estructura · chapa (mini-riel)",
                "sub": "Mini-riel sobre chapa trapezoidal" + (f" · {n} paneles" if n else ""),
                "specs": [["Montaje", "Mini-riel atornillado directo sobre chapa"],
                          ["Ventaja clave", "Perfil bajo, económico, rápido de instalar"],
                          ["Garantía", "A confirmar con ficha técnica del fabricante"]]}

    raise ValueError(f"preset de ficha desconocido: {p}")


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

def compute(cfg):
    e = cfg["economia"]
    inv = cfg["inversion_usd"]; iva = cfg.get("iva", 0.21)
    total_iva = inv * (1 + iva)
    gen1 = cfg["generacion"]["anual_kwh"]
    cons_year = cfg["consumo"]["anual_kwh"]
    cobertura = gen1 / cons_year * 100
    tc = e["tc"]
    maint = e["mantenimiento"] * inv

    if e.get("modo") == "mensual_escalonado":
        # Modo para proyectos con generación estacional desalineada del consumo y/o
        # tarifa escalonada (ej. residencial con losa radiante en invierno). Calcula
        # autoconsumo/batería/excedente/déficit MES A MES en vez de un ratio plano anual,
        # y arma el costo real de cada mes con TODOS los componentes de la factura
        # (no solo el cargo variable): cargo fijo, recargos por ley, tasa municipal e
        # IVA (este último SOLO si el cliente no lo recupera, ej. residencial — para
        # comercial/industrial que sí lo recupera, dejar iva_frac_energia en 0, como en
        # el modo plano de JG Envases).
        cons_m = cfg["consumo"]["mensual_kwh"]; gen_m = cfg["generacion"]["mensual_kwh"]
        tar = e["tarifas"]; lim = tar["limite_kwh"]; p_bajo = tar["precio_bajo"]; p_alto = tar["precio_alto"]
        cf_bajo = tar.get("cargo_fijo_bajo", e.get("cargo_fijo_ars", 0))
        cf_alto = tar.get("cargo_fijo_alto", e.get("cargo_fijo_ars", 0))
        bat = e["bateria_kwh_mes"]
        # Default 50/50 día/noche salvo que el config lo aclare distinto.
        fdir = e.get("autoconsumo_directo_frac", 0.5); p_iny = e["valor_inyeccion_ars"]
        bat_ef = e.get("bateria_eficiencia", 1.0)
        leyes_frac = e.get("leyes_frac", 0.0)
        iva_frac_res = e.get("iva_frac_energia", 0.0)
        tasa_municipal = e.get("tasa_municipal_ars", 0)
        costo_sin = 0.0; costo_con = 0.0; ahorro_iny = 0.0
        autoc_total = 0.0; deficit_total = 0.0
        for m in MES_ORDER:
            if m not in gen_m:
                continue
            c = cons_m[m]; g = gen_m[m]
            # Las 4 variables del balance mensual, en el orden que prioriza el sistema:
            # 1) autoconsumo directo: cubre el consumo DIURNO (mitad del consumo total
            #    del mes), con la generación disponible ese mes. La otra mitad del
            #    consumo es nocturno y NUNCA puede cubrirse en directo, sin importar
            #    cuánto se genere de día — por eso el tope es 50% del CONSUMO, no de
            #    la generación.
            # 2) carga de batería: lo que sobra de generación después del directo, hasta
            #    el tope mensual de la batería (kWh "en bruto" que entran a cargarla).
            #    Se usa TODAS las noches para minimizar la compra a red.
            # 3) excedente inyectado: generación que no fue ni directo ni a cargar la
            #    batería.
            # 4) déficit comprado a la red: consumo nocturno no cubierto por lo que la
            #    batería efectivamente entrega (con pérdidas de eficiencia round-trip).
            necesidad_dia = fdir * c
            directo = min(necesidad_dia, g)
            necesidad_resto = c - directo
            bat_charge = min(g - directo, bat)          # kWh que cargan la batería
            bat_entregado = min(necesidad_resto, bat_charge * bat_ef)  # kWh útiles entregados
            autoc = directo + bat_entregado
            exced = g - directo - bat_charge
            deficit = c - autoc
            alto = c > lim
            precio_mes = p_alto if alto else p_bajo
            cargo_fijo = cf_alto if alto else cf_bajo
            # Cada mes se paga cargo fijo + tasa municipal aunque el déficit sea 0
            # (son cargos de conexión, no de energía consumida).
            base_sin = c * precio_mes + cargo_fijo
            base_con = deficit * precio_mes + cargo_fijo
            costo_sin += base_sin * (1 + leyes_frac + iva_frac_res) + tasa_municipal
            costo_con += base_con * (1 + leyes_frac + iva_frac_res) + tasa_municipal
            ahorro_iny += exced * p_iny
            autoc_total += autoc; deficit_total += deficit
        ahorro = (costo_sin - costo_con) + ahorro_iny
        con_kwh = deficit_total
        p_auto = costo_sin / cons_year
        p_iny_disp = p_iny
        auto = autoc_total / gen1 if gen1 else 0.0
        usdkwh1 = (ahorro / gen1) / tc if gen1 else 0.0
    else:
        p_auto = e["costo_real_kwh_ars"]; p_iny = e["valor_inyeccion_ars"]; p_iny_disp = p_iny
        auto = e["autoconsumo"]; iny = 1 - auto
        blend = auto * p_auto + iny * p_iny
        usdkwh1 = blend / tc
        autoc_kwh = auto * gen1
        con_kwh = cons_year - autoc_kwh
        costo_sin = cons_year * p_auto
        costo_con = con_kwh * p_auto
        ahorro = costo_sin - costo_con

    rec = []; acc = 0.0; payback_year = None; payback_months = None
    for y in range(1, 13):
        g = gen1 * ((1 - e["degradacion"]) ** (y - 1))
        p = min(usdkwh1 * ((1 + e["aumento_anual"]) ** (y - 1)), e["tope_usd_kwh"])
        bruto = g * p; neto = bruto - maint; prev = acc; acc += neto
        rec.append((y, g, p, bruto, neto, acc))
        if payback_year is None and prev < inv <= acc:
            payback_year = y
            payback_months = (y - 1) + (inv - prev) / neto
    if payback_months is None:
        payback_txt = "más de 12 años"
    else:
        yrs = int(payback_months); mos = round((payback_months - yrs) * 12)
        if mos == 12: yrs += 1; mos = 0
        payback_txt = f"{yrs} año{'s' if yrs != 1 else ''}" + (f" {mos} mes{'es' if mos != 1 else ''}" if mos else "")
    def french(sld, n, t):
        r = t / 12.0
        return sld * r / (1 - (1 + r) ** (-n)) if r > 0 else sld / n
    fin = []
    for (name, adp, n, t) in cfg["financiacion"]:
        adel = total_iva * adp; saldo = total_iva - adel
        if n == 0:
            fin.append((name, adp, adel, None, 0, 0.0, 0, total_iva))
        else:
            c = french(saldo, n, t); fin.append((name, adp, adel, saldo, n, t, c, adel + c * n))
    return dict(inv=inv, iva=iva, total_iva=total_iva, gen1=gen1, cons_year=cons_year,
                cobertura=cobertura, p_auto=p_auto, p_iny=p_iny_disp, auto=auto, tc=tc,
                ahorro=ahorro, ahorro_mes=ahorro / 12, pct_menos=ahorro / costo_sin * 100,
                costo_sin=costo_sin, costo_con=costo_con, con_kwh=con_kwh,
                tco2=gen1 * e.get("factor_co2", 0.000351),
                rec=rec, payback_year=payback_year, payback_txt=payback_txt,
                ahorro_neto_1=rec[0][4], acc_10=rec[9][5], fin=fin, e=e)

def chart_svg(cfg):
    cons = cfg["consumo"]["mensual_kwh"]; gen = cfg["generacion"]["mensual_kwh"]
    meses = [m for m in MES_ORDER if m in gen]
    vmax = max(max(cons.values()), max(gen.values()))
    ymax = int((vmax // 10000 + 1) * 10000)
    W, H = 700, 300; ml, mt, mr, mb = 54, 32, 8, 24
    pw, ph = W - ml - mr, H - mt - mb
    def yy(v): return mt + ph - (v / ymax * ph)
    gw = pw / len(meses); bw = gw * 0.30
    grid = ""; step = ymax // 4
    for gv in range(0, ymax + 1, step):
        y = yy(gv)
        grid += f'<line x1="{ml}" y1="{y:.1f}" x2="{W - mr}" y2="{y:.1f}" stroke="#ece9e2"/>'
        grid += f'<text x="{ml - 7}" y="{y + 3:.1f}" text-anchor="end" class="ax">{ar(gv, 0)}</text>'
    bars = ""
    for i, m in enumerate(meses):
        gx = ml + i * gw; cv = cons[m]; gvv = gen[m]
        x1 = gx + gw / 2 - bw - 1; x2 = gx + gw / 2 + 1
        bars += f'<rect x="{x1:.1f}" y="{yy(cv):.1f}" width="{bw:.1f}" height="{(mt + ph - yy(cv)):.1f}" rx="2.5" fill="#3a3a3a"/>'
        bars += f'<rect x="{x2:.1f}" y="{yy(gvv):.1f}" width="{bw:.1f}" height="{(mt + ph - yy(gvv)):.1f}" rx="2.5" fill="#ebb236"/>'
        bars += f'<text x="{gx + gw / 2:.1f}" y="{H - 7}" text-anchor="middle" class="mo">{m}</text>'
    legend = (f'<circle cx="{ml + 155}" cy="11" r="5" fill="#3a3a3a"/><text x="{ml + 165}" y="15" class="lg">Consumo {cfg.get("nombre_lugar", "del predio")}</text>'
              f'<circle cx="{ml + 300}" cy="11" r="5" fill="#ebb236"/><text x="{ml + 310}" y="15" class="lg">Generación solar estimada</text>')
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">
<style>.ax{{font-size:8.5px;fill:#a6a6a6;font-family:Lato}}.mo{{font-size:9px;fill:#8f8f8f;font-family:Lato}}.lg{{font-size:10px;fill:#555;font-family:Lato}}</style>
{grid}{bars}{legend}
<text x="12" y="{mt + ph / 2}" transform="rotate(-90 12 {mt + ph / 2})" text-anchor="middle" class="ax">kWh por mes</text></svg>'''

def img_src(p):
    if os.path.isabs(p) and os.path.exists(p): return p
    cand = os.path.join(ASSETS, p)
    return cand if os.path.exists(cand) else p

CSS = open(os.path.join(HERE, "_style.css"), encoding="utf-8").read()

def build(cfg, out):
    d = compute(cfg); s = cfg["sistema"]
    kwp = s["n_paneles"] * s["panel_wp"] / 1000.0
    def ficha(f):
        rows = "".join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in f["specs"])
        return (f'<div class="ficha"><div class="fimg"><img src="{img_src(f["img"])}"></div>'
                f'<div class="fbody"><div class="fname">{f["name"]}</div><div class="fsub">{f["sub"]}</div>'
                f'<table class="ft">{rows}</table></div></div>')
    fichas_html = "".join(ficha(catalogo_ficha(f)) for f in cfg["fichas"])
    comp_html = "".join(f'<tr><td class="c">{a}</td><td class="b">{b}</td><td>{c}</td><td class="r">{dd}</td></tr>'
                        for a, b, c, dd in cfg["componentes"])
    cons = cfg["consumo"]["mensual_kwh"]; gen = cfg["generacion"]["mensual_kwh"]
    meses = [m for m in MES_ORDER if m in gen]
    genrows = "".join(f'<tr><td>{MES_NOM[m]}</td><td class="r">{ar(cons[m], 0)}</td><td class="r">{ar(gen[m], 0)}</td></tr>' for m in meses)
    rec_html = ""
    for (y, g, p, br, ne, ac) in d["rec"]:
        cls = ' class="hl"' if y == d["payback_year"] else ''
        rec_html += (f'<tr{cls}><td class="c">{y}</td><td class="r">{ar(g, 0)}</td><td class="r">{p:.3f}</td>'
                     f'<td class="r">{usd(br)}</td><td class="r">{usd(ne)}</td><td class="r">{usd(ac)}</td></tr>')
    fin_html = ""
    for (name, adp, adel, saldo, n, t, c, tot) in d["fin"]:
        fin_html += (f'<tr><td class="b">{name}</td><td class="r">{adp * 100:.0f}%</td><td class="r">{usd(adel)}</td>'
                     f'<td class="r">{"—" if saldo is None else usd(saldo)}</td><td class="r">{"—" if n == 0 else n}</td>'
                     f'<td class="r">{"sin interés" if n == 0 else f"{t * 100:.0f}%"}</td>'
                     f'<td class="r">{"—" if c == 0 else usd(c)}</td><td class="r">{usd(tot)}</td></tr>')
    cond_html = "".join(f'<li><b>{h}.</b> {t}</li>' for h, t in cfg["condiciones"])
    ivapct = int(round(d["iva"] * 100))
    P = dict(cfg=cfg, s=s, d=d, kwp=kwp, LOGO=LOGO, fichas_html=fichas_html, comp_html=comp_html,
             svg=chart_svg(cfg), genrows=genrows, rec_html=rec_html, fin_html=fin_html,
             cond_html=cond_html, ivapct=ivapct)
    HTML(string=render(P), base_url=ASSETS + "/").write_pdf(out)
    return d

def render(P):
    cfg = P["cfg"]; s = P["s"]; d = P["d"]; kwp = P["kwp"]; ivapct = P["ivapct"]
    inv = d["inv"]; total_iva = d["total_iva"]; gen1 = d["gen1"]; cons_year = d["cons_year"]
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="rh">{P['LOGO']}</div>
<div class="page">
  <div class="prep" style="margin-top:2px;">Proyecto de energía solar</div>
  <h1>{cfg['titulo']}</h1>
  <p class="sub">{cfg['subtitulo']}</p>
  <hr>
  <div class="prep">Preparado para</div>
  <div class="prepline"><b>{cfg['cliente']}</b> · {cfg['ubicacion']} · Presupuesto N° {cfg['presupuesto']} · {cfg['fecha']}</div>
  <p>{cfg.get('texto_intro', f"El establecimiento consume alrededor de <b>{ar(cons_year, 0)} kWh por año</b> (≈ {ar(cons_year / 12, 0)} kWh por mes en promedio), con un costo actual de la energía en torno a <b>${ar(d['p_auto'], 1)} por kWh</b> (costo real con impuestos no recuperables). Proponemos una central solar que genera energía durante el día para consumirla en el momento y reducir la compra a la red.")}</p>
  {cfg.get('desglose_tarifa_html', '')}
  <div class="cards">
    <div class="card gold"><span class="tag"></span><div class="big">{s['n_paneles']} paneles</div><div class="cap">{s['panel_wp']} W bifaciales · {s['n_inversores']} inversor {s['inversor_marca']} de {s['inversor_kw']} kW</div></div>
    <div class="card green"><span class="tag"></span><div class="big">{ar(d['pct_menos'], 0)}% menos</div><div class="cap">de gasto en energía</div></div>
    <div class="card gray"><span class="tag"></span><div class="big">USD {ar(inv, 0)}</div><div class="cap">inversión llave en mano (sin IVA)</div></div>
    <div class="card gold"><span class="tag"></span><div class="big">{d['payback_txt']}</div><div class="cap">recupero de la inversión</div></div>
  </div>
  <div class="eyebrow" style="margin-top:15px;">El sistema propuesto</div>
  <h2>{cfg['sistema_titulo']}</h2>
  <p>{cfg['sistema_texto']}</p>
  <div class="stats">
    <div class="stat"><div class="big">{ar(kwp, 2)} kWp</div><div class="cap">Potencia pico instalada</div></div>
    <div class="stat"><div class="big">{s['paneles_chapa']} + {s['paneles_plano']}</div><div class="cap">Paneles en chapa · techo plano</div></div>
    <div class="stat"><div class="big">{s['n_inversores']} × {s['inversor_kw']} kW</div><div class="cap">Inversor {s['inversor_marca']} On Grid</div></div>
  </div>
  <table>
    <thead><tr><th></th><th>Componente</th><th>Descripción</th><th class="r">Cant.</th></tr></thead>
    <tbody>{P['comp_html']}
    <tr class="total"><td></td><td colspan="2">Inversión total del proyecto (sin IVA)</td><td class="r">USD {ar(inv, 0)}</td></tr>
    <tr class="total2"><td></td><td colspan="2">Inversión total con IVA ({ivapct}%)</td><td class="r">USD {ar(total_iva, 0)}</td></tr></tbody>
  </table>
  <div class="note">{cfg['nota_inversor']}</div>
</div>

<div class="page">
  <div class="eyebrow">Fichas técnicas</div>
  <h2>Componentes del sistema</h2>
  <p class="sub" style="font-size:11px;margin-bottom:10px;">Datos de placa de los productos principales.</p>
  {P['fichas_html']}
</div>

<div class="page">
  <div class="eyebrow">Generación y aprovechamiento</div>
  <h2>Cuánta energía genera <span class="light">· y cómo se compara con el consumo</span></h2>
  <p>La generación estimada es de <b>{ar(gen1, 0)} kWh por año</b>, calculada con software profesional de simulación. El gráfico compara, mes a mes, el consumo {cfg.get('nombre_lugar', 'del predio')} con la generación solar:</p>
  {P['svg']}
  <div class="note">{cfg.get('nota_autoconsumo', f"<b>Autoconsumo estimado: {ar(d['auto'] * 100, 0)}% de lo generado.</b> La generación representa cerca del {ar(d['cobertura'], 0)}% del consumo anual {cfg.get('nombre_lugar', 'del predio')} y la mayor parte del consumo ocurre de día —cuando la planta está en actividad—, por lo que prácticamente toda la energía solar se consume en el momento. Solo un excedente menor se inyectaría a la red en picos de mediodía de verano. Es un criterio conservador.")}</div>
  <div class="two">
    <div><table>
      <thead><tr><th>Mes</th><th class="r">Consumo (kWh)</th><th class="r">Generación (kWh)</th></tr></thead>
      <tbody>{P['genrows']}
      <tr class="total"><td>Total anual</td><td class="r">{ar(cons_year, 0)}</td><td class="r">{ar(gen1, 0)}</td></tr></tbody>
    </table></div>
    <div>
      <div class="eyebrow" style="margin-top:4px;">Cobertura</div>
      <h2 style="font-size:15px;">Qué parte del consumo cubre</h2>
      <div class="stat" style="margin:8px 0;"><div class="big" style="color:#4e9e3a;">~{ar(d['cobertura'], 0)}%</div><div class="cap">del consumo anual {cfg.get('nombre_lugar', 'del predio')}</div></div>
      <div class="stat" style="margin:8px 0;"><div class="big">{ar(d['auto'] * 100, 0)}% / {ar((1 - d['auto']) * 100, 0)}%</div><div class="cap">autoconsumo / inyección</div></div>
      <div class="stat" style="margin:8px 0;"><div class="big">{ar(d['tco2'], 0)} tCO₂</div><div class="cap">emisiones evitadas por año</div></div>
      <div class="cap-s">{cfg.get('nota_consumo', f'Consumo: promedio {cfg.get("nombre_lugar", "del predio")} según datos de facturación. Generación: simulación profesional.')}</div>
    </div>
  </div>
</div>

<div class="page">
  <div class="eyebrow">El ahorro</div>
  <h2>Cuánto se ahorra desde el primer día</h2>
  <p>Cuánto costaría la energía de un año entero al precio de hoy, con y sin la central solar. El cargo por potencia contratada no cambia; el ahorro se da sobre la energía.</p>
  <table>
    <thead><tr><th>Energía {cfg.get('nombre_lugar', 'del predio')} · a precio de hoy</th><th class="r">Sin central</th><th class="r">Con central</th></tr></thead>
    <tbody>
      <tr><td class="b">Energía comprada a la red (kWh/año)</td><td class="r">{ar(cons_year, 0)}</td><td class="r">{ar(d['con_kwh'], 0)}</td></tr>
      <tr><td class="b">Costo de esa energía (por año)</td><td class="r">$ {ar(d['costo_sin'], 0)}</td><td class="r">$ {ar(d['costo_con'], 0)}</td></tr>
      <tr><td class="b">Costo promedio por mes</td><td class="r">$ {ar(d['costo_sin'] / 12, 0)}</td><td class="r">$ {ar(d['costo_con'] / 12, 0)}</td></tr>
    </tbody>
  </table>
  <div class="cards" style="margin-top:10px;">
    <div class="card green"><span class="tag"></span><div class="big">$ {ar(d['ahorro'], 0)}</div><div class="cap">ahorro por año en energía</div></div>
    <div class="card green"><span class="tag"></span><div class="big">$ {ar(d['ahorro_mes'], 0)}</div><div class="cap">ahorro promedio por mes</div></div>
    <div class="card gold"><span class="tag"></span><div class="big">{ar(d['pct_menos'], 0)}%</div><div class="cap">menos de gasto en energía</div></div>
  </div>
  <p style="margin-top:8px;font-size:8.8px;color:#6b6b6b;">Equivale a unos <b>USD {ar(d['ahorro'] / d['tc'], 0)}</b> al tipo de cambio de hoy ($ {ar(d['tc'], 0)} BNA). Es "a precio de hoy y congelado": en la práctica crece a medida que evoluciona la tarifa.</p>
  <div class="eyebrow" style="margin-top:13px;">Análisis de recupero</div>
  <h2>En cuánto se recupera la inversión</h2>
  <table style="margin-bottom:5px;"><tbody>
      <tr><td>Inversión: <b>USD {ar(inv, 0)}</b> (sin IVA)</td><td>Aumento del costo + inflación (USD): <b>{ar(d['e']['aumento_anual'] * 100, 0)}% anual</b></td></tr>
      <tr><td>Generación año 1: <b>{ar(gen1, 0)} kWh</b></td><td>Tope de precio: <b>USD {ar(d['e']['tope_usd_kwh'], 2)}/kWh</b> · Degradación: <b>{ar(d['e']['degradacion'] * 100, 1)}%/año</b></td></tr>
      <tr><td>Costo real kWh (autoconsumo): <b>${ar(d['p_auto'], 1)}</b> · Inyección: <b>${ar(d['p_iny'], 0)}</b></td><td>Mantenimiento: <b>{ar(d['e']['mantenimiento'] * 100, 0)}%/año</b> · TC: <b>${ar(d['tc'], 0)}</b></td></tr>
  </tbody></table>
  <table>
    <thead><tr><th>Año</th><th class="r">Generación (kWh)</th><th class="r">USD/kWh</th><th class="r">Ahorro bruto</th><th class="r">Ahorro neto</th><th class="r">Acumulado</th></tr></thead>
    <tbody>{P['rec_html']}</tbody>
  </table>
  <div class="note">Modelo conservador: proyectamos el aumento del precio sólo hasta <b>USD {ar(d['e']['tope_usd_kwh'], 2)}/kWh</b> y ahí lo congelamos. Ese valor (USD 0,16–0,18/kWh) es aproximadamente el <b>costo promedio del kWh en América Latina</b>, y a su vez menor que el promedio de EE.UU. (~USD 0,19) y Europa (~USD 0,25). La fila resaltada marca el año en que el ahorro acumulado supera la inversión (<b>{d['payback_txt']}</b>).</div>
</div>

<div class="page">
  <div class="eyebrow">Financiación</div>
  <h2>Simulación de financiación</h2>
  <p>{cfg.get('nota_financiacion', f"Se calcula sobre el total con IVA incluido: <b>USD {ar(inv, 0)} + IVA {ivapct}% = USD {ar(total_iva, 0)}</b>. Aunque para la empresa el IVA se recupera, se desembolsa por adelantado, así que también se financia. Financiación propia de Oriens, en dólares oficiales Banco Nación; el contado fraccionado no tiene interés.")}</p>
  <table>
    <thead><tr><th>Modalidad</th><th class="r">Adelanto</th><th class="r">Adelanto (USD)</th><th class="r">Saldo financiado</th><th class="r">Cuotas</th><th class="r">TNA</th><th class="r">Cuota mensual</th><th class="r">Total</th></tr></thead>
    <tbody>{P['fin_html']}</tbody>
  </table>
  <div class="cap-s">La cuota se calcula sobre el saldo financiado a la TNA indicada. El tipo de cambio se toma al valor Banco Nación vigente a la fecha de cada pago.</div>
  <div class="eyebrow" style="margin-top:18px;">Condiciones y siguientes pasos</div>
  <h2>Cómo avanzamos</h2>
  <div class="two">
    <div><ol>{P['cond_html']}</ol></div>
    <div><div class="resume">
      <div class="t">En resumen</div>
      <p style="margin:0;font-size:9.5px;">Una inversión de <b>USD {ar(inv, 0)}</b> (USD {ar(total_iva, 0)} con IVA) que se recupera en <b>{d['payback_txt']}</b> y sigue generando ahorro durante más de dos décadas. A precio de hoy, el ahorro arranca en <b>$ {ar(d['ahorro'], 0)} por año</b> ({ar(d['pct_menos'], 0)}% de la energía) y crece a medida que evoluciona la tarifa. Con la ubicación de los paneles ya definida, el proyecto está listo para avanzar.</p>
    </div></div>
  </div>
</div>
</body></html>"""

if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "reference", "ejemplo_config.json")
    out = sys.argv[2] if len(sys.argv) > 2 else "Propuesta Oriens.pdf"
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    d = build(cfg, out)
    print(f"OK -> {out} | payback {d['payback_txt']} | ahorro/anio ${ar(d['ahorro'], 0)} | cobertura {ar(d['cobertura'], 0)}%")
