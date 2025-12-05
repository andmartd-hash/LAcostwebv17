import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LACOSWEB V17", layout="wide", page_icon="📊")

# --- 1. BASE DE DATOS Y PARÁMETROS (Extracción de Hoja 'Parameters') ---
# Aquí definimos los valores que antes buscabas con VLOOKUP o IFs.
# Nota: He puesto valores de ejemplo. Debes actualizar estos números con los reales de tu hoja Parameters.

PARAMS = {
    # Lógica de Contingencia (Celda I3 basada en H3)
    # Referencia Excel: Parameters!J226, J227, J228
    "RISK_COSTS": {
        "Low": 500.0,
        "Med": 1200.0,
        "High": 3500.0
    },
    # Catálogo de Servicios (Para VLOOKUP filas 14-20)
    # Referencia Excel: Parameters!$K$436:$N$458
    # Clave: ID Servicio (Col D). Valor: [Descripción (Col B), Costo Unitario (Col H)]
    "SERVICES_DB": {
        "S001": {"desc": "Consultoría Senior", "cost": 150.0},
        "S002": {"desc": "Desarrollo Backend", "cost": 120.0},
        "S003": {"desc": "Desarrollo Frontend", "cost": 110.0},
        "S004": {"desc": "QA Testing", "cost": 90.0},
        "S005": {"desc": "Gestión de Proyecto", "cost": 130.0},
        "S006": {"desc": "Soporte Nivel 1", "cost": 50.0},
        "S007": {"desc": "Arquitectura Cloud", "cost": 180.0},
        "S008": {"desc": "DevOps Engineering", "cost": 160.0},
    }
}

# --- 2. LÓGICA DE NEGOCIO (Funciones de Cálculo) ---

def calculate_duration(start, end):
    """Lógica celda E8: Calcula meses de duración."""
    if not start or not end: return 0
    if end < start: return 0
    days = (end - start).days
    return round(days / 30.44, 1)

def get_service_details(service_id):
    """Simula el VLOOKUP para traer descripción y costo."""
    return PARAMS["SERVICES_DB"].get(service_id, {"desc": "No encontrado", "cost": 0.0})

# --- 3. INTERFAZ DE USUARIO ---

st.title("📊 LACOSWEB V17 - Cloud Data Entry")
st.markdown("Sistema de cotización y captura de datos (Reemplazo de Excel).")

# -- SECCIÓN A: CABECERA DEL CONTRATO (Sidebar) --
with st.sidebar:
    st.header("1. Información del Contrato")
    st.info("Datos de las celdas B2-H4")
    
    country = st.selectbox("Country (B2)", ["Colombia", "Perú", "México", "Chile"])
    customer_name = st.text_input("Customer Name (D2)", "Cliente Ejemplo SAS")
    contract_id = st.text_input("Contract ID (D4)", "CTR-2025-001")
    
    st.markdown("---")
    st.header("2. Análisis de Riesgo")
    
    # Selector de Riesgo (H3)
    risk_level = st.select_slider("Risk Level (H3)", options=["Low", "Med", "High"], value="Low")
    
    # Cálculo automático de Contingencia (I3)
    contingency_cost = PARAMS["RISK_COSTS"][risk_level]
    st.metric("Costo Contingencia (I3)", f"${contingency_cost:,.2f}")
    
    st.markdown("---")
    st.header("3. Tiempos (E8)")
    col_d1, col_d2 = st.columns(2)
    start_date = col_d1.date_input("Start Date", date.today())
    end_date = col_d2.date_input("End Date", date.today() + timedelta(days=180))
    
    duration = calculate_duration(start_date, end_date)
    st.metric("Duración Calculada", f"{duration} Meses")

# -- SECCIÓN B: DETALLE DE SERVICIOS (Tabla Editable) --
st.subheader("📋 Detalle de Servicios (Input Rows 14-20)")

# Inicializar datos de la tabla si no existen
if "df_items" not in st.session_state:
    # Estructura inicial vacía
    data = {
        "Service ID": ["S001", "S002", "", "", ""],
        "Cantidad": [1, 1, 0, 0, 0],
        "Descripción (Auto)": ["Consultoría Senior", "Desarrollo Backend", "", "", ""],
        "Costo Unitario (Auto)": [150.0, 120.0, 0.0, 0.0, 0.0]
    }
    st.session_state.df_items = pd.DataFrame(data)

# Mostrar editor de datos
# Esto permite editar ID y Cantidad. Las otras columnas se recalcularán.
edited_df = st.data_editor(
    st.session_state.df_items[["Service ID", "Cantidad"]],
    num_rows="dynamic",
    use_container_width=True,
    key="data_editor"
)

# --- 4. MOTOR DE CÁLCULO EN TIEMPO REAL ---
# Recorremos la tabla editada para aplicar los "VLOOKUPs" y cálculos
calculated_rows = []
subtotal_services = 0.0

for index, row in edited_df.iterrows():
    svc_id = str(row["Service ID"]).strip()
    qty = row["Cantidad"]
    
    # Lógica VLOOKUP
    details = get_service_details(svc_id)
    unit_cost = details["cost"]
    desc = details["desc"]
    
    if svc_id == "" or svc_id == "nan":
        desc = ""
        unit_cost = 0.0
        
    line_total = unit_cost * qty
    subtotal_services += line_total
    
    calculated_rows.append({
        "Service ID": svc_id,
        "Descripción": desc,
        "Cantidad": qty,
        "Costo Unitario": unit_cost,
        "Subtotal": line_total
    })

df_final = pd.DataFrame(calculated_rows)

# Mostrar tabla calculada (Visualización limpia)
st.write("---")
col_res1, col_res2 = st.columns([3, 1])

with col_res1:
    st.markdown("#### Detalle Calculado")
    st.dataframe(
        df_final[df_final["Service ID"] != ""], 
        use_container_width=True,
        column_config={
            "Costo Unitario": st.column_config.NumberColumn(format="$%.2f"),
            "Subtotal": st.column_config.NumberColumn(format="$%.2f")
        }
    )

with col_res2:
    st.markdown("#### Resumen Financiero")
    st.write(f"**Servicios:** ${subtotal_services:,.2f}")
    st.write(f"**Contingencia:** ${contingency_cost:,.2f}")
    st.markdown("---")
    total_project = subtotal_services + contingency_cost
    st.metric("TOTAL PROYECTO", f"${total_project:,.2f}")

# --- 5. EXPORTAR A EXCEL ---
st.markdown("### Acciones")
if st.button("💾 Generar Reporte Excel"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Guardar Input Data
        summary_data = {
            "Campo": ["Customer", "Country", "Risk", "Duration", "Total"],
            "Valor": [customer_name, country, risk_level, duration, total_project]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Resumen', index=False)
        
        # Guardar Detalle
        df_final.to_excel(writer, sheet_name='Detalle Servicios', index=False)
        
    st.download_button(
        label="📥 Descargar .xlsx",
        data=buffer,
        file_name=f"Cotizacion_{contract_id}.xlsx",
        mime="application/vnd.ms-excel"
    )

# Catálogo de Ayuda (Para que sepas qué IDs usar)
with st.expander("ℹ️ Ver Catálogo de Servicios Disponibles (IDs válidos)"):
    st.write(pd.DataFrame(PARAMS["SERVICES_DB"]).T)
