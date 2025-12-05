import streamlit as st
import pandas as pd
from datetime import date
import io

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="LacostWeb ver19", layout="wide", page_icon="🌐")

# --- CSS PERSONALIZADO (Para letra pequeña en Sidebar) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        font-size: 12px;
    }
    [data-testid="stSidebar"] label {
        font-size: 13px !important;
        font-weight: bold;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 13px !important;
    }
    /* Ocultar flechas del input number */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASE DE DATOS EMBEBIDA (V5 Data)
# ==========================================

DB_COUNTRIES = {
    "Argentina": {"ER": 1428.95, "Curr": "ARS", "Tax": 0.0529},
    "Brazil":    {"ER": 5.34,    "Curr": "BRL", "Tax": 0.1425},
    "Chile":     {"ER": 934.70,  "Curr": "CLP", "Tax": 0.0},
    "Colombia":  {"ER": 3775.22, "Curr": "COP", "Tax": 0.01},
    "Peru":      {"ER": 3.37,    "Curr": "PEN", "Tax": 0.0},
    "Mexico":    {"ER": 18.42,   "Curr": "MXN", "Tax": 0.0},
    "Uruguay":   {"ER": 39.73,   "Curr": "UYU", "Tax": 0.0},
    "Venezuela": {"ER": 235.28,  "Curr": "VES", "Tax": 0.0155},
    "Ecuador":   {"ER": 1.0,     "Curr": "USD", "Tax": 0.0}
}

DB_OFFERINGS = {
    "IBM Customized Support for Multivendor Hardware Services": {"L40": "6942-76T", "Conga": "Location Based Services"},
    "IBM Support for Red Hat": {"L40": "6948-B73", "Conga": "Conga by CSV"},
    "SWMA MVS SPT other Prod": {"L40": "6942-76O", "Conga": "Conga by CSV"},
    "IBM Support for Oracle":  {"L40": "6942-42E", "Conga": "Location Based Services"},
    "Relocation Services - Packaging": {"L40": "6942-54E", "Conga": "Location Based Services"}
}

DB_RISK = {
    "Low": 0.02,
    "Medium": 0.05,
    "High": 0.08
}

DB_SLC = [
    {"Scope": "no brasil", "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7SD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7 4h Resp", "Factor": 1.5},
    {"Scope": "no brasil", "SLC": "24X7 6h Fix", "Factor": 1.6},
    {"Scope": "Brasil",    "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "Brasil",    "SLC": "24X7SD", "Factor": 1.218},
    {"Scope": "Brasil",    "SLC": "24X7 4h Resp", "Factor": 1.7}
]

# ==========================================
# 2. MOTORES DE CÁLCULO
# ==========================================

def get_slc_factor(country, slc_code):
    """
    CORREGIDO: Manejo robusto de errores para evitar TypeError
    """
    # 1. Validación inicial: Si no hay código SLC, retornar default
    if not slc_code or pd.isna(slc_code):
        return 1.0
        
    scope_key = "Brasil" if country == "Brazil" else "no brasil"
    slc_str = str(slc_code).strip() # Convertir a string limpio
    
    for item in DB_SLC:
        # Comparación estricta de Scope y laxa de SLC
        if item["Scope"].lower() == scope_key.lower() and slc_str in str(item["SLC"]):
            return item["Factor"]
            
    return 1.0

def calc_duration(start, end):
    if not start or not end or end < start: return 0.0
    days = (end - start).days
    return round(days / 30.44, 1)

# ==========================================
# 3. INTERFAZ DE USUARIO
# ==========================================

st.title("🌐 LacostWeb ver19")

# --- SIDEBAR COMPACTO ---
with st.sidebar:
    st.markdown("### Configuración")
    
    # País y Moneda
    country = st.selectbox("Country", list(DB_COUNTRIES.keys()), index=3)
    country_data = DB_COUNTRIES[country]
    
    col_curr1, col_curr2 = st.columns(2)
    view_currency = col_curr1.radio("Moneda:", ["USD", "Local"], horizontal=True)
    er_val = country_data['ER'] if country_data['ER'] else 1.0
    
    # Texto pequeño para la tasa
    col_curr2.markdown(f"<small>Tasa {country_data['Curr']}:<br><b>{er_val:,.2f}</b></small>", unsafe_allow_html=True)

    # Cliente
    customer = st.text_input("Cliente", "Cliente V5")
    
    # Riesgo (Con visualización del %)
    risk_col1, risk_col2 = st.columns([2,1])
    risk_level = risk_col1.selectbox("QA Risk", list(DB_RISK.keys()))
    risk_pct = DB_RISK[risk_level]
    risk_col2.markdown(f"<br><b>{risk_pct*100}%</b>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Fechas
    c_date1, c_date2 = st.columns(2)
    start_date = c_date1.date_input("Inicio", date.today())
    end_date = c_date2.date_input("Fin", date.today().replace(year=date.today().year + 1))
    
    contract_duration = calc_duration(start_date, end_date)
    st.caption(f"Duración: {contract_duration} meses")
    
    # Costo Distribuido (SIN BOTONES +/-)
    # Usamos step=0.0 para deshabilitar los steppers visuales en muchos navegadores
    dist_cost_input = st.number_input("Distributed Cost (Póliza)", min_value=0.0, value=100.0, step=0.0, format="%.2f")
    
    st.markdown("---")
    target_gp = st.slider("Target GP %", 0.0, 1.0, 0.40, 0.01)

# --- TABLA CENTRAL ---

st.subheader("📋 Servicios")

if "df_services" not in st.session_state:
    data = {
        "Offering": ["IBM Customized Support for Multivendor Hardware Services"],
        "SLC": ["9X5NBD"],
        "QTY": [1],
        "Unit Cost (USD)": [100.0] 
    }
    st.session_state.df_services = pd.DataFrame(data)

column_config = {
    "Offering": st.column_config.SelectboxColumn("Offering", options=list(DB_OFFERINGS.keys()), width="large"),
    "SLC": st.column_config.SelectboxColumn("SLC", options=["9X5NBD", "24X7SD", "24X7 4h Resp", "24X7 6h Fix"], width="medium"),
    "Unit Cost (USD)": st.column_config.NumberColumn("Costo Unit. (USD)", format="$%.2f", min_value=0.0),
    "QTY": st.column_config.NumberColumn("Cant", min_value=1, step=1)
}

edited_df = st.data_editor(
    st.session_state.df_services,
    num_rows="dynamic",
    use_container_width=True,
    column_config=column_config,
    key="editor"
)

# ==========================================
# 4. ENGINE DE CÁLCULO
# ==========================================

if not edited_df.empty:
    
    num_rows = len(edited_df)
    # Evitar división por cero si borran todas las filas
    cost_per_row_dist = dist_cost_input / num_rows if num_rows > 0 else 0
    
    results = []
    total_cost_usd = 0.0
    
    for idx, row in edited_df.iterrows():
        # Extracción segura de datos
        offering = str(row.get("Offering", ""))
        offering_data = DB_OFFERINGS.get(offering, {"L40": "N/A", "Conga": "N/A"})
        
        slc = row.get("SLC", "")
        # Safe float conversion
        try: qty = float(row.get("QTY", 0))
        except: qty = 0.0
            
        try: unit_cost_usd = float(row.get("Unit Cost (USD)", 0.0))
        except: unit_cost_usd = 0.0
        
        # Cálculo Factor (Función corregida)
        slc_factor = get_slc_factor(country, slc)
        
        # Matemáticas V5
        base_line_cost = (unit_cost_usd * qty * contract_duration * slc_factor) 
        total_line_cost = base_line_cost + cost_per_row_dist
        
        total_cost_usd += total_line_cost
        
        results.append({
            "Offering": offering,
            "L40": offering_data["L40"],
            "SLC Factor": slc_factor,
            "Base USD": base_line_cost,
            "Dist. Cost": cost_per_row_dist,
            "Total USD": total_line_cost
        })
        
    df_results = pd.DataFrame(results)
    
    # ==========================================
    # 5. RESULTADOS
    # ==========================================
    
    st.divider()
    
    # Financial Logic
    contingency_amt = total_cost_usd * risk_pct
    cost_with_risk = total_cost_usd + contingency_amt
    
    safe_gp = 0.99 if target_gp >= 1.0 else target_gp
    sell_price_usd = cost_with_risk / (1 - safe_gp)
    
    taxes_usd = sell_price_usd * country_data['Tax']
    final_price_usd = sell_price_usd + taxes_usd
    
    # Currency View Logic
    disp_factor = er_val if view_currency == "Local" else 1.0
    sym = country_data['Curr'] if view_currency == "Local" else "USD"
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo Total", f"{total_cost_usd * disp_factor:,.2f} {sym}")
    c2.metric(f"Contingencia ({risk_pct*100}%)", f"{contingency_amt * disp_factor:,.2f} {sym}")
    c3.metric(f"Venta (GP {target_gp*100:.0f}%)", f"{sell_price_usd * disp_factor:,.2f} {sym}")
    c4.metric("Precio Final (+Tax)", f"{final_price_usd * disp_factor:,.2f} {sym}")

    with st.expander("Ver detalle técnico"):
        st.dataframe(df_results)

    # Export
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_results.to_excel(writer, sheet_name='Detalle', index=False)
        pd.DataFrame([{
            "Total Cost": total_cost_usd,
            "Risk": contingency_amt,
            "Sell Price": sell_price_usd,
            "Final Price": final_price_usd
        }]).to_excel(writer, sheet_name='Resumen', index=False)
        
    st.download_button("📥 Descargar Excel", buffer, f"LacostWeb_V19_{customer}.xlsx")
