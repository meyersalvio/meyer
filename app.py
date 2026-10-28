import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Cadena de Valor", page_icon="⛓️", layout="wide")
st.title("Analizador de Cadena de Valor")
st.caption("Actividades primarias · Modelo de Porter")

empresa = st.text_input("Empresa analizada", "Gloria S.A. (caso ilustrativo)")

DATOS = {
    "Logística interna": [
        ("Abastecimiento de materia prima", 3, "% de leche recibida dentro de especificación",
         "Contratos de largo plazo con ganaderos, precio por calidad y asistencia técnica."),
        ("Cadena de frío en recepción", 4, "% de lotes rechazados por temperatura",
         "Mantener monitoreo con sensores y registros digitales."),
        ("Control de inventarios", 2, "Rotación de inventario y % de mermas",
         "Aplicar PEPS/FEFO, clasificación ABC y punto de reorden."),
        ("Gestión de proveedores", 3, "Entregas a tiempo (OTIF)",
         "Scorecard trimestral de proveedores y proveedores alternos."),
    ],
    "Operaciones (producción)": [
        ("Eficiencia de planta (OEE)", 3, "OEE = disponibilidad × rendimiento × calidad",
         "Implementar SMED, TPM y tablero de OEE por línea."),
        ("Calidad e inocuidad", 5, "% de reclamos por calidad",
         "Sostener auditorías internas y mejora continua."),
        ("Mantenimiento", 2, "MTBF, MTTR y % de mantenimiento preventivo",
         "Plan preventivo y predictivo, repuestos críticos y capacitación."),
        ("Uso de energía y mermas", 3, "kWh por litro procesado",
         "Recuperar condensados y optimizar ciclos de limpieza CIP."),
    ],
    "Logística externa": [
        ("Cobertura de distribución", 4, "% de puntos de venta atendidos",
         "Distribuidores locales y preventa móvil en zonas rurales."),
        ("Nivel de servicio (OTIF)", 3, "Pedidos completos y a tiempo",
         "Pronóstico colaborativo de demanda y stock de seguridad por SKU."),
        ("Costo logístico", 2, "Costo logístico como % de ventas",
         "Software de ruteo (TMS), consolidación de carga y costo por ruta."),
        ("Trazabilidad y devoluciones", 3, "% de devoluciones y tiempo de respuesta",
         "Código QR por lote y gestión de devoluciones con causa raíz."),
    ],
    "Marketing y ventas": [
        ("Posicionamiento de marca", 5, "Recordación de marca (top of mind)",
         "Reforzar la propuesta de valor en productos de mayor valor agregado."),
        ("Precios y promociones", 3, "Margen por canal y elasticidad precio",
         "Segmentar precios por canal y evaluar el ROI de promociones."),
        ("Canales digitales", 2, "% de ventas online y costo de adquisición",
         "E-commerce B2B para bodegas, redes sociales y CRM."),
        ("Fuerza de ventas", 3, "Ventas por vendedor y cumplimiento de cuota",
         "Comisiones por mix y rentabilidad, y capacitación comercial."),
    ],
    "Servicios": [
        ("Atención de reclamos", 3, "Tiempo promedio de resolución",
         "Canal único omnicanal con meta de resolución en 48 horas."),
        ("Asesoría a bodegas", 3, "Visitas efectivas por cliente al mes",
         "Programa de acompañamiento en exhibición, frío y rotación."),
        ("Reposición y garantía", 4, "% de reposiciones en plazo",
         "Reposición en la siguiente visita de ruta y registro digital."),
        ("Satisfacción y fidelización", 2, "NPS y tasa de recompra",
         "Encuesta NPS trimestral y programa de lealtad."),
    ],
}

def nivel(p):
    return "Fortaleza" if p >= 4 else "Aceptable" if p >= 3 else "Debilidad"

filas = []
tabs = st.tabs([f"{i+1}. {k}" for i, k in enumerate(DATOS)])
for tab, (actividad, items) in zip(tabs, DATOS.items()):
    with tab:
        for criterio, punt, kpi, sol in items:
            c1, c2 = st.columns([2, 3])
            with c1:
                p = st.slider(criterio, 1, 5, punt, key=f"{actividad}-{criterio}")
                st.caption(f"Indicador: {kpi}")
            with c2:
                if p <= 3:
                    st.warning(f"**{nivel(p)}** · Solución propuesta: {sol}")
                else:
                    st.success(f"**{nivel(p)}** · Para mantener: {sol}")
            filas.append({"Actividad": actividad, "Criterio": criterio,
                          "Puntaje": p, "Nivel": nivel(p), "Acción": sol})

df = pd.DataFrame(filas)
prom = df.groupby("Actividad", sort=False)["Puntaje"].mean()

st.divider()
st.header(f"Resumen: {empresa}")
a, b = st.columns(2)
with a:
    fig = go.Figure(go.Scatterpolar(r=list(prom) + [prom.iloc[0]],
                                    theta=list(prom.index) + [prom.index[0]], fill="toself"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
with b:
    st.metric("Puntaje global (1-5)", f"{df['Puntaje'].mean():.2f}")
    st.dataframe(prom.round(2).rename("Promedio"), use_container_width=True)

st.subheader("Plan de acción priorizado (puntaje ≤ 3)")
plan = df[df["Puntaje"] <= 3].sort_values("Puntaje")
st.dataframe(plan[["Actividad", "Criterio", "Puntaje", "Acción"]],
             use_container_width=True, hide_index=True)
st.download_button("Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                   "cadena_valor.csv", "text/csv")
