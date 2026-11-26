import datetime
import re
from io import BytesIO
import textwrap
import unicodedata
from urllib.parse import quote, urljoin, urlparse

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Cadena de Valor", page_icon="⛓️", layout="wide")

COLORES = {"Logística interna": "#1f77b4", "Operaciones (producción)": "#ff7f0e",
           "Logística externa": "#2ca02c", "Marketing y ventas": "#9467bd", "Servicios": "#d62728"}
NIVEL_COL = {"Fortaleza": "#2e9e5b", "Aceptable": "#e8a317", "Debilidad": "#d64545"}

# (criterio, puntaje_base, indicador, solución, palabras clave para el análisis en línea)
DATOS = {
    "Logística interna": [
        ("Abastecimiento de materia prima", 3, "% de insumos recibidos dentro de especificación",
         "Contratos de largo plazo con proveedores, precio por calidad y asistencia técnica.",
         ["proveedor", "materia prima", "insumo", "abastecimiento", "compra", "acopio", "supplier"]),
        ("Almacenamiento y cadena de frío", 3, "% de lotes rechazados o mermados",
         "Monitoreo con sensores, registros digitales y almacenes adecuados.",
         ["almacen", "bodega", "cadena de frio", "refriger", "inventario", "warehouse"]),
        ("Control de inventarios", 3, "Rotación de inventario y % de mermas",
         "Aplicar PEPS/FEFO, clasificación ABC y punto de reorden.",
         ["stock", "inventario", "rotacion", "reposicion", "erp"]),
        ("Gestión de proveedores", 3, "Entregas a tiempo (OTIF)",
         "Scorecard trimestral de proveedores y proveedores alternos.",
         ["homologacion", "alianza", "proveedores", "socios", "aliados", "convenio"]),
    ],
    "Operaciones (producción)": [
        ("Capacidad y eficiencia de planta", 3, "OEE = disponibilidad × rendimiento × calidad",
         "Implementar SMED, TPM y tablero de OEE por línea.",
         ["planta", "produccion", "fabrica", "capacidad", "manufactura", "proceso", "linea de"]),
        ("Calidad e inocuidad", 3, "% de reclamos por calidad",
         "Certificaciones (ISO, HACCP, BPM) y mejora continua.",
         ["calidad", "iso", "haccp", "bpm", "certificacion", "inocuidad", "norma"]),
        ("Mantenimiento y tecnología", 3, "MTBF, MTTR y % de mantenimiento preventivo",
         "Plan preventivo y predictivo, repuestos críticos y capacitación.",
         ["tecnologia", "maquinaria", "equipos", "automatiz", "mantenimiento", "innovacion"]),
        ("Gestión ambiental y mermas", 3, "kWh o agua por unidad producida",
         "Metas de eficiencia energética, reciclaje y reducción de residuos.",
         ["ambiental", "sostenib", "residuos", "reciclaj", "energia", "huella", "ecologic"]),
    ],
    "Logística externa": [
        ("Cobertura de distribución", 3, "% de puntos de venta atendidos",
         "Distribuidores locales y preventa móvil en zonas de baja cobertura.",
         ["distribu", "cobertura", "nacional", "sucursal", "tiendas", "puntos de venta", "sedes"]),
        ("Entrega y nivel de servicio", 3, "Pedidos completos y a tiempo (OTIF)",
         "Pronóstico colaborativo de demanda y stock de seguridad por SKU.",
         ["delivery", "entrega", "despacho", "envio", "reparto", "flota", "transporte"]),
        ("Costo y rutas logísticas", 3, "Costo logístico como % de ventas",
         "Software de ruteo (TMS), consolidación de carga y costo por ruta.",
         ["logistica", "ruta", "flota", "camion", "courier", "operador logistico"]),
        ("Trazabilidad y devoluciones", 3, "% de devoluciones y tiempo de respuesta",
         "Código QR por lote y gestión de devoluciones con causa raíz.",
         ["trazabilidad", "seguimiento", "devolucion", "tracking", "garantia de entrega"]),
    ],
    "Marketing y ventas": [
        ("Posicionamiento de marca", 3, "Recordación de marca (top of mind)",
         "Reforzar propuesta de valor y diferenciación.",
         ["marca", "lider", "años de", "trayectoria", "reconoc", "premio", "confianza"]),
        ("Precios y promociones", 3, "Margen por canal y elasticidad precio",
         "Segmentar precios por canal y evaluar el ROI de promociones.",
         ["precio", "oferta", "promocion", "descuento", "cupon", "combo", "%"]),
        ("Canales digitales", 3, "% de ventas online y costo de adquisición",
         "E-commerce, redes sociales y CRM con datos de compra.",
         ["tienda online", "comprar", "carrito", "facebook", "instagram", "tiktok", "whatsapp", "linkedin", "e-commerce"]),
        ("Fuerza de ventas y clientes", 3, "Ventas por vendedor y cumplimiento de cuota",
         "Comisiones por mix y rentabilidad, y capacitación comercial.",
         ["ventas", "cotiza", "clientes", "mayorista", "corporativ", "asesor comercial", "distribuidor"]),
    ],
    "Servicios": [
        ("Atención y reclamos", 3, "Tiempo promedio de resolución",
         "Canal único omnicanal con meta de resolución en 48 horas.",
         ["contacto", "reclamo", "libro de reclamaciones", "atencion al cliente", "soporte", "telefono", "correo"]),
        ("Asesoría y soporte técnico", 3, "Visitas o consultas efectivas por cliente",
         "Programa de acompañamiento y capacitación al cliente.",
         ["asesoria", "capacitacion", "consultoria", "soporte tecnico", "instalacion", "mantenimiento"]),
        ("Garantía y posventa", 3, "% de reposiciones en plazo",
         "Reposición ágil y registro digital de incidencias.",
         ["garantia", "posventa", "post venta", "reposicion", "cambio", "devolucion"]),
        ("Satisfacción y fidelización", 3, "NPS y tasa de recompra",
         "Encuesta NPS trimestral y programa de lealtad.",
         ["testimonio", "opiniones", "fidelizacion", "puntos", "club", "suscripcion", "satisfaccion", "reseñas"]),
    ],
}

PAGINAS_UTILES = ["nosotros", "quienes", "about", "producto", "servicio", "contacto", "tienda",
                  "sostenib", "calidad", "distribu", "empresa"]


def quitar_tildes(t):
    return "".join(unicodedata.normalize("NFD", c)[0] for c in t).lower()


def nivel(p):
    return "Fortaleza" if p >= 4 else "Aceptable" if p >= 3 else "Debilidad"


@st.cache_data(show_spinner=False, ttl=3600)
def descargar(url):
    h = {"User-Agent": "Mozilla/5.0 (compatible; AnalizadorCadenaValor/1.0)"}
    r = requests.get(url, headers=h, timeout=12)
    r.raise_for_status()
    return r.text


def texto_de(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style", "noscript"]):
        t.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ")), s


GENERICAS = {"inicio", "home", "bienvenido", "bienvenidos", "welcome", "pagina principal", "sitio oficial",
             "oficial", "index", "portada", "tienda online", "web oficial"}


def limpiar_nombre(site, titulo, url):
    """Detecta el nombre de la empresa a partir del sitio (og:site_name, título o dominio)."""
    host = urlparse(url).netloc.lower().replace("www.", "")
    base = host.split(".")[0]
    def limpio(t):
        return t.strip(" -–—|·•:")
    if site and quitar_tildes(limpio(site)) not in GENERICAS:
        return limpio(site)[:60]
    partes = [limpio(x) for x in re.split(r"\s+[|\-–—·•:]\s+|\s*\|\s*", titulo or "")]
    partes = [x for x in partes if x and quitar_tildes(x) not in GENERICAS]
    for x in partes:
        if base and base in quitar_tildes(x).replace(" ", ""):
            return x[:60]
    if partes:
        return (min(partes, key=len) if len(partes) > 1 else partes[0])[:60]
    return base.replace("-", " ").title()


def sacar_info(sopa, url):
    def meta(*nombres):
        for n in nombres:
            t = sopa.find("meta", attrs={"property": n}) or sopa.find("meta", attrs={"name": n})
            if t and t.get("content"):
                return t["content"].strip()
        return ""
    site = meta("og:site_name", "application-name")
    titulo = meta("og:title") or (sopa.title.string.strip() if sopa.title and sopa.title.string else "")
    nombre = limpiar_nombre(site, titulo, url)
    desc = meta("og:description", "description", "twitter:description")
    c = []
    for n in ("og:image", "twitter:image"):
        v = meta(n)
        if v:
            c.append(urljoin(url, v))
    for rel in ("apple-touch-icon", "icon", "shortcut icon"):
        t = sopa.find("link", rel=lambda r: r and rel in " ".join(r).lower() if isinstance(r, list) else r and rel in r.lower())
        if t and t.get("href"):
            c.append(urljoin(url, t["href"]))
    for im in sopa.find_all("img", src=True)[:40]:
        if "logo" in (im["src"] + " ".join(im.get("class", [])) + (im.get("alt") or "")).lower():
            c.append(urljoin(url, im["src"]))
            break
    c.append(urljoin(url, "/favicon.ico"))
    return titulo, desc[:300], c, nombre


def bajar_imagen(cands):
    from io import BytesIO
    from PIL import Image
    for u in cands:
        if u.lower().split("?")[0].endswith(".svg"):
            continue
        try:
            r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200 and 100 < len(r.content) < 4_000_000:
                Image.open(BytesIO(r.content)).verify()
                return r.content
        except Exception:
            continue
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def leer_sitio(url, max_paginas=5):
    html = descargar(url)
    texto, sopa = texto_de(html)
    titulo, desc, cands, nombre = sacar_info(sopa, url)
    info = {"titulo": titulo, "desc": desc, "nombre": nombre, "url": url}
    visitadas, base = [url], urlparse(url).netloc
    for a in sopa.find_all("a", href=True):
        if len(visitadas) >= max_paginas:
            break
        l = urljoin(url, a["href"]).split("#")[0]
        if urlparse(l).netloc == base and l not in visitadas and any(k in l.lower() for k in PAGINAS_UTILES):
            try:
                texto += " " + texto_de(descargar(l))[0]
                visitadas.append(l)
            except Exception:
                pass
    return texto, visitadas, info


def analizar_texto(texto):
    """Devuelve {(actividad, criterio): (puntaje, nº de menciones, fragmento)}"""
    norm = quitar_tildes(texto)
    res = {}
    for act, items in DATOS.items():
        for crit, _, _, _, claves in items:
            hits, frag = 0, ""
            for k in claves:
                k2 = quitar_tildes(k)
                n = norm.count(k2)
                hits += n
                if n and not frag:
                    i = norm.find(k2)
                    frag = "…" + texto[max(0, i - 70): i + 110].strip() + "…"
            p = 2 if hits == 0 else 3 if hits <= 2 else 4 if hits <= 6 else 5
            res[(act, crit)] = (p, hits, frag)
    return res



def cadena_html(prom):
    cs = ""
    for i, (a, p) in enumerate(prom.items()):
        cs += (f"<div class='chev' style='background:{COLORES[a]}'><div class='n'>{i+1}</div>"
               f"<div class='t'>{a}</div><div class='p'>{p:.1f}<small>/5</small></div></div>")
    return ("<style>.cadena{display:flex;gap:0;margin:8px 0 18px;overflow-x:auto}"
            ".chev{flex:1;min-width:150px;color:#fff;padding:14px 26px 14px 34px;"
            "clip-path:polygon(0 0,88% 0,100% 50%,88% 100%,0 100%,12% 50%);margin-right:-14px;text-align:center}"
            ".chev .n{font-size:12px;opacity:.85}.chev .t{font-weight:700;font-size:14px;line-height:1.2}"
            ".chev .p{font-size:26px;font-weight:800}.chev small{font-size:13px;font-weight:500}"
            ".hero{background:linear-gradient(120deg,#0f6e56,#1f77b4 55%,#9467bd);color:#fff;border-radius:16px;"
            "padding:20px 26px;margin-bottom:10px}.hero h1{color:#fff;margin:0;font-size:30px}"
            ".hero p{margin:4px 0 0;opacity:.92}</style><div class='cadena'>" + cs + "</div>")


# ---------- Interfaz ----------
st.markdown("<style>.hero{background:linear-gradient(120deg,#0f6e56,#1f77b4 55%,#9467bd);color:#fff;border-radius:16px;"
            "padding:20px 26px;margin-bottom:10px}.hero h1{color:#fff;margin:0;font-size:30px}.hero p{margin:4px 0 0;opacity:.92}</style>"
            "<div class='hero'><h1>⛓️ Analizador de Cadena de Valor</h1>"
            "<p>Actividades primarias · Modelo de Porter · análisis manual o en línea desde el sitio web de la empresa</p></div>",
            unsafe_allow_html=True)
banner = st.container()
ficha = st.container()

for act, items in DATOS.items():
    for crit, base, *_ in items:
        st.session_state.setdefault(f"{act}|{crit}", base)

with st.sidebar:
    st.header("Análisis en línea")
    url = st.text_input("Link de la empresa", placeholder="https://www.empresa.com")
    if st.button("🔎 Analizar sitio web", width="stretch"):
        if not url.strip():
            st.warning("Escribe un link.")
        else:
            if not url.startswith("http"):
                url = "https://" + url.strip()
            try:
                with st.spinner("Leyendo el sitio..."):
                    texto, paginas, info = leer_sitio(url)
                r = analizar_texto(texto)
                for (act, crit), (p, _, _) in r.items():
                    st.session_state[f"{act}|{crit}"] = p
                st.session_state["evid"] = r
                st.session_state["paginas"] = paginas
                st.session_state["info"] = info
                st.session_state["empresa_nombre"] = info["nombre"]
                st.success(f"Se leyeron {len(paginas)} página(s).")
            except Exception as e:
                st.error(f"No se pudo leer el sitio: {e}")
    empresa = st.text_input("Empresa detectada (editable)", key="empresa_nombre",
                            placeholder="Se detecta sola al analizar el link").strip() or "Empresa analizada"
    if st.button("↺ Restablecer caso base", width="stretch"):
        for act, items in DATOS.items():
            for crit, base, *_ in items:
                st.session_state[f"{act}|{crit}"] = base
        st.session_state.pop("evid", None)
    st.info("El análisis en línea cuenta menciones de palabras clave en el sitio. "
            "Es una **estimación inicial**: ajusta los puntajes con los deslizadores usando datos reales.")
    if "paginas" in st.session_state:
        with st.expander("Páginas analizadas"):
            for p in st.session_state["paginas"]:
                st.write(p)

with ficha:
    inf = st.session_state.get("info")
    if inf:
        st.subheader(inf["nombre"] or empresa)
        if inf["desc"]:
            st.write(inf["desc"])

LAB1 = {1: "🔴 Crítico", 2: "🟠 Bajo", 3: "🟡 Medio", 4: "🟢 Alto", 5: "💚 Excelente"}
LAB2 = {1: "😟", 2: "😕", 3: "😐", 4: "🙂", 5: "🤩"}
LAB4 = {1: "Invisible", 2: "Débil", 3: "Estable", 4: "Fuerte", 5: "Líder"}
LAB5 = {i: "★" * i + "☆" * (5 - i) for i in range(1, 6)}
filas = []


def wrap(t, n=14):
    return textwrap.fill(t, n).replace("\n", "<br>")


def banner_act(act, icono, frase):
    c = COLORES[act]
    st.markdown(f"<div style='background:{c}22;border-left:6px solid {c};border-radius:12px;padding:10px 16px;margin-bottom:10px'>"
                f"<span style='font-size:26px'>{icono}</span> <b style='color:{c};font-size:18px'>{act}</b>"
                f"<div style='opacity:.85'>{frase}</div></div>", unsafe_allow_html=True)


def card(act, crit, p, sol):
    lv = nivel(p)
    st.markdown(f"<div style='border-left:5px solid {NIVEL_COL[lv]};padding:6px 12px;background:{NIVEL_COL[lv]}18;"
                f"border-radius:6px;margin-bottom:6px'><b>{crit}</b> · <b style='color:{NIVEL_COL[lv]}'>{lv}</b><br>"
                f"<b>{'Solución propuesta' if p <= 3 else 'Para mantener'}:</b> {sol}</div>", unsafe_allow_html=True)
    ev = st.session_state.get("evid", {}).get((act, crit))
    if ev and ev[2]:
        st.caption(f"Evidencia en el sitio ({ev[1]} menciones): {ev[2]}")


def registrar(act, items, ps):
    for (crit, _, _, sol, _), p in zip(items, ps):
        filas.append({"Actividad": act, "Criterio": crit, "Puntaje": p, "Nivel": nivel(p), "Acción": sol})


def leer(texto):
    st.info("**Cómo leer esta gráfica:** " + texto)


def soluciones(act, items, ps):
    with st.expander("Ver soluciones por criterio"):
        for (crit, _, _, sol, _), p in zip(items, ps):
            card(act, crit, p, sol)
    registrar(act, items, ps)


def tab_interna(act, items):
    banner_act(act, "🚚", "Regla de esta actividad: <b>una cadena se rompe en su punto más débil (cuello de botella)</b>.")
    ps = []
    for c, (crit, _, kpi, _, _) in zip(st.columns(4), items):
        with c:
            ps.append(st.select_slider(crit, [1, 2, 3, 4, 5], key=f"{act}|{crit}", format_func=lambda x: LAB1[x]))
            st.caption(kpi)
    mn = min(ps)
    k = ps.index(mn)
    if mn <= 3:
        st.warning(f"El insumo fluye bien en otros tramos, pero se frena en **{items[k][0]}** ({mn}/5). Mientras no se corrija, el resto de la cadena espera.")
    else:
        st.success("Flujo continuo: no hay cuellos de botella en el abastecimiento.")
    soluciones(act, items, ps)


def tab_operaciones(act, items):
    banner_act(act, "🏭", "Regla de esta actividad: <b>la eficiencia se multiplica</b>; una sola falla arrastra a toda la planta.")
    ps = []
    for row in (st.columns(2), st.columns(2)):
        for c in row:
            crit, _, kpi, _, _ = items[len(ps)]
            with c:
                ps.append(st.radio(crit, [1, 2, 3, 4, 5], key=f"{act}|{crit}", horizontal=True, format_func=lambda x: LAB2[x]))
                st.caption(kpi)
    oee = 100.0
    for p in ps:
        oee *= p / 5
    m1, m2 = st.columns([1, 3])
    m1.metric("Eficiencia estimada de planta", f"{oee:.0f}%")
    m2.progress(min(int(oee), 100))
    if oee < 50:
        st.error(f"De cada 100 unidades programadas, solo unas **{oee:.0f}** salen bien y a tiempo: las pérdidas son altas.")
    elif oee < 75:
        st.warning(f"De cada 100 unidades programadas, unas **{oee:.0f}** salen bien y a tiempo: hay margen de mejora.")
    else:
        st.success(f"De cada 100 unidades programadas, unas **{oee:.0f}** salen bien y a tiempo: planta eficiente.")
    soluciones(act, items, ps)


def tab_externa(act, items):
    banner_act(act, "📦", "Regla de esta actividad: <b>equilibrar servicio al cliente y eficiencia de costos</b>.")
    izq, der = st.columns([2, 3])
    ps = []
    with izq:
        for crit, _, kpi, _, _ in items:
            ps.append(st.number_input(crit, 1, 5, step=1, key=f"{act}|{crit}"))
            st.caption(kpi)
    serv = (ps[0] + ps[1]) / 2
    efi = (ps[2] + ps[3]) / 2
    if serv >= 3 and efi >= 3:
        cuad = "⭐ Estrella: buen servicio con costos controlados"
    elif serv >= 3:
        cuad = "💸 Buen servicio, pero caro"
    elif efi >= 3:
        cuad = "🐢 Económico, pero con servicio limitado"
    else:
        cuad = "🚨 Crítico: servicio débil y costos altos"
    with der:
        m1, m2 = st.columns(2)
        m1.metric("Servicio al cliente", f"{serv:.1f} / 5")
        m2.metric("Eficiencia de costos", f"{efi:.1f} / 5")
        st.info(f"Diagnóstico: **{cuad}**")
    soluciones(act, items, ps)


def tab_marketing(act, items):
    banner_act(act, "📣", "Regla de esta actividad: <b>de cada 1 000 personas alcanzadas, ¿cuántas terminan comprando?</b>")
    izq, der = st.columns([2, 3])
    ps = []
    with izq:
        for crit, _, kpi, _, _ in items:
            ps.append(st.select_slider(crit, [1, 2, 3, 4, 5], key=f"{act}|{crit}", format_func=lambda x: LAB4[x]))
            st.caption(kpi)
    comp = 1000.0
    for p in ps:
        comp *= 0.3 + 0.1 * (p - 1)
    k = ps.index(min(ps))
    with der:
        st.metric("Compradores por cada 1 000 personas", f"{comp:.0f}")
        st.warning(f"De 1 000 personas, unas **{comp:.0f}** compran. La mayor fuga está en **{items[k][0]}** ({LAB4[ps[k]]}). (Simulación orientativa.)")
    soluciones(act, items, ps)


def tab_servicios(act, items):
    banner_act(act, "🤝", "Regla de esta actividad: <b>cada falla en el servicio le resta puntos a la satisfacción del cliente</b>.")
    ps = []
    for c, (crit, _, kpi, _, _) in zip(st.columns(4), items):
        with c:
            ps.append(st.radio(crit, [1, 2, 3, 4, 5], key=f"{act}|{crit}", format_func=lambda x: LAB5[x]))
            st.caption(kpi)
    perdidas = [(5 - p) * 5 for p in ps]
    final = 100 - sum(perdidas)
    st.metric("Satisfacción estimada del cliente", f"{final} / 100")
    k = perdidas.index(max(perdidas))
    if max(perdidas) > 0:
        st.warning(f"La mayor pérdida de satisfacción viene de **{items[k][0]}** (-{perdidas[k]} puntos).")
    else:
        st.success("Satisfacción estimada: 100 de 100.")
    soluciones(act, items, ps)


FUNC = [tab_interna, tab_operaciones, tab_externa, tab_marketing, tab_servicios]
tabs = st.tabs([f"{i+1}. {k}" for i, k in enumerate(DATOS)])
for tab, f, (act, items) in zip(tabs, FUNC, DATOS.items()):
    with tab:
        f(act, items)

df = pd.DataFrame(filas)
prom = df.groupby("Actividad", sort=False)["Puntaje"].mean()
glob = df["Puntaje"].mean()
with banner:
    st.markdown(cadena_html(prom), unsafe_allow_html=True)

st.divider()
st.header(f"📊 Dashboard · {empresa}")

lvg = nivel(glob)
conteo = df["Nivel"].value_counts().reindex(["Fortaleza", "Aceptable", "Debilidad"]).fillna(0).astype(int)
def tarjeta(titulo, valor, sub, color):
    return (f"<div style='flex:1;min-width:170px;background:{color}1a;border-left:6px solid {color};"
            f"border-radius:12px;padding:12px 16px'><div style='font-size:12px;opacity:.75'>{titulo}</div>"
            f"<div style='font-size:28px;font-weight:800;color:{color}'>{valor}</div>"
            f"<div style='font-size:12px;opacity:.8'>{sub}</div></div>")
st.markdown("<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px'>"
            + tarjeta("Puntaje global", f"{glob:.2f} / 5", lvg, NIVEL_COL[lvg])
            + tarjeta("Mejor actividad", f"{prom.max():.1f}", prom.idxmax(), "#2e9e5b")
            + tarjeta("Actividad crítica", f"{prom.min():.1f}", prom.idxmin(), "#d64545")
            + tarjeta("Fortalezas / Debilidades", f"{conteo['Fortaleza']} / {conteo['Debilidad']}",
                      f"de {len(df)} criterios evaluados", "#1f77b4") + "</div>", unsafe_allow_html=True)

f1, f2 = st.columns(2)
with f1:
    radar = go.Figure(go.Scatterpolar(r=list(prom) + [prom.iloc[0]], theta=list(prom.index) + [prom.index[0]],
                                      fill="toself", line=dict(color="#0f6e56", width=3),
                                      fillcolor="rgba(15,110,86,0.25)"))
    radar.update_layout(title="Radar por actividad", polar=dict(radialaxis=dict(range=[0, 5])),
                        showlegend=False, height=400, margin=dict(t=60, b=20))
    st.plotly_chart(radar, width="stretch")
with f2:
    ids = [empresa] + list(DATOS) + list(df["Criterio"])
    pars = [""] + [empresa] * 5 + list(df["Actividad"])
    vals = [df["Puntaje"].sum()] + [df[df["Actividad"] == a]["Puntaje"].sum() for a in DATOS] + list(df["Puntaje"])
    cols = ["#37474f"] + [COLORES[a] for a in DATOS] + [NIVEL_COL[n] for n in df["Nivel"]]
    sol = go.Figure(go.Sunburst(labels=ids, parents=pars, values=vals, branchvalues="total",
                                marker=dict(colors=cols, line=dict(color="white", width=2)),
                                insidetextorientation="radial"))
    sol.update_layout(title="Cadena completa (anillo exterior = nivel)", height=400, margin=dict(t=60, b=10))
    st.plotly_chart(sol, width="stretch")

f3, f4 = st.columns([3, 2])
with f3:
    mat = [df[df["Actividad"] == a]["Puntaje"].tolist() for a in DATOS]
    nom = [df[df["Actividad"] == a]["Criterio"].tolist() for a in DATOS]
    heat = go.Figure(go.Heatmap(z=mat, x=["Criterio 1", "Criterio 2", "Criterio 3", "Criterio 4"], y=list(DATOS),
                                text=mat, texttemplate="<b>%{text}</b>", customdata=nom,
                                hovertemplate="%{customdata}: %{z}/5<extra></extra>", zmin=1, zmax=5, xgap=4, ygap=4,
                                colorscale=[[0, "#d64545"], [0.5, "#e8a317"], [1, "#2e9e5b"]], showscale=False))
    heat.update_layout(title="Mapa de calor: actividad × criterio", height=380, margin=dict(t=60, b=20),
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(heat, width="stretch")
with f4:
    don = go.Figure(go.Pie(labels=list(conteo.index), values=list(conteo.values), hole=0.62, sort=False,
                           marker=dict(colors=[NIVEL_COL[n] for n in conteo.index], line=dict(color="white", width=3)),
                           textinfo="label+value"))
    don.update_layout(title="Distribución de niveles", height=380, margin=dict(t=60, b=20), showlegend=False,
                      annotations=[dict(text=f"<b>{glob:.1f}</b><br>global", x=0.5, y=0.5, font_size=24, showarrow=False)])
    st.plotly_chart(don, width="stretch")

d = df.sort_values("Puntaje")
rank = go.Figure(go.Bar(x=d["Puntaje"], y=d["Criterio"], orientation="h",
                        marker_color=[NIVEL_COL[n] for n in d["Nivel"]], text=d["Puntaje"], textposition="outside"))
rank.update_layout(title="Ranking de criterios (rojo = prioridad de mejora)", height=560,
                   xaxis=dict(range=[0, 5.5]), margin=dict(t=60, b=20))
st.plotly_chart(rank, width="stretch")

st.subheader("Plan de acción priorizado (puntaje ≤ 3)")
filtro = st.multiselect("Filtrar por actividad", list(DATOS), default=list(DATOS))
plan = df[(df["Puntaje"] <= 3) & (df["Actividad"].isin(filtro))].sort_values("Puntaje")
st.dataframe(plan[["Actividad", "Criterio", "Puntaje", "Acción"]], width="stretch", hide_index=True)
st.download_button("⬇ Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                   "cadena_valor.csv", "text/csv")

# ---------- Flujo de caja ----------
st.divider()
st.header(f"💰 Flujo de caja · {empresa}")
st.info("Los sitios web casi nunca publican su flujo de caja. Esta es una **proyección a 12 meses con supuestos editables** "
        "(valores referenciales). Si la empresa publica estados financieros (por ejemplo en la SMV), escribe aquí sus cifras reales.")
slug = re.sub(r"\W+", "-", empresa.lower()).strip("-") or "empresa"
IN0 = [("Ventas de productos o servicios", 90.0), ("Otros ingresos", 10.0)]
EG0 = [("Materia prima e insumos", "Logística interna", 38.0), ("Mano de obra y planta", "Operaciones (producción)", 18.0),
       ("Distribución y transporte", "Logística externa", 7.0), ("Marketing y ventas", "Marketing y ventas", 6.0),
       ("Servicio y posventa", "Servicios", 2.0), ("Gastos administrativos", "Apoyo", 8.0)]
c1, c2, c3, c4 = st.columns(4)
base = c1.number_input("Ingreso mensual inicial (S/)", 0.0, value=100000.0, step=5000.0, key=f"{slug}|base")
crec = c2.number_input("Crecimiento mensual (%)", -20.0, 50.0, 1.5, 0.5, key=f"{slug}|g")
caja0 = c3.number_input("Saldo inicial de caja (S/)", 0.0, value=50000.0, step=5000.0, key=f"{slug}|caja0")
ajuste = c4.toggle("Ajustar costos según la evaluación", True, key=f"{slug}|aj",
                   help="Si una actividad de la cadena de valor tiene puntaje bajo, sus costos suben (hasta +10% por punto bajo 3).")
e1, e2 = st.columns([2, 3])
ing_df = e1.data_editor(pd.DataFrame(IN0, columns=["Ingreso", "% del total"]), key=f"{slug}|ing",
                        hide_index=True, disabled=["Ingreso"], width="stretch")
eg_df = e2.data_editor(pd.DataFrame(EG0, columns=["Egreso", "Actividad", "% de ingresos"]), key=f"{slug}|eg",
                       hide_index=True, disabled=["Egreso", "Actividad"], width="stretch")

TASA = 0.295
meses = [f"Mes {i}" for i in range(1, 13)]
ing_tot = [base * (1 + crec / 100) ** t for t in range(12)]
pesos = ing_df["% del total"].fillna(0).clip(lower=0)
pesos = pesos / pesos.sum() if pesos.sum() > 0 else pesos
cf = pd.DataFrame({"Mes": meses})
for nom, w_ in zip(ing_df["Ingreso"], pesos):
    cf[nom] = [x * w_ for x in ing_tot]
cf["Total ingresos"] = ing_tot
egr_act = {}
for _, r in eg_df.iterrows():
    f_ = 1 + (3 - prom.get(r["Actividad"], 3)) * 0.05 if ajuste and r["Actividad"] in prom.index else 1.0
    cf[r["Egreso"]] = [x * max(r["% de ingresos"], 0) / 100 * f_ for x in ing_tot]
    egr_act[r["Actividad"]] = egr_act.get(r["Actividad"], 0) + cf[r["Egreso"]].sum()
cols_eg = list(eg_df["Egreso"])
cf["Egresos operativos"] = cf[cols_eg].sum(axis=1)
cf["Impuesto a la renta (29.5%)"] = (cf["Total ingresos"] - cf["Egresos operativos"]).clip(lower=0) * TASA
cf["Flujo neto"] = cf["Total ingresos"] - cf["Egresos operativos"] - cf["Impuesto a la renta (29.5%)"]
cf["Saldo de caja"] = caja0 + cf["Flujo neto"].cumsum()
cf = cf.round(2)
tot = cf.drop(columns=["Mes", "Saldo de caja"]).sum().round(2)
cf_tot = pd.concat([cf, pd.DataFrame([{"Mes": "TOTAL AÑO", **tot.to_dict(), "Saldo de caja": cf["Saldo de caja"].iloc[-1]}])],
                   ignore_index=True)
egr_total = tot["Egresos operativos"] + tot["Impuesto a la renta (29.5%)"]
margen = tot["Flujo neto"] / tot["Total ingresos"] * 100 if tot["Total ingresos"] else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingresos del año", f"S/ {tot['Total ingresos']:,.0f}")
k2.metric("Egresos del año (con impuesto)", f"S/ {egr_total:,.0f}")
k3.metric("Flujo neto del año", f"S/ {tot['Flujo neto']:,.0f}")
k4.metric("Margen neto", f"{margen:.1f}%")

fig = go.Figure()
fig.add_bar(x=meses, y=cf["Total ingresos"], name="Ingresos", marker_color="#2e9e5b")
fig.add_bar(x=meses, y=cf["Egresos operativos"] + cf["Impuesto a la renta (29.5%)"], name="Egresos", marker_color="#d64545")
fig.add_scatter(x=meses, y=cf["Saldo de caja"], name="Saldo de caja", yaxis="y2", line=dict(color="#1f77b4", width=3))
fig.update_layout(title="Ingresos, egresos y saldo de caja por mes", barmode="group", height=400, margin=dict(t=60, b=20),
                  yaxis=dict(title="S/ por mes"), yaxis2=dict(overlaying="y", side="right", title="Saldo (S/)", showgrid=False),
                  legend=dict(orientation="h"))
st.plotly_chart(fig, width="stretch")
if (cf["Flujo neto"] < 0).any():
    st.warning("Hay meses con flujo neto negativo: revisa los costos de la actividad con menor puntaje.")
if egr_act and ajuste:
    st.caption(f"Actividad con menor puntaje: **{prom.idxmin()}** ({prom.min():.1f}). Mejorarla reduce sus costos en esta proyección.")
st.dataframe(cf_tot.style.format({c: "{:,.0f}" for c in cf_tot.columns if c != "Mes"}), width="stretch", hide_index=True)

# ---------- Informes descargables ----------
hoy = datetime.date.today().strftime("%d/%m/%Y")
plan_full = df[df["Puntaje"] <= 3].sort_values("Puntaje")
resumen = pd.DataFrame({"Concepto": ["Empresa", "Fecha", "Puntaje global (1-5)", "Ingresos del año (S/)", "Egresos del año con impuesto (S/)",
                                     "Flujo neto del año (S/)", "Margen neto (%)", "Saldo inicial de caja (S/)", "Crecimiento mensual (%)"],
                        "Valor": [empresa, hoy, round(glob, 2), round(tot["Total ingresos"], 2), round(egr_total, 2),
                                  round(tot["Flujo neto"], 2), round(margen, 1), caja0, crec]})


def excel_bytes():
    from openpyxl.styles import Font
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        df.to_excel(w, sheet_name="Evaluación", index=False)
        plan_full[["Actividad", "Criterio", "Puntaje", "Acción"]].to_excel(w, sheet_name="Plan de acción", index=False)
        cf_tot.to_excel(w, sheet_name="Flujo de caja", index=False)
        for ws in w.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col) + 2))
            for c in ws[1]:
                c.font = Font(bold=True)
    return out.getvalue()


def pdf_bytes():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    ss = getSampleStyleSheet()
    sm = ss["BodyText"].clone("sm", fontSize=8, leading=10)
    def tabla(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f6e56")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f4")]),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    f = [Paragraph(f"Informe de cadena de valor y flujo de caja: {empresa}", ss["Title"]), Paragraph(f"Fecha: {hoy}", ss["Normal"]),
         Spacer(1, 8), Paragraph(f"Puntaje global de la cadena de valor: <b>{glob:.2f} / 5</b> ({nivel(glob)})", ss["Normal"]), Spacer(1, 8),
         Paragraph("1. Puntaje por actividad primaria", ss["Heading2"]),
         tabla([["Actividad", "Promedio (1-5)", "Nivel"]] + [[a, f"{v:.1f}", nivel(v)] for a, v in prom.items()], [250, 90, 100]),
         Spacer(1, 8), Paragraph("2. Plan de acción priorizado (puntaje 3 o menos)", ss["Heading2"]),
         tabla([["Actividad", "Criterio", "Pts", "Acción"]] + [[Paragraph(r.Actividad, sm), Paragraph(r.Criterio, sm), r.Puntaje, Paragraph(r.Acción, sm)]
                                                               for r in plan_full.itertuples()], [90, 110, 25, 300]),
         Spacer(1, 8), Paragraph("3. Flujo de caja proyectado a 12 meses (S/)", ss["Heading2"]),
         Paragraph(f"Ingresos del año: S/ {tot['Total ingresos']:,.0f} | Egresos con impuesto: S/ {egr_total:,.0f} | "
                   f"Flujo neto: S/ {tot['Flujo neto']:,.0f} | Margen neto: {margen:.1f}%", ss["Normal"]), Spacer(1, 6),
         tabla([["Mes", "Ingresos", "Egresos oper.", "Impuesto", "Flujo neto", "Saldo de caja"]] +
               [[r["Mes"], f"{r['Total ingresos']:,.0f}", f"{r['Egresos operativos']:,.0f}", f"{r['Impuesto a la renta (29.5%)']:,.0f}",
                 f"{r['Flujo neto']:,.0f}", f"{r['Saldo de caja']:,.0f}"] for _, r in cf_tot.iterrows()]),
         Spacer(1, 8), Paragraph("Egresos del año por actividad de la cadena de valor (S/)", ss["Heading2"]),
         tabla([["Actividad", "Egreso anual"]] + [[a, f"{v:,.0f}"] for a, v in egr_act.items()], [250, 100]), Spacer(1, 10),
         Paragraph("Nota: el flujo de caja es una proyección con supuestos referenciales editables, no cifras oficiales de la empresa. "
                   "El puntaje se basa en el análisis del sitio web y en los ajustes del usuario.", sm)]
    doc.build(f)
    return buf.getvalue()


d1, d2, d3 = st.columns(3)
d1.download_button("📄 Informe completo (PDF)", pdf_bytes(), f"informe_{slug}.pdf", "application/pdf", width="stretch")
d2.download_button("📊 Libro de Excel (4 hojas)", excel_bytes(), f"informe_{slug}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
d3.download_button("🧾 Flujo de caja (CSV)", cf_tot.to_csv(index=False).encode("utf-8-sig"), f"flujo_caja_{slug}.csv",
                   "text/csv", width="stretch")
st.caption("PDF: resumen para exponer · Excel: todo el detalle para editar · CSV: flujo de caja para otros programas.")
