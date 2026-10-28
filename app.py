import re
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


@st.cache_data(show_spinner=False, ttl=3600)
def leer_sitio(url, max_paginas=5):
    html = descargar(url)
    texto, sopa = texto_de(html)
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
    return texto, visitadas


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

for act, items in DATOS.items():
    for crit, base, *_ in items:
        st.session_state.setdefault(f"{act}|{crit}", base)

with st.sidebar:
    st.header("Análisis en línea")
    empresa = st.text_input("Nombre de la empresa", "Gloria S.A. (caso ilustrativo)")
    wa_num = st.text_input("Tu WhatsApp (con código de país)", "51", help="Ejemplo: 51999999999")
    url = st.text_input("Link de la empresa", placeholder="https://www.empresa.com")
    if st.button("🔎 Analizar sitio web", use_container_width=True):
        if not url.strip():
            st.warning("Escribe un link.")
        else:
            if not url.startswith("http"):
                url = "https://" + url.strip()
            try:
                with st.spinner("Leyendo el sitio..."):
                    texto, paginas = leer_sitio(url)
                r = analizar_texto(texto)
                for (act, crit), (p, _, _) in r.items():
                    st.session_state[f"{act}|{crit}"] = p
                st.session_state["evid"] = r
                st.session_state["paginas"] = paginas
                st.success(f"Se leyeron {len(paginas)} página(s).")
            except Exception as e:
                st.error(f"No se pudo leer el sitio: {e}")
    if st.button("↺ Restablecer caso base", use_container_width=True):
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

filas = []
tabs = st.tabs([f"{i+1}. {k}" for i, k in enumerate(DATOS)])
for tab, (act, items) in zip(tabs, DATOS.items()):
    with tab:
        st.markdown(f"<h4 style='color:{COLORES[act]}'>{act}</h4>", unsafe_allow_html=True)
        for crit, _, kpi, sol, _ in items:
            c1, c2 = st.columns([2, 3])
            with c1:
                p = st.slider(crit, 1, 5, key=f"{act}|{crit}")
                st.caption(f"Indicador: {kpi}")
            with c2:
                lv = nivel(p)
                accion = ("Solución propuesta" if p <= 3 else "Para mantener")
                st.markdown(
                    f"<div style='border-left:5px solid {NIVEL_COL[lv]};padding:6px 12px;background:{NIVEL_COL[lv]}18;border-radius:6px'>"
                    f"<b style='color:{NIVEL_COL[lv]}'>{lv}</b> · <b>{accion}:</b> {sol}</div>", unsafe_allow_html=True)
                ev = st.session_state.get("evid", {}).get((act, crit))
                if ev and ev[2]:
                    st.caption(f"Evidencia en el sitio ({ev[1]} menciones): {ev[2]}")
                elif ev:
                    st.caption("Sin menciones en el sitio analizado.")
            filas.append({"Actividad": act, "Criterio": crit, "Puntaje": p, "Nivel": lv, "Acción": sol})

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
    st.plotly_chart(radar, use_container_width=True)
with f2:
    ids = [empresa] + list(DATOS) + list(df["Criterio"])
    pars = [""] + [empresa] * 5 + list(df["Actividad"])
    vals = [df["Puntaje"].sum()] + [df[df["Actividad"] == a]["Puntaje"].sum() for a in DATOS] + list(df["Puntaje"])
    cols = ["#37474f"] + [COLORES[a] for a in DATOS] + [NIVEL_COL[n] for n in df["Nivel"]]
    sol = go.Figure(go.Sunburst(labels=ids, parents=pars, values=vals, branchvalues="total",
                                marker=dict(colors=cols, line=dict(color="white", width=2)),
                                insidetextorientation="radial"))
    sol.update_layout(title="Cadena completa (anillo exterior = nivel)", height=400, margin=dict(t=60, b=10))
    st.plotly_chart(sol, use_container_width=True)

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
    st.plotly_chart(heat, use_container_width=True)
with f4:
    don = go.Figure(go.Pie(labels=list(conteo.index), values=list(conteo.values), hole=0.62, sort=False,
                           marker=dict(colors=[NIVEL_COL[n] for n in conteo.index], line=dict(color="white", width=3)),
                           textinfo="label+value"))
    don.update_layout(title="Distribución de niveles", height=380, margin=dict(t=60, b=20), showlegend=False,
                      annotations=[dict(text=f"<b>{glob:.1f}</b><br>global", x=0.5, y=0.5, font_size=24, showarrow=False)])
    st.plotly_chart(don, use_container_width=True)

d = df.sort_values("Puntaje")
rank = go.Figure(go.Bar(x=d["Puntaje"], y=d["Criterio"], orientation="h",
                        marker_color=[NIVEL_COL[n] for n in d["Nivel"]], text=d["Puntaje"], textposition="outside"))
rank.update_layout(title="Ranking de criterios (rojo = prioridad de mejora)", height=560,
                   xaxis=dict(range=[0, 5.5]), margin=dict(t=60, b=20))
st.plotly_chart(rank, use_container_width=True)

st.subheader("Plan de acción priorizado (puntaje ≤ 3)")
filtro = st.multiselect("Filtrar por actividad", list(DATOS), default=list(DATOS))
plan = df[(df["Puntaje"] <= 3) & (df["Actividad"].isin(filtro))].sort_values("Puntaje")
st.dataframe(plan[["Actividad", "Criterio", "Puntaje", "Acción"]], use_container_width=True, hide_index=True)
st.download_button("⬇ Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                   "cadena_valor.csv", "text/csv")

# ---------- WhatsApp ----------
numero = re.sub(r"\D", "", wa_num)
msg = (f"Hola, te comparto el análisis de cadena de valor de {empresa}: puntaje global {glob:.2f}/5. "
       f"Mejor actividad: {prom.idxmax()} ({prom.max():.1f}). Actividad crítica: {prom.idxmin()} ({prom.min():.1f}). "
       "¿Podemos conversar las mejoras?")
wa_url = (f"https://wa.me/{numero}?text=" if len(numero) > 5 else "https://wa.me/?text=") + quote(msg)

st.markdown(f"""
<style>
.wa-box{{background:linear-gradient(135deg,#25D366,#128C7E);border-radius:16px;padding:18px 22px;color:#fff;margin:14px 0}}
.wa-box h3{{margin:0 0 4px 0;color:#fff}}
.wa-fab{{position:fixed;right:22px;bottom:22px;z-index:9999;background:#25D366;color:#fff!important;text-decoration:none!important;
 border-radius:50px;padding:12px 20px;font-weight:700;display:flex;gap:8px;align-items:center;
 box-shadow:0 4px 14px rgba(0,0,0,.35);animation:pulso 2s infinite}}
@keyframes pulso{{0%{{box-shadow:0 0 0 0 rgba(37,211,102,.7)}}70%{{box-shadow:0 0 0 18px rgba(37,211,102,0)}}100%{{box-shadow:0 0 0 0 rgba(37,211,102,0)}}}}
</style>
<div class="wa-box"><h3>💬 Conversemos por WhatsApp</h3>
Envía este diagnóstico a un asesor, a tu equipo o a tu docente con un solo clic.</div>
<a class="wa-fab" href="{wa_url}" target="_blank">
<svg width="24" height="24" viewBox="0 0 24 24" fill="#fff"><path d="M12 2a10 10 0 0 0-8.6 15L2 22l5.1-1.3A10 10 0 1 0 12 2zm5.2 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.1-4.5-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.8s.7-2 1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.9 2.1c.1.2.1.4 0 .5l-.4.6-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1.1c.2-.3.4-.2.6-.1l2 1c.3.1.5.2.5.3.1.2.1.8-.1 1.3z"/></svg>
WhatsApp</a>""", unsafe_allow_html=True)
st.link_button("💬 Enviar resultados por WhatsApp", wa_url, use_container_width=True)
