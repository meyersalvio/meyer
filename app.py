import re
import textwrap
import unicodedata
from io import BytesIO
from urllib.parse import urljoin, urlparse

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Cadena de Valor y Flujo de Caja", page_icon="⛓️", layout="wide")

COLORES = {
    "Logística interna": "#1f77b4",
    "Operaciones (producción)": "#ff7f0e",
    "Logística externa": "#2ca02c",
    "Marketing y ventas": "#9467bd",
    "Servicios": "#d62728",
}
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
         ["tienda online", "comprar", "carrito", "facebook", "instagram", "tiktok", "linkedin", "e-commerce"]),
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

PAGINAS_UTILES = [
    "nosotros", "quienes", "about", "producto", "servicio", "contacto",
    "tienda", "sostenib", "calidad", "distribu", "empresa"
]

GENERICAS = {
    "inicio", "home", "bienvenido", "bienvenidos", "welcome", "pagina principal",
    "sitio oficial", "oficial", "index", "portada", "tienda online", "web oficial"
}


def quitar_tildes(t):
    return "".join(unicodedata.normalize("NFD", c)[0] for c in t).lower()


def nivel(p):
    return "Fortaleza" if p >= 4 else "Aceptable" if p >= 3 else "Debilidad"


def slug_archivo(texto):
    limpio = re.sub(r"[^a-zA-Z0-9_-]+", "_", quitar_tildes(texto)).strip("_")
    return limpio or "empresa"


@st.cache_data(show_spinner=False, ttl=3600)
def descargar(url):
    h = {"User-Agent": "Mozilla/5.0 (compatible; AnalizadorCadenaValor/1.0)"}
    r = requests.get(url, headers=