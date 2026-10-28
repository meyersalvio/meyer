import random
import time
from itertools import combinations

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Capital Intelectual", page_icon="🧠", layout="wide")

I = [
    dict(n="Lingüístico-verbal", e="🗣️", c="#e5484d", s=["Expresión oral", "Redacción", "Persuasión", "Lectura y vocabulario"],
         r="Convence al público de comprar un lápiz en 30 segundos.",
         a="Escribir un resumen diario de 5 líneas y presentar una idea ante el equipo cada semana."),
    dict(n="Lógico-matemática", e="🧮", c="#2563eb", s=["Razonamiento analítico", "Cálculo", "Resolución de problemas", "Pensamiento crítico"],
         r="Resuelve un acertijo lógico del público en 1 minuto.",
         a="Practicar problemas de lógica y analizar un indicador real de la empresa cada semana."),
    dict(n="Visual-espacial", e="🎨", c="#c026d3", s=["Orientación espacial", "Diseño visual", "Imaginación", "Lectura de gráficos"],
         r="Dibuja en 1 minuto el logo de la empresa sin mirar.",
         a="Hacer mapas mentales, bocetos de procesos y leer un gráfico nuevo cada día."),
    dict(n="Musical", e="🎵", c="#e08a00", s=["Ritmo", "Memoria auditiva", "Sensibilidad al sonido", "Creatividad sonora"],
         r="Inventa un jingle de 10 segundos para el producto.",
         a="Escuchar y analizar música a diario y crear jingles o ritmos para retener ideas."),
    dict(n="Corporal-kinestésica", e="🤸", c="#0f9d8a", s=["Coordinación", "Destreza manual", "Control corporal", "Aprendizaje práctico"],
         r="Explica un proceso solo con mímica y que el público adivine.",
         a="Aprender haciendo: talleres prácticos, simulaciones y pausas activas."),
    dict(n="Interpersonal", e="🤝", c="#f06292", s=["Empatía", "Liderazgo", "Trabajo en equipo", "Negociación"],
         r="Resuelve en 1 minuto un conflicto entre dos voluntarios.",
         a="Practicar escucha activa, rotar el liderazgo en proyectos y hacer mentorías."),
    dict(n="Intrapersonal", e="🪞", c="#7c4dff", s=["Autoconocimiento", "Autorregulación", "Motivación", "Metas personales"],
         r="Cuenta en 30 segundos tu mayor fortaleza y tu mayor reto.",
         a="Llevar un diario de logros, fijar metas SMART y revisar emociones al cierre del día."),
    dict(n="Naturalista", e="🌿", c="#43a047", s=["Observación", "Clasificación", "Sensibilidad ambiental", "Interés por seres vivos"],
         r="Clasifica 5 objetos del aula por categorías en 1 minuto.",
         a="Observar patrones del entorno, proyectos de sostenibilidad y salidas de campo."),
    dict(n="Existencial", e="🌌", c="#455a64", s=["Sentido y propósito", "Pensamiento filosófico", "Visión a largo plazo", "Valores y ética"],
         r="Responde en 30 segundos: ¿para qué existe nuestra empresa?",
         a="Definir su propósito personal, debatir dilemas éticos y planificar a 5 años."),
]
SH = ["Verbal", "Lógica", "Espacial", "Musical", "Corporal", "Interper.", "Intraper.", "Natural", "Existenc."]
M = [dict(n="🚀 Lanzar un producto", w=[3, 2, 3, 0, 0, 3, 1, 0, 2]),
     dict(n="🚨 Resolver una crisis", w=[3, 3, 0, 0, 0, 3, 3, 0, 2]),
     dict(n="🌱 Campaña de sostenibilidad", w=[2, 1, 2, 0, 1, 3, 1, 3, 3]),
     dict(n="🎭 Evento cultural", w=[2, 0, 3, 3, 2, 3, 1, 0, 1]),
     dict(n="💻 Startup tecnológica", w=[2, 3, 3, 0, 0, 2, 2, 0, 2])]
COL = ["#6d3fd2", "#e5484d", "#0f9d8a", "#e08a00", "#2563eb", "#c026d3", "#43a047", "#f06292"]


def cl(x):
    return max(1, min(5, x))


def mk(n, b):
    return {"n": n, "v": [[cl(x + d) for d in (0, 1, -1, 0)] for x in b]}


if "P" not in st.session_state:
    st.session_state.P = [mk("Ana", [5, 3, 3, 2, 2, 5, 4, 2, 3]), mk("Luis", [3, 5, 4, 2, 2, 3, 4, 2, 3]),
                          mk("Carla", [4, 2, 5, 5, 3, 4, 3, 3, 3]), mk("Marco", [2, 4, 3, 2, 5, 3, 3, 5, 2]),
                          mk("Sofía", [4, 3, 2, 3, 3, 5, 5, 3, 5])]
P = st.session_state.P
for _n, _p in enumerate(P):
    _p.setdefault("id", _n)


def _del(pid):
    st.session_state.P[:] = [q for q in st.session_state.P if q["id"] != pid]
    for k in [k for k in st.session_state if str(k).startswith(f"s|{pid}|")]:
        del st.session_state[k]
    st.session_state["sel"] = 0


def _add():
    n = st.session_state.get("nn", "").strip()
    if not n:
        return
    nid = max(q["id"] for q in st.session_state.P) + 1
    st.session_state.P.append({"n": n, "id": nid, "extra": True,
                               "v": [[st.session_state[f"nb{i}"]] * 4 for i in range(9)]})
    st.session_state["sel"] = len(st.session_state.P) - 1


def sc(p, i):
    return sum(p["v"][i]) / 4


def ici(p):
    return round(sum(sc(p, i) for i in range(9)) / 9 * 20)


def lvl(n):
    return "Talento sobresaliente" if n >= 80 else "Alto potencial" if n >= 60 else "En desarrollo" if n >= 40 else "Por activar"


def rgba(h, a):
    return f"rgba({int(h[1:3], 16)},{int(h[3:5], 16)},{int(h[5:7], 16)},{a})"


def radar(ser, h=430):
    th = [f"{x['e']} {SH[i]}" for i, x in enumerate(I)]
    fig = go.Figure()
    for p, c in ser:
        r = [sc(p, i) for i in range(9)]
        fig.add_trace(go.Scatterpolar(r=r + [r[0]], theta=th + [th[0]], fill="toself", name=p["n"],
                                      line=dict(color=c, width=3), fillcolor=rgba(c, .25)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5])), height=h, margin=dict(t=30, b=30),
                      legend=dict(orientation="h"))
    return fig


st.markdown("<div style='background:linear-gradient(120deg,#6d3fd2,#e5484d 60%,#e08a00);color:#fff;border-radius:18px;"
            "padding:18px 24px;margin-bottom:10px'><h1 style='color:#fff;margin:0;font-size:28px'>🧠 Capital Intelectual · Talento Humano</h1>"
            "</div>", unsafe_allow_html=True)

t0, t1, t2, t3 = st.tabs(["👥 Personas", "⚔️ Duelo", "🎯 Armador de equipos", "🎡 Ruleta de retos"])

# ---------------- Personas ----------------
with t0:
    sel = st.radio("Persona", range(len(P)), format_func=lambda i: P[i]["n"], horizontal=True, key="sel")
    p = P[sel]
    if p.get("extra"):
        st.button("🗑️ Eliminar a " + p["n"], on_click=_del, args=(p["id"],), key="del")
    with st.expander("➕ Agregar persona y evaluar sus inteligencias"):
        with st.form("add", clear_on_submit=True):
            st.text_input("Nombre", key="nn")
            st.caption("Elige el nivel (1 a 5) de cada inteligencia. Luego puedes afinar los sub-desarrollos abajo.")
            cs = st.columns(3)
            for i, x in enumerate(I):
                cs[i % 3].select_slider(f"{x['e']} {x['n']}", [1, 2, 3, 4, 5], value=3, key=f"nb{i}")
            st.form_submit_button("Guardar persona", on_click=_add)
    top = st.container()
    st.subheader("Sub-desarrollos por inteligencia")
    st.caption("Abre cada inteligencia y mueve sus 4 sub-desarrollos. Todo se actualiza en vivo.")
    for i, x in enumerate(I):
        with st.expander(f"{x['e']} {x['n']}"):
            cols = st.columns(4)
            for j, s in enumerate(x["s"]):
                k = f"s|{p['id']}|{i}|{j}"
                st.session_state.setdefault(k, p["v"][i][j])
                p["v"][i][j] = cols[j].slider(s, 1, 5, key=k)
            st.progress(sc(p, i) / 5, text=f"{x['n']}: {sc(p, i):.1f} / 5")
    with top:
        a, b = st.columns(2)
        a.subheader(f"Constelación de talento de {p['n']}")
        a.plotly_chart(radar([(p, COL[p["id"] % 8])]), width="stretch")
        s = [sc(p, i) for i in range(9)]
        o = sorted(range(9), key=lambda i: -s[i])
        b.metric("Índice de Capital Intelectual", f"{ici(p)} / 100", lvl(ici(p)), delta_color="off")
        b.markdown(f"**Inteligencia dominante:** {I[o[0]]['e']} {I[o[0]]['n']}")
        b.markdown("  ".join(f"`{I[i]['e']} {SH[i]} {s[i]:.1f}`" for i in o[:3]))
        b.markdown("#### 🌱 Plan de desarrollo")
        for i in reversed(o[-2:]):
            b.markdown(f"**{I[i]['e']} {I[i]['n']} ({s[i]:.1f}):** {I[i]['a']}")

# ---------------- Duelo ----------------
with t1:
    d1, d2 = st.columns(2)
    ia = d1.selectbox("Persona A", range(len(P)), format_func=lambda i: P[i]["n"], index=0)
    ib = d2.selectbox("Persona B", range(len(P)), format_func=lambda i: P[i]["n"], index=min(1, len(P) - 1))
    A, B = P[ia], P[ib]
    sin = round(sum(max(sc(A, i), sc(B, i)) for i in range(9)) / 9 * 20)
    g1, g2 = st.columns(2)
    g1.plotly_chart(radar([(A, COL[A["id"] % 8]), (B, COL[B["id"] % 8] if ib != ia else "#888")]), width="stretch")
    with g2:
        st.metric("Sinergia del dúo", f"{sin}%", help="Se toma el mejor puntaje de los dos en cada inteligencia.")
        fig = go.Figure([go.Bar(y=[f"{x['e']} {SH[i]}" for i, x in enumerate(I)], x=[sc(A, i) for i in range(9)],
                                orientation="h", name=A["n"], marker_color=COL[A["id"] % 8]),
                         go.Bar(y=[f"{x['e']} {SH[i]}" for i, x in enumerate(I)], x=[sc(B, i) for i in range(9)],
                                orientation="h", name=B["n"], marker_color=COL[B["id"] % 8] if ib != ia else "#888")])
        fig.update_layout(barmode="group", height=400, xaxis=dict(range=[0, 5]), margin=dict(t=10, b=10),
                          yaxis=dict(autorange="reversed"), legend=dict(orientation="h"))
        st.plotly_chart(fig, width="stretch")

# ---------------- Armador de equipos ----------------
with t2:
    st.subheader("🎯 Elige la misión y arma el equipo ideal")
    mi = st.selectbox("Misión", range(len(M)), format_func=lambda i: M[i]["n"])
    ks = st.select_slider("Integrantes del equipo", [k for k in (2, 3, 4) if k <= len(P)])
    if st.button("⚡ Formar equipo ideal", type="primary", key="armar"):
        with st.spinner("Analizando combinaciones de talento..."):
            time.sleep(1.2)
        st.session_state.team = (mi, ks)
    tm = st.session_state.get("team")
    if tm:
        mi, ks = tm
        w = M[mi]["w"]
        def tscore(t):
            return round(sum(w[i] * max(sc(P[j], i) for j in t) for i in range(9)) / sum(5 * x for x in w) * 100)
        rk = sorted(((tscore(t), t) for t in combinations(range(len(P)), ks)), reverse=True)
        best = rk[0][1]
        need = [i for i in range(9) if w[i] > 0]
        st.success(f"Equipo ideal para {M[mi]['n']}: cobertura {rk[0][0]}%")
        cols = st.columns(len(best))
        for n, j in enumerate(best):
            cub = [i for i in need if sc(P[j], i) == max(sc(P[q], i) for q in best)]
            cols[n].markdown(
                f"<div style='background:{COL[P[j]["id"] % 8]};color:#fff;border-radius:14px;padding:14px'><b style='font-size:18px'>{P[j]['n']}</b>"
                f"<div style='font-size:24px'>{' '.join(I[i]['e'] for i in cub) or '👤'}</div>"
                f"<div style='font-size:12px'>Aporta: {', '.join(SH[i] for i in cub) or 'apoyo'}</div></div>", unsafe_allow_html=True)
        mx = [max(sc(P[j], i) for j in best) for i in need]
        quien = [P[next(j for j in best if sc(P[j], i) == m)]["n"] for i, m in zip(need, mx)]
        fig = go.Figure(go.Bar(y=[f"{I[i]['e']} {SH[i]} {'★' * w[i]}" for i in need], x=mx, orientation="h",
                               marker_color=[I[i]["c"] for i in need], text=quien, textposition="inside"))
        fig.update_layout(title="Cobertura por inteligencia requerida (★ = importancia)", xaxis=dict(range=[0, 5]),
                          height=60 + 48 * len(need), yaxis=dict(autorange="reversed"), margin=dict(t=50, b=10))
        st.plotly_chart(fig, width="stretch")
        gaps = [i for i, m in zip(need, mx) if w[i] >= 2 and m <= 3.5]
        if gaps:
            st.warning("**Brechas del equipo:** " + ", ".join(f"{I[i]['e']} {I[i]['n']}" for i in gaps) + f".  \nAcción: {I[gaps[0]]['a']}")
        else:
            st.info("El equipo cubre bien todas las inteligencias clave de esta misión.")
        st.caption("Otras opciones: " + " · ".join(f"{s}% {' + '.join(P[j]['n'] for j in t)}" for s, t in rk[1:4]))

# ---------------- Ruleta ----------------
with t3:
    st.subheader("🎡 Ruleta de retos en vivo")
    st.caption("Gira la ruleta: te toca una inteligencia, un reto para el público y el voluntario ideal del equipo.")
    if st.button("🎡 ¡Girar!", type="primary", key="girar"):
        k = random.randrange(9)
        ph = st.empty()
        for n in range(26):
            x = I[random.randrange(9)] if n < 25 else I[k]
            ph.markdown(f"<div style='text-align:center;font-size:96px'>{x['e']}</div>", unsafe_allow_html=True)
            time.sleep(0.05 + n * 0.012)
        ph.empty()
        st.session_state.k = k
    k = st.session_state.get("k")
    if k is not None:
        x = I[k]
        m = max(sc(p, k) for p in P)
        v = " / ".join(p["n"] for p in P if sc(p, k) == m)
        st.markdown(
            f"<div style='border-left:8px solid {x['c']};background:{rgba(x['c'], .12)};border-radius:12px;padding:16px'>"
            f"<div style='font-size:44px'>{x['e']}</div><h3 style='margin:0'>{x['n']}</h3>"
            f"<p><b>🎤 Reto en vivo:</b> {x['r']}</p><p><b>⭐ Voluntario ideal:</b> {v} ({m:.1f}/5)</p>"
            f"<p style='opacity:.8'><b>Para desarrollarla:</b> {x['a']}</p></div>", unsafe_allow_html=True)

st.caption("Datos de ejemplo. Base teórica: inteligencias múltiples de Howard Gardner (8 originales + existencial). Escala 1 a 5.")
