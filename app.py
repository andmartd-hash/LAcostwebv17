import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import io

# ==========================================
# 1. CONFIGURACIÓN E INTERFAZ GENERAL
# ==========================================
st.set_page_config(page_title="LacostWeb V20", layout="wide", page_icon="🚀")

# CSS Profesional y Compacto
st.markdown("""
    <style>
    /* Layout General */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { width: 300px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    
    /* Fuentes y Textos */
    .small-font { font-size: 11px !important; }
    label { font-size: 11px !important; font-weight: bold; }
    
    /* Tablas Compactas */
    div[data-testid="stDataEditor"] table { font-size: 10px; }
    div[data-testid="stDataEditor"] th { font-size: 10px; padding: 4px; background-color: #f8f9fa; }
    div[data-testid="stDataEditor"] td { font-size: 10px; padding: 4px; }
    
    /* Inputs Numéricos Limpios */
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    
    /* Ajuste Menús Desplegables Largos (Offerings) */
    div[data-baseweb="select"] > div { white-space: normal !important; height: auto !important; min-height: 1.8rem; }
    div[data-baseweb="popover"] div[role="listbox"] div { 
        font-size: 11px !important; white-space: normal !important; line-height: 1.2 !important; min-width: 350px !important; 
    }
    
    /* Títulos de Sección */
    .section-header { 
        font-size: 16px; font-weight: bold; color: #1565C0; border-bottom: 2px solid #1565C0; margin-top: 20px; margin-bottom: 10px; padding-bottom: 5px; 
    }
    .kpi-card {
        background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px; text-align: center;
    }
    .kpi-val { font-size: 18px; font-weight: bold; color: #2E86C1; }
    .kpi-lbl { font-size: 11px; color: #666; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MAESTROS DE DATOS (Extracto de V6-BASE)
# ==========================================

# 2.1 COUNTRIES
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

# 2.2 OFFERINGS
DB_OFFERINGS = {
    "IBM Customized Support for Multivendor Hardware Services": {"L40": "6942-76T", "Conga": "Location Based Services"},
    "IBM Support for Red Hat": {"L40": "6948-B73", "Conga": "Conga by CSV"},
    "SWMA MVS SPT other Prod": {"L40": "6942-76O", "Conga": "Conga by CSV"},
    "IBM Support for Oracle":  {"L40": "6942-42E", "Location Based Services"},
    "Relocation Services - Packaging": {"L40": "6942-54E", "Location Based Services"},
    "1-HWMA MVS SPT other Prod": {"L40": "6942-0IC", "Conga by CSV"}
}

# 2.3 SLC (Factores)
DB_SLC = [
    {"Scope": "no brasil", "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7SD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7 4h Resp", "Factor": 1.5},
    {"Scope": "Brasil",    "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "Brasil",    "SLC": "24X7SD", "Factor": 1.218},
    {"Scope": "Brasil",    "SLC": "24X7 4h Resp", "Factor": 1.7}
]

# 2.4 RISK
DB_RISK = {"Low": 0.02, "Medium": 0.05, "High": 0.08}

# 2.5 LABOR (Machine Category & Brand Rate) - Simplificado del CSV
# Estructura: {Clave_Unica: Costo}
# Nota: Asumo que los costos en DB_LABOR son en moneda local o base según tu lógica de dividir por ER.
DB_LABOR = {
    # Brazil Machine Categories
    "Brazil|System Z": 2803.85,
    "Brazil|Power HE": 1516.61,
    "Brazil|Power LE": 742.22,
    "Brazil|Storage HE": 1403.43,
    "Brazil|MVS HE": 361.36,
    # Global Brand Rates
    "ALL|Brand Rate Full - B1": 15247.99,
    "ALL|Brand Rate Full - B2": 17897.25,
    "ALL|Brand Rate Full - B3": 31500.00
}

# ==========================================
# 3. MOTORES LÓGICOS
# ==========================================

def get_slc_factor(country, slc_code):
    if not slc_code: return 1.0
    scope_key = "Brasil" if country == "Brazil" else "no brasil"
    for item in DB_SLC:
        if item["Scope"].lower() == scope_key.lower() and str(slc_code) in item["SLC"]:
            return float(item["Factor"])
    return 1.0

def calc_months(start, end):
    if not start or not end or end < start: return 0.0
    return round((end - start).days / 30.44, 1)

def get_labor_cost(country, labor_type, labor_detail):
    # Buscar primero especifico por país (Machine Category)
    key_country = f"{country}|{labor_detail}"
    if key_country in DB_LABOR:
        return DB_LABOR[key_country]
    
    # Buscar global (Brand Rate)
    key_global = f"ALL|{labor_detail}"
    if key_global in DB_LABOR:
        return DB_LABOR[key_global]
        
    return 0.0

def reset_index(df):
    df.reset_index(drop=True, inplace=True)
    df.index = np.arange(1, len(df) + 1)
    return df

# ==========================================
# 4. INTERFAZ: SIDEBAR (General Info)
# ==========================================

with st.sidebar:
    st.markdown("### 1. General Info")
    
    country = st.selectbox("Country", list(DB_COUNTRIES.keys()), index=3) # Colombia default
    country_data = DB_COUNTRIES[country]
    er_val = country_data['ER'] if country_data['ER'] else 1.0
    
    # Currency
    currency_mode = st.radio("Currency Mode", ["USD", "Local"], horizontal=True)
    st.caption(f"Exchange Rate ({country_data['Curr']}): {er_val:,.2f}")
    
    # Dates
    c_d1, c_d2 = st.columns(2)
    start_date = c_d1.date_input("Start Date", date.today())
    end_date = c_d2.date_input("End Date", date.today().replace(year=date.today().year + 1))
    period = calc_months(start_date, end_date)
    st.info(f"Contract Period: **{period} months**")
    
    # Risk & Poliza
    qa_risk = st.selectbox("QA Risk", list(DB_RISK.keys()))
    risk_pct = DB_RISK[qa_risk]
    dist_cost = st.number_input("Distributed Cost (Poliza)", min_value=0.0, step=0.0, format="%.2f")
    
    st.divider()
    target_gp = st.slider("Target GP %", 0.0, 1.0, 0.40, 0.01)

# ==========================================
# 5. HEADER PRINCIPAL
# ==========================================

col_h1, col_h2 = st.columns([1, 4])
with col_h2:
    st.markdown("<h1 style='text-align: right; color: #1565C0;'>LacostWeb V20 🚀</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: right; color: gray;'>Blueprint V6-BASE Implementation | {customer_name if 'customer_name' in locals() else 'New Quote'}</p>", unsafe_allow_html=True)

# ==========================================
# 6. SECCIÓN INPUT COSTS (Sub-Secciones)
# ==========================================

st.markdown("<div class='section-header'>2. Input Costs</div>", unsafe_allow_html=True)

# Pestañas para las sub-secciones
tab_services, tab_labor = st.tabs(["🛠️ Servicios (Offerings)", "👷 Labor (RR/BR)"])

# -------------------------------------------------------------------
# SUB-SECCIÓN A: SERVICIOS (Tabla Principal)
# -------------------------------------------------------------------
with tab_services:
    if "df_services" not in st.session_state:
        st.session_state.df_services = pd.DataFrame(columns=[
            "Offering", "L40", "Go to Conga", "Description", "QTY", 
            "Start Date", "End Date", "Duration", "SLC", "Unit USD", "Unit Local", "Del"
        ])
    
    # Barra de Entrada (Input Bar)
    with st.expander("➕ Agregar Servicio", expanded=True):
        c1, c2 = st.columns([2, 1])
        in_off = c1.selectbox("Offering", options=list(DB_OFFERINGS.keys()), key="in_off")
        in_slc = c2.selectbox("SLC", options=sorted(list(set([x["SLC"] for x in DB_SLC]))), key="in_slc")
        
        c3, c4, c5, c6 = st.columns(4)
        in_qty = c3.number_input("Qty", 1, 9999, 1, key="in_qty")
        in_desc = c4.text_input("Desc", "Soporte", key="in_desc")
        in_cost = c5.number_input("Unit Cost USD", 0.0, step=0.0, key="in_cost")
        
        if c6.button("Agregar a Tabla", use_container_width=True):
            off_data = DB_OFFERINGS.get(in_off, {"L40":"", "Conga":""})
            new_row = {
                "Offering": in_off, "L40": off_data["L40"], "Go to Conga": off_data["Conga"],
                "Description": in_desc, "QTY": in_qty, 
                "Start Date": start_date, "End Date": end_date, "Duration": period,
                "SLC": in_slc, "Unit USD": in_cost, "Unit Local": 0.0, "Del": False
            }
            st.session_state.df_services = pd.concat([st.session_state.df_services, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df_services = reset_index(st.session_state.df_services)
            st.rerun()

    # Editor de Tabla
    col_cfg_srv = {
        "Offering": st.column_config.TextColumn("Offering", width="large", disabled=True),
        "SLC": st.column_config.SelectboxColumn("SLC", options=sorted(list(set([x["SLC"] for x in DB_SLC]))), width="medium"),
        "Unit USD": st.column_config.NumberColumn("Unit USD", width="small"),
        "Unit Local": st.column_config.NumberColumn("Unit Local", width="small"),
        "Del": st.column_config.CheckboxColumn("🗑️", width="small")
    }
    
    edited_services = st.data_editor(
        st.session_state.df_services,
        column_config=col_cfg_srv,
        use_container_width=True,
        num_rows="fixed",
        hide_index=False,
        key="editor_services"
    )
    
    # Lógica de Borrado Servicios
    if not edited_services.empty:
        if edited_services["Del"].any():
            st.session_state.df_services = edited_services[~edited_services["Del"]].reset_index(drop=True)
            st.session_state.df_services = reset_index(st.session_state.df_services)
            st.rerun()

# -------------------------------------------------------------------
# SUB-SECCIÓN B: LABOR (RR/BR)
# -------------------------------------------------------------------
with tab_labor:
    if "df_labor" not in st.session_state:
        st.session_state.df_labor = pd.DataFrame(columns=["Role Type", "Role Detail", "Base Rate (DB)", "Qty", "Del"])
        
    with st.expander("➕ Agregar Labor", expanded=True):
        l1, l2, l3, l4 = st.columns([1, 2, 1, 1])
        # Filtro inteligente de roles
        role_options = list(DB_LABOR.keys())
        # Filtrar solo lo relevante para el país seleccionado + Globales
        filtered_roles = [r.split("|")[1] for r in role_options if r.startswith(country) or r.startswith("ALL")]
        
        in_role_type = l1.selectbox("Type", ["Machine Category", "Brand Rate Full"])
        in_role_det = l2.selectbox("Role Detail", filtered_roles)
        in_l_qty = l3.number_input("Hours/Qty", 1, 1000, 1)
        
        if l4.button("Add Labor", use_container_width=True):
            # Buscar costo base en DB
            cost_base = get_labor_cost(country, in_role_type, in_role_det) # Intento simple
            if cost_base == 0: # Intento con el string directo
                 cost_base = get_labor_cost(country, "Any", in_role_det)
            
            new_l_row = {
                "Role Type": in_role_type, "Role Detail": in_role_det, 
                "Base Rate (DB)": cost_base, "Qty": in_l_qty, "Del": False
            }
            st.session_state.df_labor = pd.concat([st.session_state.df_labor, pd.DataFrame([new_l_row])], ignore_index=True)
            st.session_state.df_labor = reset_index(st.session_state.df_labor)
            st.rerun()
            
    edited_labor = st.data_editor(
        st.session_state.df_labor,
        use_container_width=True,
        num_rows="fixed",
        key="editor_labor"
    )
    
    # Lógica Borrado Labor
    if not edited_labor.empty:
        if edited_labor["Del"].any():
            st.session_state.df_labor = edited_labor[~edited_labor["Del"]].reset_index(drop=True)
            st.session_state.df_labor = reset_index(st.session_state.df_labor)
            st.rerun()

# ==========================================
# 7. ENGINE DE CÁLCULO (Sección 3: Total Cost)
# ==========================================

total_services_usd = 0.0
total_labor_usd = 0.0

# 7.1 CALCULO SERVICIOS
# Fórmula: (Unit Cost * Qty * Duration * SLC) + DistCost(parcial)
rows_srv = len(edited_services)
dist_cost_unit = dist_cost / rows_srv if rows_srv > 0 else 0

for idx, row in edited_services.iterrows():
    # Independencia de Moneda
    if currency_mode == "USD":
        base_u = row["Unit USD"]
    else:
        # Convertir Local a USD para el total
        base_u = row["Unit Local"] / er_val if er_val else 0
    
    slc_f = get_slc_factor(country, row["SLC"])
    line_tot = (base_u * row["QTY"] * row["Duration"] * slc_f) + dist_cost_unit
    total_services_usd += line_tot

# 7.2 CALCULO LABOR
# Fórmula File: (Rate / ER) * Qty
for idx, row in edited_labor.iterrows():
    rate_db = row["Base Rate (DB)"]
    qty = row["Qty"]
    
    # Aplicar la división por ER según Logic_rules.csv
    # Asumimos que la DB tiene precios locales o globales que requieren conversión
    if er_val and er_val > 0:
        line_labor_usd = (rate_db / er_val) * qty
    else:
        line_labor_usd = 0
        
    total_labor_usd += line_labor_usd

GRAND_TOTAL_USD = total_services_usd + total_labor_usd

# ==========================================
# 8. PRICING & RESULTADOS (Sección 4)
# ==========================================

st.markdown("<div class='section-header'>3. & 4. Total Cost & Pricing</div>", unsafe_allow_html=True)

# Lógica Financiera
contingency = GRAND_TOTAL_USD * risk_pct
cost_w_risk = GRAND_TOTAL_USD + contingency
sell_price = cost_w_risk / (1 - target_gp) if target_gp < 1 else 0
taxes = sell_price * country_data["Tax"]
final_price = sell_price + taxes

# Factor de Visualización Final
disp_factor = er_val if currency_mode == "Local" else 1.0
sym = country_data["Curr"] if currency_mode == "Local" else "USD"

# TARJETAS KPI
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_services_usd * disp_factor:,.0f}</div><div class='kpi-lbl'>Total Servicios ({sym})</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_labor_usd * disp_factor:,.0f}</div><div class='kpi-lbl'>Total Labor ({sym})</div></div>", unsafe_allow_html=True)
with k3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-val' style='color:#E67E22'>{contingency * disp_factor:,.0f}</div><div class='kpi-lbl'>Risk ({risk_pct*100}%)</div></div>", unsafe_allow_html=True)
with k4:
    st.markdown(f"<div class='kpi-card'><div class='kpi-val' style='color:#27AE60'>{sell_price * disp_factor:,.0f}</div><div class='kpi-lbl'>Sell Price (GP {target_gp*100:.0f}%)</div></div>", unsafe_allow_html=True)
with k5:
    st.markdown(f"<div class='kpi-card'><div class='kpi-val'>{final_price * disp_factor:,.0f}</div><div class='kpi-lbl'>Final + Tax ({sym})</div></div>", unsafe_allow_html=True)

# EXPORTACIÓN
st.write("")
if st.button("💾 Descargar Cotización Completa (Excel)"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        edited_services.to_excel(writer, sheet_name='Detailed Services', index=False)
        edited_labor.to_excel(writer, sheet_name='Detailed Labor', index=False)
        
        # Resumen
        res = pd.DataFrame({
            "Concepto": ["Country", "Currency Mode", "Services Total USD", "Labor Total USD", "Risk", "Sell Price", "Final Price"],
            "Valor": [country, currency_mode, total_services_usd, total_labor_usd, contingency, sell_price, final_price]
        })
        res.to_excel(writer, sheet_name='Summary', index=False)
        
    st.download_button("📥 Click to Download", buffer, f"Lacost_V20_{customer_name}.xlsx", "application/vnd.ms-excel")
