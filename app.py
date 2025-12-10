import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import io

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA & ESTILOS (Blueprint UI)
# ==========================================
st.set_page_config(page_title="LacostWeb V20", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    /* Layout General */
    .block-container { padding-top: 0.5rem; padding-bottom: 5rem; }
    
    /* 1. SECCIÓN GENERAL INFO (SIDEBAR) */
    section[data-testid="stSidebar"] { width: 300px !important; padding-top: 1rem; }
    section[data-testid="stSidebar"] label { font-size: 11px !important; font-weight: bold; }
    section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] select { 
        height: 1.8rem; min-height: 1.8rem; font-size: 11px; 
    }
    
    /* 2. SECCIÓN INPUT COSTS (TABLAS) */
    div[data-testid="stDataEditor"] table { font-size: 10px !important; }
    div[data-testid="stDataEditor"] th { 
        font-size: 10px; padding: 4px; background-color: #f0f2f6; color: #31333F; min-width: 80px; 
    }
    div[data-testid="stDataEditor"] td { font-size: 10px; padding: 4px; line-height: 1.2; }
    
    /* Corrección Menús Desplegables Largos (Offerings) */
    div[data-baseweb="select"] > div { white-space: normal !important; height: auto !important; min-height: 1.8rem; }
    div[data-baseweb="popover"] div[role="listbox"] div { 
        font-size: 11px !important; white-space: normal !important; line-height: 1.3 !important; min-width: 450px !important;
    }
    
    /* 3. & 4. TOTAL COST & PRICING (KPIS) */
    .kpi-card {
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; 
        padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .kpi-val { font-size: 18px; font-weight: bold; color: #1565C0; }
    .kpi-lbl { font-size: 11px; color: #666; text-transform: uppercase; margin-top: 5px; }
    .section-title { 
        font-size: 16px; font-weight: bold; color: #1565C0; 
        border-bottom: 2px solid #1565C0; margin-top: 25px; margin-bottom: 10px; padding-bottom: 5px;
    }
    
    /* Botones */
    div.stButton > button { width: 100%; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 2px; }
    
    /* Inputs sin flechas */
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASES (Extraídas de V6-BASE.xlsx)
# ==========================================

# TABLE: COUNTRIES
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

# TABLE: OFFERING (Con claves L40 y Conga)
DB_OFFERINGS = {
    "IBM Customized Support for Multivendor Hardware Services": {"L40": "6942-76T", "Conga": "Location Based Services"},
    "IBM Support for Red Hat": {"L40": "6948-B73", "Conga": "Conga by CSV"},
    "SWMA MVS SPT other Prod": {"L40": "6942-76O", "Conga": "Conga by CSV"},
    "IBM Support for Oracle":  {"L40": "6942-42E", "Conga": "Location Based Services"},
    "Relocation Services - Packaging": {"L40": "6942-54E", "Conga": "Location Based Services"},
    "1-HWMA MVS SPT other Prod": {"L40": "6942-0IC", "Conga": "Conga by CSV"}
}

# TABLE: SLC
DB_SLC = [
    {"Scope": "no brasil", "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7SD", "Factor": 1.0},
    {"Scope": "no brasil", "SLC": "24X7 4h Resp", "Factor": 1.5},
    {"Scope": "Brasil",    "SLC": "9X5NBD", "Factor": 1.0},
    {"Scope": "Brasil",    "SLC": "24X7SD", "Factor": 1.218},
    {"Scope": "Brasil",    "SLC": "24X7 4h Resp", "Factor": 1.7}
]

# TABLE: QA_RISK
DB_RISK = {"Low": 0.02, "Medium": 0.05, "High": 0.08}

# TABLE: LABOR (Machine Category & Brand Rate)
# Extraído de Databases.csv -> Costos Base
DB_LABOR = {
    # Brazil Specific
    "Brazil|System Z": 2803.85,
    "Brazil|Power HE": 1516.61,
    "Brazil|Power LE": 742.22,
    "Brazil|Storage HE": 1403.43,
    "Brazil|MVS HE": 361.36,
    # Global / Brand Rates
    "ALL|Brand Rate Full - B1": 15247.99,
    "ALL|Brand Rate Full - B2": 17897.25,
    "ALL|Brand Rate Full - B3": 31500.00
}

# ==========================================
# 3. LOGIC ENGINE (Fórmulas de V6-BASE)
# ==========================================

def get_slc_factor(country, slc_code):
    if not slc_code: return 1.0
    scope_key = "Brasil" if country == "Brazil" else "no brasil"
    for item in DB_SLC:
        if item["Scope"].lower() == scope_key.lower() and str(slc_code) in item["SLC"]:
            return float(item["Factor"])
    return 1.0

def calc_duration(start, end):
    if not start or not end or end < start: return 0.0
    return round((end - start).days / 30.44, 1)

def get_labor_rate(country, role_type, role_detail):
    # Lógica de búsqueda jerárquica
    key_country = f"{country}|{role_detail}"
    if key_country in DB_LABOR:
        return DB_LABOR[key_country]
    key_global = f"ALL|{role_detail}"
    if key_global in DB_LABOR:
        return DB_LABOR[key_global]
    return 0.0

def safe_reset_index(df):
    """Reinicia índice en 1 para tablas UI"""
    df_new = df.reset_index(drop=True)
    df_new.index = np.arange(1, len(df_new) + 1)
    return df_new

# ==========================================
# SECCIÓN 1: GENERAL INFO (Sidebar)
# ==========================================

with st.sidebar:
    st.markdown("### 1. General Info")
    
    # Inputs Base
    country = st.selectbox("Country", list(DB_COUNTRIES.keys()), index=3)
    country_data = DB_COUNTRIES[country]
    er_val = country_data['ER'] if country_data['ER'] else 1.0
    
    currency_mode = st.radio("Currency Mode", ["USD", "Local"], horizontal=True)
    st.caption(f"Tasa de Cambio ({country_data['Curr']}): {er_val:,.2f}")
    
    c_d1, c_d2 = st.columns(2)
    start_date = c_d1.date_input("Start Date", date.today())
    end_date = c_d2.date_input("End Date", date.today().replace(year=date.today().year + 1))
    
    contract_period = calc_duration(start_date, end_date)
    st.text_input("Contract Period", value=f"{contract_period}", disabled=True)
    
    qa_risk_name = st.selectbox("QA Risk", list(DB_RISK.keys()))
    risk_pct = DB_RISK[qa_risk_name]
    
    dist_cost = st.number_input("Distributed Cost (Poliza)", min_value=0.0, step=0.0, format="%.2f")
    
    st.markdown("---")
    # Datos opcionales cliente
    c_name = st.text_input("Customer Name", "Cliente")
    target_gp = st.slider("Target GP %", 0.0, 1.0, 0.40, 0.01)

# ==========================================
# HEADER
# ==========================================
c_h1, c_h2 = st.columns([1, 4])
with c_h2:
    st.markdown(f"<h1 style='text-align: right; color: #1565C0;'>LacostWeb V20</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: right; color: gray;'>Configuración: {country} | {currency_mode}</p>", unsafe_allow_html=True)

# ==========================================
# SECCIÓN 2: INPUT COSTS
# ==========================================
st.markdown("<div class='section-title'>2. Input Costs</div>", unsafe_allow_html=True)

tab_srv, tab_lab = st.tabs(["Sub-sección: Servicios", "Sub-sección: Labor (RR/BR)"])

# --- TABLA SERVICIOS ---
with tab_srv:
    if "df_srv" not in st.session_state:
        st.session_state.df_srv = pd.DataFrame(columns=[
            "Offering", "L40", "Go to Conga", "Description", "QTY", 
            "Start Date", "End Date", "Duration", "SLC", "Unit USD", "Unit Local", "Del"
        ])
    
    if "Del" not in st.session_state.df_srv.columns: st.session_state.df_srv["Del"] = False

    # Barra Input
    with st.expander("➕ Nuevo Servicio", expanded=False):
        c1, c2 = st.columns([3, 1])
        in_off = c1.selectbox("Offering", options=list(DB_OFFERINGS.keys()))
        in_slc = c2.selectbox("SLC", options=sorted(list(set([x["SLC"] for x in DB_SLC]))))
        
        c3, c4, c5, c6 = st.columns(4)
        in_qty = c3.number_input("Qty", 1, 99999, 1)
        in_desc = c4.text_input("Descripción", "Soporte")
        in_cost_usd = c5.number_input("Unit Cost USD", 0.0, step=0.0)
        
        if c6.button("Agregar Fila", key="add_srv"):
            off_data = DB_OFFERINGS.get(in_off, {"L40":"", "Conga":""})
            new_row = {
                "Offering": in_off, "L40": off_data["L40"], "Go to Conga": off_data["Conga"],
                "Description": in_desc, "QTY": in_qty, 
                "Start Date": start_date, "End Date": end_date, "Duration": contract_period,
                "SLC": in_slc, "Unit USD": in_cost_usd, "Unit Local": 0.0, "Del": False
            }
            st.session_state.df_srv = pd.concat([st.session_state.df_srv, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df_srv = safe_reset_index(st.session_state.df_srv)
            st.rerun()

    # Editor
    cfg_srv = {
        "Offering": st.column_config.TextColumn("Offering", width="large", disabled=True),
        "SLC": st.column_config.SelectboxColumn("SLC", options=sorted(list(set([x["SLC"] for x in DB_SLC]))), width="medium"),
        "Unit USD": st.column_config.NumberColumn("Unit USD", width="small"),
        "Unit Local": st.column_config.NumberColumn("Unit Local", width="small"),
        "Del": st.column_config.CheckboxColumn("🗑️", width="small")
    }
    
    ed_srv = st.data_editor(
        st.session_state.df_srv, column_config=cfg_srv, 
        use_container_width=True, num_rows="fixed", hide_index=False, key="ed_srv"
    )
    
    # Borrado Seguro
    if not ed_srv.empty and ed_srv["Del"].any():
        st.session_state.df_srv = ed_srv[~ed_srv["Del"]]
        st.session_state.df_srv = safe_reset_index(st.session_state.df_srv)
        st.rerun()

# --- TABLA LABOR ---
with tab_lab:
    if "df_lab" not in st.session_state:
        st.session_state.df_lab = pd.DataFrame(columns=["Role Type", "Role Detail", "Base Rate", "Qty", "Del"])
    
    if "Del" not in st.session_state.df_lab.columns: st.session_state.df_lab["Del"] = False

    # Barra Input
    with st.expander("➕ Nueva Labor", expanded=False):
        l1, l2, l3, l4 = st.columns([2, 2, 1, 1])
        in_rtype = l1.selectbox("Type", ["Machine Category", "Brand Rate Full"])
        
        # Filtro inteligente pero permisivo: Muestra todo lo que coincida con el tipo
        avail_roles = sorted([k.split("|")[1] for k in DB_LABOR.keys() if k.startswith(in_rtype)])
        in_rdet = l2.selectbox("Role Detail", avail_roles)
        in_lqty = l3.number_input("Qty/Hours", 1, 99999, 1)
        
        if l4.button("Agregar Fila", key="add_lab"):
            rate_db = get_labor_rate(country, in_rtype, in_rdet)
            new_lrow = {
                "Role Type": in_rtype, "Role Detail": in_rdet, 
                "Base Rate": rate_db, "Qty": in_lqty, "Del": False
            }
            st.session_state.df_lab = pd.concat([st.session_state.df_lab, pd.DataFrame([new_lrow])], ignore_index=True)
            st.session_state.df_lab = safe_reset_index(st.session_state.df_lab)
            st.rerun()

    # Editor
    cfg_lab = {
        "Role Detail": st.column_config.TextColumn("Role Detail", width="medium"),
        "Base Rate": st.column_config.NumberColumn("Base Rate", format="%.2f"),
        "Del": st.column_config.CheckboxColumn("🗑️", width="small")
    }
    
    ed_lab = st.data_editor(
        st.session_state.df_lab, column_config=cfg_lab,
        use_container_width=True, num_rows="fixed", hide_index=False, key="ed_lab"
    )
    
    # Borrado Seguro
    if not ed_lab.empty and ed_lab["Del"].any():
        st.session_state.df_lab = ed_lab[~ed_lab["Del"]]
        st.session_state.df_lab = safe_reset_index(st.session_state.df_lab)
        st.rerun()

# ==========================================
# CÁLCULOS (ENGINE LÓGICO)
# ==========================================

subtotal_srv = 0.0
subtotal_lab = 0.0

# 1. SERVICIOS (Lógica Independencia Moneda)
dist_per_row = dist_cost / len(ed_srv) if len(ed_srv) > 0 else 0

for idx, row in ed_srv.iterrows():
    # Raw Inputs
    u_usd = pd.to_numeric(row.get("Unit USD"), errors='coerce') or 0.0
    u_loc = pd.to_numeric(row.get("Unit Local"), errors='coerce') or 0.0
    
    # Decisión basada en Currency Mode
    if currency_mode == "USD":
        base_rate = u_usd
    else:
        base_rate = u_loc / er_val if er_val else 0.0
    
    # Factores
    slc_f = get_slc_factor(country, row.get("SLC"))
    qty = row.get("QTY", 0)
    dur = row.get("Duration", 0)
    
    # Formula V6
    line_total = (base_rate * qty * dur * slc_f) + dist_per_row
    subtotal_srv += line_total

# 2. LABOR (Lógica Formula: Rate / ER * Qty)
for idx, row in ed_lab.iterrows():
    rate = row.get("Base Rate", 0.0)
    qty = row.get("Qty", 0.0)
    
    if er_val > 0:
        line_total = (rate / er_val) * qty
    else:
        line_total = 0.0
    subtotal_lab += line_total

GRAND_TOTAL = subtotal_srv + subtotal_lab

# ==========================================
# SECCIÓN 3 & 4: TOTAL & PRICING
# ==========================================

st.markdown("<div class='section-title'>3. Total Cost & 4. Pricing</div>", unsafe_allow_html=True)

# Math V6
contingency = GRAND_TOTAL * risk_pct
cost_w_risk = GRAND_TOTAL + contingency
sell_price = cost_w_risk / (1 - target_gp) if target_gp < 1 else 0
final_price = sell_price * (1 + country_data["Tax"])

# Display Logic
d_fac = er_val if currency_mode == "Local" else 1.0
sym = country_data["Curr"] if currency_mode == "Local" else "USD"

k1, k2, k3, k4, k5 = st.columns(5)

def kpi(col, val, lbl, color="#1565C0"):
    col.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-val' style='color:{color}'>{val:,.0f}</div>
            <div class='kpi-lbl'>{lbl}</div>
        </div>
    """, unsafe_allow_html=True)

kpi(k1, subtotal_srv * d_fac, f"Servicios ({sym})")
kpi(k2, subtotal_lab * d_fac, f"Labor ({sym})")
kpi(k3, contingency * d_fac, f"Risk ({risk_pct*100:.0f}%)", "#E67E22")
kpi(k4, sell_price * d_fac, f"Sell Price (GP {target_gp*100:.0f}%)", "#27AE60")
kpi(k5, final_price * d_fac, f"Final + Tax ({sym})")

# Export
st.write("")
if st.button("💾 Descargar Excel"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        ed_srv.to_excel(writer, sheet_name='Services', index=False)
        ed_lab.to_excel(writer, sheet_name='Labor', index=False)
        pd.DataFrame({
            "Metric": ["Total Services USD", "Total Labor USD", "Risk", "Sell Price", "Final Price"],
            "Value": [subtotal_srv, subtotal_lab, contingency, sell_price, final_price]
        }).to_excel(writer, sheet_name='Summary', index=False)
    st.download_button("📥 Click para descargar", buffer, f"Lacost_V20.xlsx", "application/vnd.ms-excel")
