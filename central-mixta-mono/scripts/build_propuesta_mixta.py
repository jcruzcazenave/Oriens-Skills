#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builder de la propuesta MIXTA MONOFASICA de Oriens Energia Solar.

Compara 2 o 3 alternativas sobre bajada monofasica donde al menos una es
OFF GRID (en paralelo a la red, sin inyectar) y otra HIBRIDA (con inyeccion
del excedente y credito que se arrastra mes a mes).

Uso:
    python build_propuesta_mixta.py config.json "salida.pdf"
    python build_propuesta_mixta.py config.json --solo-calculo   # sin PDF

Todo sale del JSON. Ver reference/metodologia_mixta.md y reference/config_schema.md.
"""
import json, sys, os

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

OG, HB = "off_grid", "hibrido"


# ---------------- formato ----------------
def num(v, dec=0):
    return f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def ars(v, dec=0):
    return "$" + num(v, dec)


def usd(v, dec=0):
    return "USD " + num(v, dec)


def pct(v, dec=0):
    return num(v * 100, dec) + " %"


def anios_meses(x):
    if x is None:
        return "más de 25 años"
    a = int(x)
    m = int(round((x - a) * 12))
    if m == 12:
        a, m = a + 1, 0
    s = f"{a} año{'s' if a != 1 else ''}"
    return s + (f" y {m} mes{'es' if m != 1 else ''}" if m else "")


# ---------------- tarifa ----------------
def multiplicador(tar):
    return 1 + tar.get("leyes_frac", 0.0) + tar.get("iva_frac", 0.0)


def tramo_de(consumo, tar):
    if tar.get("modo", "bloque") == "plano":
        return tar["precio_kwh"], tar.get("cargo_fijo", 0.0)
    for t in tar["tramos"]:
        if t["hasta"] is None or consumo <= t["hasta"] - 0.01:
            return t["precio_kwh"], t["cargo_fijo"]
    t = tar["tramos"][-1]
    return t["precio_kwh"], t["cargo_fijo"]


def factura(consumo, tar, credito=0.0):
    """Devuelve (pago, credito_remanente).

    Energia = kWh x (precio del tramo + cargos variables por kWh) x multiplicador.
    Fijo    = cargo fijo del tramo x multiplicador + fijos exentos (alumbrado, etc.).
    El credito por inyeccion (pesos planos) descuenta SOLO de la energia; nunca del fijo.
    modo 'bloque': todo el consumo al precio del tramo alcanzado (cooperativas).
    modo 'plano' : un unico precio y un unico cargo fijo.
    """
    precio, cf = tramo_de(consumo, tar)
    m = multiplicador(tar)
    energia = consumo * (precio + tar.get("cargo_variable_kwh", 0.0)) * m
    fijo = cf * m + tar.get("fijos_exentos", 0.0)
    usado = min(energia, credito)
    return fijo + energia - usado, credito - usado


def precio_inyeccion(tar):
    """Criterio Oriens: 50% del promedio, sin impuestos, del precio de TODOS los tramos."""
    if tar.get("precio_inyeccion_kwh") is not None:
        return tar["precio_inyeccion_kwh"]
    if tar.get("modo", "bloque") == "plano":
        return tar["precio_kwh"] / 2
    ps = [t["precio_kwh"] for t in tar["tramos"]]
    return sum(ps) / len(ps) / 2


# ---------------- motor ----------------
def generacion_de(sis, alt):
    if alt.get("generacion_mensual_kwh"):
        return list(alt["generacion_mensual_kwh"])
    base = sis["generacion_base"]
    k = alt["paneles"] / base["paneles"]
    return [g * k for g in base["mensual_kwh"]]


def simular_anio(cfg, alt, gen, inyecta, saldo0=0.0):
    """Un anio completo, recorrido desde mes_inicio para arrastrar el credito.
    Devuelve filas indexadas por mes calendario y el saldo final."""
    con, sup = cfg["consumo"], cfg["supuestos"]
    tar = con["tarifa"]
    cons = con["meses_kwh"]
    dia_frac = sup.get("autoconsumo_dia_frac", 0.5)
    efic = sup.get("bateria_eficiencia", 0.9)
    reserva = sup.get("reserva_bateria_kwh", 0.0)
    p_iny = precio_inyeccion(tar)
    bat = max(alt.get("bateria_util_kwh", 0.0) - reserva, 0.0)
    ini = sup.get("mes_inicio_idx", 8)
    filas = [None] * 12
    saldo = saldo0
    for k in range(12):
        i = (ini + k) % 12
        c, g, d = cons[i], gen[i], DIAS[i]
        dia = dia_frac * c
        noche = c - dia
        directo = min(dia, g)
        sobra = g - directo
        aporte = min(noche, bat * efic * d, sobra * efic) if bat > 0 else 0.0
        carga = aporte / efic if efic else 0.0
        resto = max(sobra - carga, 0.0)
        red = max(c - directo - aporte, 0.0)
        if alt["modo"] == HB:
            iny, perdido = resto, 0.0
        else:
            iny, perdido = 0.0, resto
        credito = saldo + (iny * p_iny if inyecta else 0.0)
        pago, saldo = factura(red, tar, credito)
        filas[i] = dict(mes=MESES[i], consumo=c, gen=g, directo=directo, bateria=aporte,
                        red=red, iny=iny, perdido=perdido, pago=pago, saldo=saldo)
    return filas, saldo


def resumen(filas):
    s = lambda k: sum(f[k] for f in filas)
    return dict(gen=s("gen"), directo=s("directo"), bateria=s("bateria"), red=s("red"),
                iny=s("iny"), perdido=s("perdido"), pago=s("pago"))


def calcular(cfg):
    if not cfg["consumo"].get("tarifa") or cfg["consumo"]["tarifa"].get("precio_kwh") is None and not cfg["consumo"]["tarifa"].get("tramos"):
        # sin tarifa: propuesta sólo en energía; tarifa nula para que el motor corra
        cfg["consumo"]["tarifa"] = {"modo": "plano", "precio_kwh": 0.0, "cargo_fijo": 0.0, "precio_inyeccion_kwh": 0.0}
        cfg["documento"]["sin_tarifa"] = True
    con, sis, sup = cfg["consumo"], cfg["sistema"], cfg["supuestos"]
    tar = con["tarifa"]
    tc = sup["tc"]
    cons = con["meses_kwh"]
    cons_anual = sum(cons)
    fact_sin = [factura(c, tar)[0] for c in cons]
    fsa = sum(fact_sin)
    aumento = sup.get("aumento_anual_usd", 0.10)
    degr = sup.get("degradacion", 0.005)
    sin_iny = sup.get("anios_sin_inyeccion", 1)
    horizonte = sup.get("horizonte_anios", 25)
    ver_rec = cfg["documento"].get("mostrar_recupero", False)

    alts = []
    for a in cfg["alternativas"]:
        gen = generacion_de(sis, a)
        # anio 1: sin inyeccion valorizada (alta de Usuario-Generador en tramite)
        f1, _ = simular_anio(cfg, a, gen, inyecta=False)
        r1 = resumen(f1)
        # regimen: con inyeccion valorizada (solo hibrido y solo si hay recupero)
        valoriza = a["modo"] == HB and cfg["documento"].get("valorizar_inyeccion", ver_rec)
        if valoriza:
            _, s_prev = simular_anio(cfg, a, gen, True, 0.0)
            f2, s_fin = simular_anio(cfg, a, gen, True, s_prev)
            credito_muerto = max(s_fin - s_prev, 0.0)
        else:
            f2, credito_muerto = f1, 0.0
        r2 = resumen(f2)
        ahorro1 = fsa - r1["pago"]
        ahorro2 = fsa - r2["pago"]

        # recupero a 25 anios
        inversion = a.get("inversion_usd", a["total_usd"])
        acum, repago, saldo, anual = 0.0, None, 0.0, []
        for n in range(1, horizonte + 1):
            g_n = [x * (1 - degr) ** (n - 1) for x in gen]
            iny_on = a["modo"] == HB and n > sin_iny
            fn, saldo = simular_anio(cfg, a, g_n, iny_on, saldo if iny_on else 0.0)
            ah_usd = (fsa - resumen(fn)["pago"]) / tc * (1 + aumento) ** (n - 1)
            if repago is None and acum + ah_usd >= inversion:
                repago = n - 1 + (inversion - acum) / ah_usd if ah_usd > 0 else None
            acum += ah_usd
            anual.append(ah_usd)

        kwp = a["paneles"] * sis["panel_wp"] / 1000
        alts.append(dict(
            cfg=a, modo=a["modo"], gen=gen, f1=f1, f2=f2, r1=r1, r2=r2, kwp=kwp,
            paneles=a["paneles"], cobertura=(r1["directo"] + r1["bateria"]) / cons_anual,
            ahorro1=ahorro1, ahorro2=ahorro2, fact1=r1["pago"], fact2=r2["pago"],
            credito_muerto=credito_muerto, inversion=inversion, repago=repago,
            acum=acum, anual_usd=anual, respaldo=bool(a.get("bateria_kwh")),
        ))
    return dict(cons=cons, cons_anual=cons_anual, fact_sin=fact_sin, fsa=fsa,
                fsm=fsa / 12, alts=alts, tc=tc, p_iny=precio_inyeccion(tar),
                dia_frac=sup.get("autoconsumo_dia_frac", 0.5),
                efic=sup.get("bateria_eficiencia", 0.9), sin_iny=sin_iny,
                aumento=aumento, degr=degr, horizonte=horizonte)


# ---------------- chequeos para el asesor (consola) ----------------
def chequeos(cfg, d):
    avisos = []
    fijo_min = factura(0, cfg["consumo"]["tarifa"])[0] * 12
    for a in d["alts"]:
        ac = a["cfg"]
        if a["modo"] == OG and a["r1"]["perdido"] > 0.25 * a["r1"]["gen"]:
            avisos.append(f'{ac["id"]} (off grid): se pierde el {pct(a["r1"]["perdido"] / a["r1"]["gen"])} '
                          f'de la generación ({num(a["r1"]["perdido"])} kWh/año). Paneles de más no bajan la factura.')
        if a["credito_muerto"] > 0:
            avisos.append(f'{ac["id"]} (híbrida): saturación — quedan {ars(a["credito_muerto"])}/año de crédito '
                          f'sin usar. La factura ya está en el piso de cargos fijos ({ars(fijo_min)}/año).')
        inv = ac.get("inversor_kw", 0)
        for m in (5, 6, 7):  # invierno: la bateria recibe algo?
            f = a["f1"][m]
            if a["respaldo"] and f["bateria"] < 0.3 * ac.get("bateria_util_kwh", 0) * DIAS[m]:
                avisos.append(f'{ac["id"]}: en {MESES[m]} la batería cicla sólo {num(f["bateria"] / DIAS[m], 1)} kWh/día '
                              f'de {num(ac.get("bateria_util_kwh", 0), 1)} útiles. No prometer que "ataca el invierno".')
                break
        cargas = cfg.get("cargas") or []
        resp_w = sum(c["potencia_w"] for c in cargas if c.get("circuito") == "respaldo")
        if resp_w and inv and resp_w > inv * 1000 * 0.8:
            avisos.append(f'{ac["id"]}: cargas en respaldo suman {num(resp_w / 1000, 1)} kW contra un inversor de '
                          f'{num(inv, 1)} kW. Pasar cargas pesadas al circuito de red.')
    ogs = [a for a in d["alts"] if a["modo"] == OG]
    if len(ogs) >= 2:
        k = lambda a: (a["paneles"], a["cfg"]["inversor_kw"])
        if len({k(a) for a in ogs}) > 1:
            avisos.append("Esquema estándar: las off grid deberían diferir SÓLO en la batería, y difieren en "
                          "paneles o inversor. Confirmar con el asesor.")
    pots = {a["cfg"]["inversor_kw"] for a in d["alts"]}
    if len(pots) > 1:
        avisos.append("Las alternativas no tienen la misma potencia de inversor ("
                      + " / ".join(f'{a["cfg"]["id"]}: {num(a["cfg"]["inversor_kw"], 1)} kW' for a in d["alts"])
                      + "). Revisar qué cargas entran en el circuito respaldado de cada una.")
    kwp_max = max(a["kwp"] for a in d["alts"])
    if kwp_max > cfg["sistema"].get("limite_mono_kwp", 10):
        avisos.append(f'Potencia solar {num(kwp_max, 2)} kWp: confirmar con la distribuidora el máximo admitido '
                      f'para un suministro monofásico como Usuario-Generador.')
    return avisos


# ---------------- html ----------------
def tag_modo(modo):
    return ('<span class="modo og">Off grid</span>' if modo == OG
            else '<span class="modo hb">Híbrida</span>')


def nota_estandar(alts, ver_iny):
    """Nota descriptiva del esquema estándar: off grid batería chica / off grid batería grande /
    híbrida con la batería grande (puede llevar más paneles). Describe, no recomienda.
    Devuelve "" si el esquema no aplica."""
    ogs = [a for a in alts if a["modo"] == OG]
    hbs = [a for a in alts if a["modo"] == HB]
    if len(ogs) != 2 or len(hbs) != 1:
        return ""
    o1, o2 = sorted(ogs, key=lambda a: a["cfg"].get("bateria_kwh", 0))
    h = hbs[0]
    if o1["paneles"] != o2["paneles"] or o1["cfg"]["inversor_kw"] != o2["cfg"]["inversor_kw"]:
        return ""
    i1, i2, ih = o1["cfg"]["id"], o2["cfg"]["id"], h["cfg"]["id"]
    t = (f'<b>De la {i1} a la {i2} cambia sólo la batería.</b> Con más capacidad, la casa usa de noche '
         f'{num(o2["r1"]["bateria"] - o1["r1"]["bateria"])} kWh/año más de energía propia y la cobertura del consumo '
         f'pasa de {pct(o1["cobertura"])} a {pct(o2["cobertura"])}. ')
    if h["cfg"].get("bateria_kwh") != o2["cfg"].get("bateria_kwh"):
        return t
    if h["paneles"] == o2["paneles"]:
        t += (f'<b>De la {i2} a la {ih} cambia sólo qué pasa con el excedente.</b> Comparten paneles y batería, así que '
              f'mientras se tramita el alta como Usuario-Generador rinden igual. Una vez aprobada, los '
              f'{num(h["r1"]["iny"])} kWh/año que en la {i2} no se aprovechan, en la {ih} se inyectan a la red')
    else:
        t += (f'<b>De la {i2} a la {ih} cambia el destino del excedente, y con él la cantidad de paneles.</b> '
              f'Sin inyección, sumar paneles casi no suma energía aprovechada: en la {i2} ya quedan '
              f'{num(o2["r1"]["perdido"])} kWh/año sin aprovechar. En la {ih}, con la misma batería y '
              f'{h["paneles"]} paneles en lugar de {o2["paneles"]}, la cobertura del consumo pasa a {pct(h["cobertura"])} '
              f'y lo que sobra, {num(h["r1"]["iny"])} kWh/año, se inyecta a la red una vez aprobada el alta')
    t += (f' y baja la factura anual a {ars(h["fact2"])}, contra {ars(o2["fact1"])} en la {i2}.' if ver_iny
          else ' y genera crédito para las facturas siguientes.')
    return t


def render(cfg, d):
    doc, cli, sis, con = cfg["documento"], cfg["cliente"], cfg["sistema"], cfg["consumo"]
    alts = d["alts"]
    n_alt = len(alts)
    ver_rec = doc.get("mostrar_recupero", False)
    ver_iny = doc.get("valorizar_inyeccion", ver_rec)
    est = con.get("estimado", False)
    sin_tar = doc.get("sin_tarifa", False)
    if sin_tar:
        ver_iny = False
    ver_ahorro = doc.get("mostrar_ahorro", True)
    ver_mes = doc.get("mostrar_mes_a_mes", True)
    ver_modos = doc.get("mostrar_modos", True)
    resp = cfg.get("respaldo")
    cargas = cfg.get("cargas") or []
    palabra_n = {2: "Dos", 3: "Tres"}.get(n_alt, str(n_alt))

    rh = (f'<div class="rh"><div><div class="rht">{doc["titulo"]}</div>'
          f'<div class="rhc">{cli["nombre"]}</div></div>{LOGO}</div>')

    # ---------- pagina 1 ----------
    cards = ""
    for a in alts:
        ac = a["cfg"]
        cls = "card gold" if a["modo"] == HB else "card"
        cards += f'''<div class="{cls}"><span class="tag"></span>
<div class="ttl">Alternativa {ac["id"]} — {ac["nombre"]}{tag_modo(a["modo"])}</div>
<div class="pr">{usd(ac["total_usd"], 0)}</div>
<div class="small">total contado, IVA incluido</div>
<div class="txt">{ac["resumen"]}</div>
<div style="margin-top:8px">
<div class="kv"><span>Inyecta excedente a la red</span><b>{"Sí" if a["modo"] == HB else "No"}</b></div>
<div class="kv"><span>Respaldo ante cortes</span><b>{"Sí" if a["respaldo"] else "No"}</b></div>
<div class="kv"><span>Paneles solares</span><b>{a["paneles"]} × {sis["panel_wp"]} Wp</b></div>
<div class="kv"><span>Batería</span><b>{ac.get("bateria_desc", "—")}</b></div>
</div></div>'''

    if sin_tar:
        stats_fact = ((f'<div class="stat"><div class="big">{pct(d["dia_frac"])}</div><div class="cap">consumo diurno</div></div>'
                       f'<div class="stat gold"><div class="big">{pct(1 - d["dia_frac"])}</div><div class="cap">consumo nocturno</div></div>')
                      if doc.get("mostrar_reparto", False) else "")
    else:
        stats_fact = (f'<div class="stat"><div class="big">{ars(d["fsm"])}</div><div class="cap">{"factura mensual estimada, sólo con la red" if est else "factura promedio mensual"}</div></div>'
                      f'<div class="stat gold"><div class="big">{ars(d["fsa"])}</div><div class="cap">{"factura anual estimada, sólo con la red" if est else "factura anual actual"}</div></div>')
    kws = sorted({a["cfg"]["inversor_kw"] for a in alts})
    pan = sorted({a["paneles"] for a in alts})
    p1 = f'''{rh}<div class="page">
<div class="eyebrow">{doc["eyebrow"]}</div>
<h1>{doc["titulo"]}</h1>
<div class="sub">{doc["subtitulo"]}</div>
<div class="prep">Preparada para</div>
<div class="prepline"><b>{cli["nombre"]}</b>{f'<span>{cli["ubicacion"]}</span>' if cli.get("ubicacion") else ""}<span>{cli["fecha"]}</span></div>
<div class="eyebrow">El proyecto</div>
<h2>{palabra_n} caminos para la misma instalación</h2>
<p>{doc["intro"]}</p>
<div class="stats">
<div class="stat"><div class="big">220 V</div><div class="cap">suministro monofásico</div></div>
<div class="stat"><div class="big">{" o ".join(num(k, 1) for k in kws)} kW</div><div class="cap">inversor, según alternativa</div></div>
<div class="stat"><div class="big">{" o ".join(str(p) for p in pan)}</div><div class="cap">paneles, según alternativa</div></div>
<div class="stat gold"><div class="big">{n_alt}</div><div class="cap">alternativas, off grid o híbridas</div></div>
</div>
<hr>
<div class="eyebrow">Punto de partida</div>
<h2>{"Consumo estimado" if est else "Su consumo hoy"}</h2>
<p>{con.get("texto") or (f'El suministro de {con["distribuidora"]} todavía no está conectado, así que no hay facturas previas: el consumo se estimó a partir de los equipos y del uso declarados' + ('.' if sin_tar else f', y se valorizó con la tarifa vigente de {con["distribuidora"]}.') if est else f'Analizamos {con["periodo_analizado"]} de su suministro de {con["distribuidora"]} ({con["tipo_usuario"]}).')}</p>
<div class="stats">
<div class="stat"><div class="big">{num(d["cons_anual"])} kWh</div><div class="cap">consumo anual</div></div>
<div class="stat"><div class="big">{num(d["cons_anual"] / 12)} kWh</div><div class="cap">promedio mensual</div></div>
{stats_fact}
</div>
<hr>
<div class="eyebrow">Las alternativas</div>
<h2>Qué resuelve cada una</h2>
<div class="cards">{cards}</div>
</div>'''

    # ---------- pagina 2: off grid vs hibrida + respaldo ----------
    vs_def = [
        ("Qué pasa con el excedente", "No se inyecta: lo que no consume la casa ni entra en la batería no se aprovecha.",
         "Se inyecta a la red y genera un crédito que descuenta de la energía de las facturas siguientes."),
        ("Trámite ante la distribuidora", "No requiere alta como Usuario-Generador ni cambio de medidor.",
         "Requiere el alta como Usuario-Generador y un medidor bidireccional. Hasta que se aprueba, el sistema funciona igual, sin inyectar."),
        ("Cuándo empieza a ahorrar", "Desde el día de la puesta en marcha.",
         "El autoconsumo, desde el primer día; el crédito por inyección, una vez aprobada el alta."),
        ("Respaldo ante cortes", "Con batería, sostiene las cargas esenciales.",
         "Con batería, sostiene las cargas esenciales."),
        ("Ampliación futura", "Sumar paneles sólo rinde si crece el consumo o la batería.",
         "Sumar paneles siempre suma: lo que no se usa se inyecta."),
    ]
    vs = cfg.get("modos_comparacion") or vs_def
    vs_rows = "".join(f'<tr><td>{k}</td><td>{o}</td><td>{h}</td></tr>' for k, o, h in vs)
    bloque_modos = f'''<div class="eyebrow">Off grid o híbrida</div>
<h2>Qué cambia entre una y otra</h2>
<p>{doc.get("texto_modos", "Las dos trabajan en paralelo al suministro de la red y priorizan siempre la energía solar: primero la usa la casa, después carga la batería y sólo se toma de la red lo que falta. La diferencia está en qué se hace con la energía que sobra.")}</p>
<table class="vs"><tr><th>&nbsp;</th><th>Off grid · sin inyección</th><th>Híbrida · con inyección</th></tr>{vs_rows}</table>''' if ver_modos else ""

    if cargas:
        esen = [c["nombre"] for c in cargas if c.get("circuito") == "respaldo"]
        difer = [c["nombre"] for c in cargas if c.get("circuito") != "respaldo"]
    else:
        esen = resp.get("esenciales", []) if resp else []
        difer = resp.get("diferibles", []) if resp else []
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    bloque_resp = f'''<div class="eyebrow">Cortes de luz y cargas pesadas</div>
<h2>Qué queda respaldado y qué va directo a la red</h2>
<p>{resp["motivo"]}</p>
<p>{resp.get("autonomia_ejemplo", "")} El límite no es sólo la energía guardada sino la potencia
simultánea que entregan el inversor y la batería (hasta {num(resp["descarga_max_kw"], 1)} kW). Por eso
la instalación se divide en dos circuitos: uno respaldado por el sistema y otro conectado
directo a la red.</p>
<div class="two">
<div><div class="box"><h3>Circuito respaldado</h3><ul>{li(esen)}</ul></div></div>
<div><div class="box"><h3>Circuito directo a la red</h3><ul>{li(difer)}</ul></div></div>
</div>
<div class="note"><b>Se define en la visita técnica.</b> {resp["nota"]}</div>''' if resp else ""

    p2_body = bloque_modos + ("<hr>" if bloque_modos and bloque_resp else "") + bloque_resp
    p2 = f'{rh}<div class="page">{p2_body}</div>' if p2_body else ""

    # ---------- pagina 3: comparativa, mes a mes, recupero ----------
    def frow(label, fn, cls=""):
        return (f'<tr class="{cls}"><td>{label}</td>'
                + "".join(f'<td class="b r">{fn(a)}</td>' for a in alts) + "</tr>")

    heads = "".join(f'<th class="r">{a["cfg"]["id"]} · {a["cfg"]["nombre"]}</th>' for a in alts)
    econ = ""
    ver_cob = doc.get("mostrar_cobertura", True)
    if not ver_cob:
        econ += frow("Generación anual estimada", lambda a: num(a["r1"]["gen"]) + " kWh")
    if ver_ahorro and ver_cob:
        econ += frow("Generación anual", lambda a: num(a["r1"]["gen"]) + " kWh")
        econ += frow("Energía solar usada por la casa", lambda a: num(a["r1"]["directo"] + a["r1"]["bateria"]) + " kWh/año")
        econ += frow("Cobertura del consumo estimado" if est else "Cobertura del consumo actual", lambda a: pct(a["cobertura"]))
        econ += frow("Excedente inyectado a la red", lambda a: num(a["r1"]["iny"]) + " kWh/año" if a["modo"] == HB else "—")
        econ += frow("Excedente no aprovechado", lambda a: num(a["r1"]["perdido"]) + " kWh/año" if a["modo"] == OG else "—")
        if sin_tar:
            econ += frow("Energía tomada de la red", lambda a: num(a["r1"]["red"]) + " kWh/año")
        elif ver_iny:
            econ += frow(f"Factura promedio · año 1", lambda a: ars(a["fact1"] / 12))
            econ += frow("Factura promedio · desde año 2", lambda a: ars(a["fact2"] / 12))
            econ += frow("Ahorro año 1" + (" frente a la red" if est else ""), lambda a: ars(a["ahorro1"]), "hl")
            econ += frow("Ahorro anual desde el año 2", lambda a: ars(a["ahorro2"]), "hl")
        elif not sin_tar:
            econ += frow("Factura promedio con el sistema", lambda a: ars(a["fact1"] / 12))
            econ += frow("Ahorro anual estimado" + (" frente a la red" if est else ""), lambda a: ars(a["ahorro1"]), "hl")
        if sin_tar:
            econ = econ.replace('<tr class=""><td>Cobertura', '<tr class="hl"><td>Cobertura')
    elif ver_ahorro and not sin_tar:
        econ += frow("Factura promedio con el sistema", lambda a: ars(a["fact1"] / 12))
        econ += frow("Ahorro anual estimado", lambda a: ars(a["ahorro1"]), "hl")
    econ += frow("Inversión (contado, IVA incl.)", lambda a: usd(a["cfg"]["total_usd"]))
    if ver_rec:
        econ += frow("Recupero estimado de la inversión", lambda a: anios_meses(a["repago"]), "hl")

    comp = f'''<table class="comp"><tr><th>&nbsp;</th>{heads}</tr>
{frow("Modalidad", lambda a: "Off grid · sin inyección" if a["modo"] == OG else "Híbrida · con inyección")}
{frow("Paneles solares", lambda a: f'{a["paneles"]} × {sis["panel_wp"]} Wp')}
{frow("Potencia solar instalada", lambda a: num(a["kwp"], 2) + " kWp")}
{frow("Inversor", lambda a: a["cfg"]["inversor_desc"])}
{frow("Potencia disponible", lambda a: num(a["cfg"]["inversor_kw"], 1) + " kW" + (f' · picos {num(a["cfg"]["inversor_pico_kw"], 0 if float(a["cfg"]["inversor_pico_kw"]).is_integer() else 1)} kW' if a["cfg"].get("inversor_pico_kw") else ""))}
{frow("Almacenamiento", lambda a: a["cfg"].get("bateria_desc", "Sin batería"))}
{frow("Respaldo ante cortes", lambda a: "Sí · circuito respaldado" if a["respaldo"] else "No")}
{frow("Alta como Usuario-Generador", lambda a: "No requiere" if a["modo"] == OG else "Requiere")}
{econ}
</table>'''

    nota_txt = doc.get("nota_comparativa")
    if nota_txt is None:
        nota_txt = nota_estandar(alts, ver_iny)
    nota_comp = f'<div class="note">{nota_txt}</div>' if nota_txt else ""

    bloque_mes = ""
    if ver_mes:
        sh1 = "".join(f'<th class="r" colspan="3">{a["cfg"]["id"]} · {"off grid" if a["modo"] == OG else "híbrida"}</th>' for a in alts)
        sh2 = "".join('<th class="r">gen.</th><th class="r">{}</th><th class="r">red</th>'.format(
            "no aprov." if a["modo"] == OG else "inyect.") for a in alts)
        rows = ""
        for i in range(12):
            rows += f'<tr><td class="b">{MESES[i]}</td><td class="r">{num(d["cons"][i])}</td>'
            for a in alts:
                f = a["f1"][i]
                x = f["perdido"] if a["modo"] == OG else f["iny"]
                rows += f'<td class="r">{num(f["gen"])}</td><td class="r muted">{num(x)}</td><td class="r">{num(f["red"])}</td>'
            rows += "</tr>"
        tot = f'<tr class="total"><td>Año</td><td class="r">{num(d["cons_anual"])}</td>'
        for a in alts:
            x = a["r1"]["perdido"] if a["modo"] == OG else a["r1"]["iny"]
            tot += f'<td class="r">{num(a["r1"]["gen"])}</td><td class="r">{num(x)}</td><td class="r">{num(a["r1"]["red"])}</td>'
        tot += "</tr>"
        bloque_mes = f'''<div class="eyebrow">Mes a mes</div>
<h2>Generación, excedente y energía tomada de la red</h2>
<table><tr><th rowspan="2">Mes</th><th class="r" rowspan="2">Consumo<br>kWh</th>{sh1}</tr>
<tr>{sh2}</tr>{rows}{tot}</table>
<div class="small">Valores en kWh. {doc["nota_generacion"]} El consumo se toma {pct(d["dia_frac"])} diurno y
{pct(1 - d["dia_frac"])} nocturno, y la batería con {pct(d["efic"])} de eficiencia de carga y descarga.</div>'''

    bloque_rec = ""
    if ver_rec:
        rrows = "".join(
            f'<tr><td class="b">{a["cfg"]["id"]} · {a["cfg"]["nombre"]}</td>'
            f'<td class="r">{usd(a["inversion"])}</td><td class="r">{usd(a["anual_usd"][0])}</td>'
            f'<td class="r">{usd(a["anual_usd"][1]) if len(a["anual_usd"]) > 1 else "—"}</td>'
            f'<td class="r b">{anios_meses(a["repago"])}</td>'
            f'<td class="r">{usd(a["acum"])}</td></tr>' for a in alts)
        bloque_rec = f'''<div class="eyebrow">Recupero</div>
<h2>Cuándo se paga sola cada alternativa</h2>
<table><tr><th>Alternativa</th><th class="r">Inversión</th><th class="r">Ahorro año 1</th>
<th class="r">Ahorro año 2</th><th class="r">Recupero</th><th class="r">Ahorro {d["horizonte"]} años</th></tr>{rrows}</table>
<div class="small">Ahorro en dólares con un aumento de la tarifa de {pct(d["aumento"])} anual en dólares y
{pct(d["degr"], 1)} anual de degradación de los paneles. En las alternativas híbridas, el primer
{"año" if d["sin_iny"] == 1 else f'{d["sin_iny"]} años'} se calcula sin crédito por inyección (plazo del alta como
Usuario-Generador); desde entonces, cada kWh inyectado se valoriza a {ars(d["p_iny"], 2)} y el crédito que no se
usa en un mes pasa al siguiente.</div>'''

    p3 = f'''{rh}<div class="page">
<div class="eyebrow">Comparativa</div>
<h2>Las alternativas, lado a lado</h2>
{comp}{nota_comp}{"<hr>" + bloque_rec if bloque_rec else ""}</div>'''
    if not doc.get("mostrar_comparativa", True):
        p3 = f'{rh}<div class="page">{bloque_rec}</div>' if bloque_rec else ""
    mes_en_p4 = bloque_mes

    # ---------- como funciona (diagrama + situaciones + monitoreo) ----------
    red_nom = f'Red {con["distribuidora"]}'
    hay_og = any(a["modo"] == OG for a in alts)
    hay_hb = any(a["modo"] == HB for a in alts)
    svg = f"""<svg viewBox="0 0 560 300" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:470px;display:block;margin:6px auto 2px">
<defs>
<marker id="ag" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#e0a92a"/></marker>
<marker id="ay" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#a9a9a9"/></marker>
<marker id="ab" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4a8fd8"/></marker>
<marker id="ad" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#3a3a3a"/></marker>
</defs>
<g fill="none" stroke-width="2.4" stroke-dasharray="7 5">
<path d="M150 55 H190 V135 H212" stroke="#e0a92a" marker-end="url(#ag)"/>
<path d="M410 55 H370 V135 H348" stroke="#a9a9a9" marker-end="url(#ay)"/>
<path d="M212 158 H190 V238 H160" stroke="#4a8fd8" marker-end="url(#ab)"/>
<path d="M348 158 H370 V238 H400" stroke="#3a3a3a" marker-end="url(#ad)"/>
</g>
<g font-family="Poppins" text-anchor="middle">
<rect x="40" y="18" width="110" height="74" rx="11" fill="#fff" stroke="#e2ded7" stroke-width="1.6"/>
<rect x="80" y="30" width="30" height="20" rx="2.5" fill="#e0a92a"/><path d="M90 30 V50 M100 30 V50 M80 40 H110" stroke="#fff" stroke-width="1.4"/>
<text x="95" y="72" font-size="12.5" font-weight="600" fill="#242424">Paneles</text>
<text x="95" y="110" font-size="10" fill="#9a9a9a" font-family="Lato">generan de día</text>
<rect x="410" y="18" width="110" height="74" rx="11" fill="#fff" stroke="#e2ded7" stroke-width="1.6"/>
<path d="M465 28 L454 52 M465 28 L476 52 M456 40 H474 M452 36 H478" stroke="#a9a9a9" stroke-width="2.2" fill="none"/>
<text x="465" y="72" font-size="12.5" font-weight="600" fill="#242424">{red_nom}</text>
<text x="465" y="110" font-size="10" fill="#9a9a9a" font-family="Lato">{"toma · recibe excedente" if hay_hb else "toma cuando falta"}</text>
<rect x="222" y="108" width="116" height="78" rx="11" fill="#fff" stroke="#e2ded7" stroke-width="1.6"/>
<rect x="268" y="118" width="24" height="30" rx="4" fill="#3a3a3a"/><rect x="273" y="123" width="14" height="7" rx="1.5" fill="#e0a92a"/>
<text x="280" y="170" font-size="12.5" font-weight="600" fill="#242424">Inversor</text>
<text x="280" y="203" font-size="10" fill="#9a9a9a" font-family="Lato">decide el flujo</text>
<rect x="40" y="200" width="110" height="74" rx="11" fill="#fff" stroke="#e2ded7" stroke-width="1.6"/>
<rect x="80" y="213" width="28" height="17" rx="3" fill="none" stroke="#4a8fd8" stroke-width="2.2"/><rect x="108" y="218" width="3" height="7" fill="#4a8fd8"/>
<rect x="84" y="217" width="16" height="9" fill="#4a8fd8"/>
<text x="95" y="254" font-size="12.5" font-weight="600" fill="#242424">Batería</text>
<text x="95" y="292" font-size="10" fill="#9a9a9a" font-family="Lato">carga y descarga</text>
<rect x="410" y="200" width="110" height="74" rx="11" fill="#fff" stroke="#e2ded7" stroke-width="1.6"/>
<path d="M452 222 L465 210 L478 222 V234 H452 Z" fill="none" stroke="#3a3a3a" stroke-width="2.2" stroke-linejoin="round"/>
<rect x="462" y="226" width="6" height="8" fill="#3a3a3a"/>
<text x="465" y="254" font-size="12.5" font-weight="600" fill="#242424">Su casa</text>
<text x="465" y="292" font-size="10" fill="#9a9a9a" font-family="Lato">consumo</text>
</g></svg>"""

    # reserva de respaldo por batería
    grupos = {}
    for a in alts:
        if a["cfg"].get("bateria_kwh"):
            grupos.setdefault(num(a["cfg"]["bateria_kwh"], 2), []).append(a["cfg"]["id"])
    def _ids(xs):
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y la " + xs[-1]
    reserva = "; ".join(f'{k} kWh nominales en la {_ids(v)}' for k, v in grupos.items())

    dia_txt = "Los paneles alimentan primero el consumo de la casa. Si sobra energía, el inversor carga la batería"
    if hay_hb and hay_og:
        dia_txt += (". Con la batería llena, en la híbrida el excedente se inyecta a la red; en las off grid, el inversor "
                    "ajusta la generación a lo que la casa consume.")
    elif hay_hb:
        dia_txt += ", y cuando la batería está llena el excedente se inyecta a la red."
    else:
        dia_txt += "; con la batería llena, el inversor ajusta la generación a lo que la casa consume."
    sit_def = [
        ("De día", dia_txt),
        ("De noche", "La casa toma primero la energía guardada en la batería. Cuando la batería llega a su mínimo, "
                     "el inversor pasa a tomar de la red en forma automática, sin cortes ni intervención."),
        ("Si se corta la luz", "El inversor se desconecta de la red —por seguridad— y sigue alimentando el circuito "
                               "respaldado desde la batería y, de día, desde los paneles. Se puede fijar una reserva que el "
                               f"uso diario no toque, para tenerla siempre disponible: {reserva}." if reserva else
                               "El inversor se desconecta de la red por seguridad."),
        ("Días nublados", "Con poca radiación los paneles siguen generando, aunque menos. El inversor combina lo que "
                          "llega de los paneles con la batería y completa con la red lo que falta. Una batería más grande "
                          "demora el momento en que la casa vuelve a tomar de la red."),
        ("Cargas del circuito de red", "Lo que no está en el circuito respaldado también aprovecha la energía solar "
                                       "mientras haya suministro: el inversor mide su consumo y lo cubre primero con los "
                                       "paneles y la batería. Durante un corte, esas cargas quedan sin alimentación."),
        ("Monitoreo", "Generación, consumo y estado de la batería, en tiempo real desde el celular. Cualquier "
                      "anomalía se ve al instante."),
    ]
    sits = cfg.get("situaciones") or sit_def
    sit_html = "".join(f'<div class="sit"><div class="st">{t}</div><p>{x}</p></div>' for t, x in sits)
    fuentes = ("Las alternativas combinan tres fuentes: los <b>paneles</b>, la <b>batería</b> y la "
               f'<b>red de {con["distribuidora"]}</b>. El inversor es el cerebro del sistema: prioriza siempre la energía '
               "solar, guarda lo que sobra para la noche y recurre a la red sólo cuando hace falta. Todo ocurre en forma "
               "automática, sin que nadie tenga que accionar nada.")
    bloque_funciona = f"""<div class="eyebrow">Cómo funciona</div>
<h2>El inversor decide, en cada momento, de dónde toma la energía</h2>
<p>{doc.get("texto_funciona", fuentes)}</p>
{svg}
<div class="eyebrow" style="margin-top:8px">El orden de prioridades</div>
<h2>Qué hace el sistema en cada situación</h2>
<div class="sits">{sit_html}</div>
<div class="note"><b>La prioridad es siempre la misma:</b> primero el sol, después la batería y por último la red.
Lo que la casa consume de sus propios paneles o de su batería es energía que deja de comprarse.</div>"""

    # ---------- como avanzamos + condiciones ----------
    pasos_def = [
        "Visita técnica al sitio: ubicación de los paneles fuera de las sombras, recorrido del cableado y relevamiento del tablero.",
        "Definición del circuito respaldado y del circuito directo a la red.",
        "Elección de la alternativa y confirmación del presupuesto.",
        "Instalación y puesta en marcha.",
    ]
    pasos = "".join(f"<li>{p}</li>" for p in (cfg.get("proximos_pasos") or pasos_def))
    cond = "".join(f'<tr><td class="b" style="width:26%">{k}</td><td>{v}</td></tr>'
                   for k, v in cfg.get("condiciones", []))
    bloque_avanza = (f'<div style="page-break-inside:avoid"><div class="eyebrow">Cómo avanzamos</div><h2>Los próximos pasos</h2>'
                     f'<ol class="steps">{pasos}</ol></div>'
                     + (f'<hr><div class="eyebrow">Condiciones y alcance</div><h2>Cómo trabajamos</h2><table>{cond}</table>' if cond else ""))

    p_mes = f'{rh}<div class="page">{mes_en_p4}</div>' if mes_en_p4 else ""
    p4 = p_mes + f'{rh}<div class="page">{bloque_funciona}</div>'

    # ---------- pagina 5: presupuestos + financiacion comparada ----------
    presu = ""
    for idx, a in enumerate(alts):
        ac = a["cfg"]
        items = "".join(f'<tr><td class="b">{i[0]}</td><td>{i[1]}</td><td class="c">{i[2]}</td></tr>'
                        for i in ac["items"])
        presu += f'''<div style="page-break-inside:avoid;margin-bottom:8px">
<h3 style="margin-top:6px">Alternativa {ac["id"]} — {ac["nombre"]}{tag_modo(a["modo"])} <span class="muted" style="font-weight:400">· Presup. N° {ac["presupuesto_nro"]}</span></h3>
<table class="presu"><tr><th>Ítem</th><th>Descripción</th><th class="c">Cant.</th></tr>{items}
<tr class="sub"><td></td><td class="r">Subtotal (sin IVA) · IVA</td><td class="c nw">{usd(ac["subtotal_usd"], 1)} · {usd(ac["iva_usd"], 1)}</td></tr>
<tr class="total2"><td></td><td class="r">Total</td><td class="c nw">{usd(ac["total_usd"], 1)}</td></tr></table></div>'''
    mods = []
    for a in alts:
        for r in a["cfg"].get("financiacion", []):
            if r[0] not in mods:
                mods.append(r[0])
    fin_rows = ""
    for m in mods:
        fin_rows += f'<tr><td class="b">{m}</td>'
        for a in alts:
            r = next((x for x in a["cfg"].get("financiacion", []) if x[0] == m), None)
            q = lambda x: str(x).replace("USD", "").strip()
            fin_rows += (f'<td class="r nw">{q(r[1])}</td><td class="r nw">{q(r[2])}</td><td class="r b nw">{q(r[3]) if len(r) > 3 else ""}</td>'
                         if r else '<td></td><td></td><td></td>')
        fin_rows += "</tr>"
    fin_h1 = "".join(f'<th class="c" colspan="3">{a["cfg"]["id"]} · {a["cfg"]["nombre"]}</th>' for a in alts)
    fin_h2 = "".join('<th class="r">anticipo</th><th class="r">cuota</th><th class="r">total</th>' for _ in alts)
    fin_h1 = fin_h1.replace("</th>", "</th>", 1)
    tabla_fin = (f'''<div style="page-break-inside:avoid"><hr><div class="eyebrow">Financiación</div>
<h2>Modalidades de pago <span class="muted" style="font-weight:400">· en USD</span></h2>
<table class="fin"><tr><th rowspan="2">Modalidad</th>{fin_h1}</tr><tr>{fin_h2}</tr>{fin_rows}</table>'''
                 if mods else "")
    nota_fin = doc.get("nota_financiacion", "Valores con IVA incluido. Financiación propia Oriens en dólares oficiales "
                       "(BNA venta), instrumentada mediante contrato de mutuo y pagarés o e-cheqs por cuota.")
    p5 = f'''{rh}<div class="page"><div class="eyebrow">Presupuesto</div>
<h2>Qué incluye cada alternativa</h2>{presu}</div>'''
    bloque_fin = (tabla_fin.replace('<hr>', '', 1) + f'<div class="small">{nota_fin}</div></div><hr>') if mods else ""

    # ---------- pagina 6: fichas + cierre ----------
    fichas = ""
    for f in cfg.get("fichas", []):
        sp = f["specs"]
        rows = ""
        for j in range(0, len(sp), 2):
            par = sp[j:j + 2]
            cells = "".join(f'<td class="k">{k}</td><td class="v">{v}</td>' for k, v in par)
            if len(par) == 1:
                cells += '<td class="k"></td><td class="v"></td>'
            rows += f"<tr>{cells}</tr>"
        img = f'<div class="fimg"><img src="{os.path.join(ASSETS, f["img"])}"></div>' if f.get("img") else ""
        fichas += f'''<div class="{"ficha" if f.get("img") else "ficha noimg"}" style="page-break-inside:avoid">{img}<div class="fbody">
<div class="fcat">{f["cat"]}</div><div class="fname">{f["name"]}</div>
<div class="fsub">{f.get("sub", "")}</div><table class="ft">{rows}</table></div></div>'''
    p_fichas = f'''{rh}<div class="page"><div class="eyebrow">Ficha técnica · componentes</div>
<h2>Los productos de su central</h2>
<p>Equipos de primeras marcas, con garantía oficial. Estas son sus especificaciones.</p>
{fichas}</div>'''
    cierre = (f'<div class="close"><div class="t">{doc.get("frase_cierre", "Empezá a controlar tu energía.")}</div>'
              + (f'<div class="c">{doc["cierre"]}</div>' if doc.get("cierre") else "") + '</div>'
              if doc.get("mostrar_cierre", False) else "")
    p6 = f'''{rh}<div class="page">{bloque_fin}{bloque_avanza}{cierre}</div>'''

    marca = (f'<div class="borrador">{doc["borrador"] if isinstance(doc["borrador"], str) else "BORRADOR"}</div>'
             if doc.get("borrador") else "")
    return ("<!doctype html><html><head><meta charset='utf-8'></head><body>"
            f"{marca}{p1}{p2}{p3}{p4}{p_fichas}{p5}{p6}</body></html>")


def imprimir(cfg, d):
    print(f'Factura actual: {ars(d["fsa"])}/año ({ars(d["fsm"])}/mes) · consumo {num(d["cons_anual"])} kWh/año')
    print(f'Precio de inyección (50% promedio tramos, sin impuestos): {ars(d["p_iny"], 2)}/kWh')
    for a in d["alts"]:
        r1, r2 = a["r1"], a["r2"]
        print(f'\n[{a["cfg"]["id"]}] {a["cfg"]["nombre"]} · {a["modo"]} · {a["paneles"]} paneles ({num(a["kwp"], 2)} kWp)')
        print(f'  gen {num(r1["gen"])} · directo {num(r1["directo"])} · batería {num(r1["bateria"])} · '
              f'red {num(r1["red"])} · inyectado {num(r1["iny"])} · perdido {num(r1["perdido"])} kWh')
        print(f'  cobertura {pct(a["cobertura"], 1)} · factura año1 {ars(a["fact1"])} · ahorro año1 {ars(a["ahorro1"])}')
        if a["modo"] == HB:
            print(f'  régimen c/inyección: factura {ars(a["fact2"])} · ahorro {ars(a["ahorro2"])} · '
                  f'crédito sin usar {ars(a["credito_muerto"])}/año')
        print(f'  inversión {usd(a["inversion"])} · repago {anios_meses(a["repago"])} · ahorro {d["horizonte"]} años {usd(a["acum"])}')
    avisos = chequeos(cfg, d)
    if avisos:
        print("\nAVISOS PARA EL ASESOR:")
        for x in avisos:
            print("  ⚠ " + x)


def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    d = calcular(cfg)
    imprimir(cfg, d)
    if "--solo-calculo" in sys.argv:
        return
    from weasyprint import HTML, CSS
    out = sys.argv[2] if len(sys.argv) > 2 else "propuesta.pdf"
    pie = f'ORIENS ENERGÍA SOLAR · Propuesta para {cfg["cliente"]["nombre"]}'
    css = open(os.path.join(HERE, "_style_mixta.css"), encoding="utf-8").read().replace("var(--pie)", f'"{pie}"')
    HTML(string=render(cfg, d), base_url=HERE).write_pdf(out, stylesheets=[CSS(string=css)])
    print(f"\nOK → {out}")


if __name__ == "__main__":
    main()
