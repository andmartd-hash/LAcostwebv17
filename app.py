import streamlit as st
import pandas as pd
from datetime import date, datetime
import io

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="LACOSWEB V5 - Pricing Engine", layout="wide", page_icon="💰")

# ==========================================
# 1. BASE DE DATOS EMBEBIDA (Extraída de tus CSVs V5)
# ==========================================

# DB: COUNTRIES (E/R, Currency, Taxes)
DB_COUNTRIES = {
    "Argentina": {"ER": 1428.95, "Curr": "ARS", "Tax": 0.0529},
    "Brazil":    {"ER": 5.34,    "Curr": "BRL", "Tax": 0.1425},
    "Chile":     {"ER": 934.70,  "Curr": "CLP", "Tax": 0.0},
    "Colombia":  {"ER": 3775.22, "Curr": "COP", "Tax": 0.01},
    "Peru":      {"ER": 3.37,    "Curr": "PEN", "Tax": 0.0},
    "Mexico":    {"ER": 18.42,   "Curr": "MXN", "Tax": 0.0},
    "Uruguay":   {"ER": 39.73,   "Curr": "UYU", "Tax": 0.0},
    "Venezuela": {"ER": 235.28,  "Curr": "VES", "Tax": 0.0155},
    "Ecuador":   {"ER": 1.0,     "Curr": "USD", "Tax": 0.0} # Asumido 1 para USD
}

# DB: OFFERINGS (L40 mapping)
# Simplificado con los ejemplos del CSV
DB_OFFERINGS = {
    "IBM Customized Support for Multivendor Hardware Services": {"L40": "6942-76T", "Conga": "Location Based Services"},
    "IBM Support for Red Hat": {"L40": "6948-B73", "Conga": "Conga by CSV"},
    "SWMA MVS SPT other Prod": {"L40": "6942-76O", "Conga": "Conga by CSV"},
    "IBM Support for Oracle":  {"L40": "6942-42E", "Conga": "Location Based Services"},
    "Relocation Services - Packaging": {"L40": "6942-54E", "Conga": "Location Based Services"}
}

# DB: QA RISK (Contingency %)
DB_RISK = {
    "Low": 0.02,
    "Medium": 0.05,
    "High": 0.08
}

# DB: SLC (Uplift Factors - Logic Brasil vs No Brasil)
# Extracto del CSV SLC.csv
DB_SLC = [
    {"Scope": "no brasil", "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7SD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7 4h Resp", "Factor": 1.5},
    {"Scope": "no brasil", "SLC": "24X7 6h Fix", "Factor": 1.6},
    {"Scope": "Brasil",    "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "Brasil",    "SLC": "24X7SD", "Factor": 1.218}, # Ejemplo uplifts Brasil
    {"Scope": "Brasil",    "SLC": "24X7 4h Resp", "Factor": 1.7}
]

# ==========================================
# 2. MOTORES DE CÁLCULO (Lógica V5)
# ==========================================

def get_slc_factor(country, slc_code):
    """Determina el factor basado en si es Brasil o Resto del mundo."""
    scope_key = "Brasil" if country == "Brazil" else "no brasil"
    
    # Buscar en la lista de diccionarios
    for item in DB_SLC:
        # Búsqueda laxa (contains) para facilitar coincidencias
        if item["Scope"].lower() == scope_key.lower() and slc_code in item["SLC"]:
            return item["Factor"]
    return 1.0 # Default si no encuentra

def calc_duration(start, end):
    if not start or not end or end < start: return 0.0
    days = (end - start).days
    return round(days / 30.44, 1)

# ==========================================
# 3. INTERFAZ DE USUARIO (Frontend)
# ==========================================

st.title("💼 LACOSWEB V5 - Cotizador Financiero")
st.markdown("Sistema de Precios Multi-moneda y Riesgo (V5-BASE)")

# --- SIDEBAR: DATOS DEL CONTRATO (Input.csv Sidebar) ---
with st.sidebar:
    st.header("1. Configuración del Contrato")
    
    # Selección de País y Moneda
    country = st.selectbox("Country", list(DB_COUNTRIES.keys()), index=3) # Default Colombia
    country_data = DB_COUNTRIES[country]
    
    col_curr1, col_curr2 = st.columns(2)
    view_currency = col_curr1.radio("Ver Valores en:", ["USD", "Local"], horizontal=True)
    
    # Mostrar Tasa de Cambio (E/R)
    er_val = country_data['ER'] if country_data['ER'] else 1.0
    col_curr2.metric(f"Tasa ({country_data['Curr']})", f"{er_val:,.2f}")

    # Datos Cliente
    customer = st.text_input("Customer Name", "Cliente V5")
    risk_level = st.selectbox("QA Risk", list(DB_RISK.keys()))
    risk_pct = DB_RISK[risk_level]
    
    st.markdown("---")
    st.header("2. Periodo y Costos Fijos")
    
    c_date1, c_date2 = st.columns(2)
    start_date = c_date1.date_input("Contract Start", date.today())
    end_date = c_date2.date_input("Contract End", date.today().replace(year=date.today().year + 1))
    
    contract_duration = calc_duration(start_date, end_date)
    st.info(f"Periodo Contrato: **{contract_duration} meses**")
    
    # Distributed Cost (Poliza/Fianza)
    dist_cost_input = st.number_input("Distributed Cost (Póliza/Fianza)", min_value=0.0, value=100.0)
    
    st.markdown("---")
    st.header("3. Pricing Target")
    target_gp = st.slider("Target GP % (Margen)", 0.0, 1.0, 0.40, 0.01) # Default 40% del CSV Pricing

# --- PANEL CENTRAL: TABLA DE SERVICIOS (Input.csv Center) ---

st.subheader("📋 Detalle de Servicios (Offering & SLC)")

# Inicializar estado de la tabla si no existe
if "df_services" not in st.session_state:
    # Estructura basada en Input.csv
    data = {
        "Offering": ["IBM Customized Support for Multivendor Hardware Services"],
        "Description": ["Soporte Servidores"],
        "SLC": ["9X5NBD"],
        "QTY": [1],
        "Unit Cost (USD)": [100.0] 
    }
    st.session_state.df_services = pd.DataFrame(data)

# Configuración del Editor
column_config = {
    "Offering": st.column_config.SelectboxColumn("Offering", options=list(DB_OFFERINGS.keys()), width="large"),
    "SLC": st.column_config.SelectboxColumn("SLC (Nivel Servicio)", options=["9X5NBD", "24X7SD", "24X7 4h Resp", "24X7 6h Fix"], width="medium"),
    "Unit Cost (USD)": st.column_config.NumberColumn("Costo Unit. (USD)", format="$%.2f", min_value=0.0),
    "QTY": st.column_config.NumberColumn("Cantidad", min_value=1, step=1)
}

edited_df = st.data_editor(
    st.session_state.df_services,
    num_rows="dynamic",
    use_container_width=True,
    column_config=column_config,
    key="editor"
)

# ==========================================
# 4. PROCESAMIENTO Y CÁLCULOS (Engine)
# ==========================================

if not edited_df.empty:
    
    # A. Pre-cálculo: Cuántas líneas activas hay para distribuir el costo fijo
    num_rows = len(edited_df)
    cost_per_row_dist = dist_cost_input / num_rows if num_rows > 0 else 0
    
    results = []
    total_cost_usd = 0.0
    
    for idx, row in edited_df.iterrows():
        # 1. Recuperar Datos Base
        offering = row.get("Offering", "")
        offering_data = DB_OFFERINGS.get(offering, {"L40": "N/A", "Conga": "N/A"})
        
        slc = row.get("SLC", "")
        qty = row.get("QTY", 0)
        unit_cost_usd = row.get("Unit Cost (USD)", 0.0)
        
        # 2. Factores
        # Si es Local, convertiríamos Unit Cost a USD. Asumimos input en USD por simplicidad del editor.
        # Factor SLC (Uplift)
        slc_factor = get_slc_factor(country, slc)
        
        # 3. Costo Base de la Línea
        # Fórmula: (Unit Cost * Qty * Duration * SLC_Factor) + Costo Distribuido
        base_line_cost = (unit_cost_usd * qty * contract_duration * slc_factor) 
        total_line_cost = base_line_cost + cost_per_row_dist
        
        total_cost_usd += total_line_cost
        
        results.append({
            "Offering": offering,
            "L40 (Auto)": offering_data["L40"],
            "Conga (Auto)": offering_data["Conga"],
            "SLC Factor": slc_factor,
            "Base USD": base_line_cost,
            "Dist. Cost": cost_per_row_dist,
            "Total Cost (USD)": total_line_cost
        })
        
    df_results = pd.DataFrame(results)
    
    # ==========================================
    # 5. RESULTADOS FINANCIEROS (Pricing.csv Logic)
    # ==========================================
    
    st.markdown("---")
    st.header("💰 Análisis Financiero")
    
    # Lógica de Precio (Pricing.csv): Costo * (1+Riesgo) / (1-GP)
    # Costo Total + Contingencia
    contingency_amt = total_cost_usd * risk_pct
    cost_with_risk = total_cost_usd + contingency_amt
    
    # Precio de Venta
    if target_gp >= 1.0: target_gp = 0.99 # Evitar división por cero
    sell_price_usd = cost_with_risk / (1 - target_gp)
    
    # Impuestos
    taxes_usd = sell_price_usd * country_data['Tax']
    final_price_usd = sell_price_usd + taxes_usd
    
    # CONVERSIÓN DE MONEDA (VIEW)
    display_factor = er_val if view_currency == "Local" else 1.0
    curr_symbol = country_data['Curr'] if view_currency == "Local" else "USD"
    
    # Mostrar KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric("Costo Total", f"{total_cost_usd * display_factor:,.2f} {curr_symbol}", delta=f"Riesgo: {risk_pct*100}%")
    kpi2.metric("Contingencia", f"{contingency_amt * display_factor:,.2f} {curr_symbol}")
    kpi3.metric("Precio Venta (Revenue)", f"{sell_price_usd * display_factor:,.2f} {curr_symbol}", delta=f"GP: {target_gp*100}%")
    kpi4.metric(f"Precio Final (+{country_data['Tax']*100}% Tax)", f"{final_price_usd * display_factor:,.2f} {curr_symbol}")

    # Tabla Detallada
    with st.expander("Ver desglose detallado por línea"):
        st.dataframe(df_results.style.format({
            "SLC Factor": "{:.2f}",
            "Base USD": "${:,.2f}",
            "Dist. Cost": "${:,.2f}",
            "Total Cost (USD)": "${:,.2f}"
        }))

    # ==========================================
    # 6. EXPORTACIÓN
    # ==========================================
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_results.to_excel(writer, sheet_name='Detailed Cost', index=False)
        # Hoja Resumen
        summary = pd.DataFrame({
            "Concept": ["Customer", "Country", "Currency", "E/R", "Total Cost", "Total Price", "GP%"],
            "Value": [customer, country, country_data['Curr'], er_val, total_cost_usd, sell_price_usd, target_gp]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
        
    st.download_button(
        label=f"📥 Descargar Cotización ({customer})",
        data=buffer,
        file_name=f"Cotizacion_{customer}_V5.xlsx",
        mime="application/vnd.ms-excel"
    )
