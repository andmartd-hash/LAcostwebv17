import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# ==========================================
# 1. CONFIGURACIÓN E INTERFAZ
# ==========================================
st.set_page_config(page_title="LacostWeb V20", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
   .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    section { width: 300px!important; padding-top: 2rem; }
    /* Estilos para inputs y tablas compactas */
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    div table { font-size: 10px; }
    div th { font-size: 10px; background-color: #f0f2f6; }
    div td { font-size: 10px; }
   .kpi-card { background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px; text-align: center; }
   .kpi-val { font-size: 18px; font-weight: bold; color: #2E86C1; }
   .kpi-lbl { font-size: 11px; color: #666; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS (DATA LOADER)
# ==========================================

class PricingDataLoader:
    def __init__(self):
        self.load_data()

    def load_data(self):
        # 1. COUNTRIES
        csv_countries = """Country,Currency,ER,Tax
Argentina,ARS,1428.948633,0.0529
Brazil,BRL,5.341035,0.1425
Chile,CLP,934.704,0
Colombia,COP,3775.22225,0.01
Ecuador,USD,1.0,0
Peru,PEN,3.3729225,0
Mexico,MXN,18.420365,0
Uruguay,UYU,39.73184,0
Venezuela,VES,235.28249,0.0155"""
        self.countries_df = pd.read_csv(StringIO(csv_countries))

        # 2. SLC (Scope: Brazil vs no brazil)
        csv_slc = """Scope,SLC,UpliftFactor
no brazil,M1A,1.0
no brazil,M16,1.0
no brazil,M19,1.0
no brazil,M5B,1.05
no brazil,M47,1.5
no brazil,MJ7,1.1
no brazil,M3F,1.15
no brazil,M3B,1.2
no brazil,M33,1.3
no brazil,M2F,1.4
no brazil,M2B,1.6
no brazil,M23,1.7
Brazil,M1A,1.0
Brazil,M19,1.0
Brazil,M47,1.5
Brazil,NStdSBD6x24,1.266
Brazil,NStdFix4 7x24,1.458"""
        self.slc_df = pd.read_csv(StringIO(csv_slc))

        # 3. OFFERINGS
        csv_offering = """Offering,L40,Conga
IBM Customized Support for Hardware Services-Logo,6942-76V,Location Based Services
IBM Support for Red Hat,6948-B73,Conga by CSV
System Technical Support Service-MVS-STSS,6942-1FN,Location Based Services
Relocation Services - Packaging,6942-54E,Location Based Services"""
        self.offering_df = pd.read_csv(StringIO(csv_offering))

        # 4. LABOR (Matriz Compleja)
        # Nota: Los vacíos se manejan como NaN. Def A=System Z, C=Power HE, etc.
        csv_labor = """Scope,MC_RR,Def,Argentina,Brazil,Chile,Colombia,Ecuador,Peru,Mexico,Uruguay,Venezuela
no brazil,Machine Category,A,304504.2,,2165270.415,2054058.998,991.20735,1284.609,12857.25,30167.39,102721.98
no brazil,Machine Category,C,194856.48,,486361.26,540008.96,340.52,505.85,5857.95,18987.51,40555.17
Brazil,Machine Category,1,,2803.85,,,,,,,
Brazil,Machine Category,2,,1516.61,,,,,,,
ALL,Brand Rate Full,B1,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99"""
        self.labor_df = pd.read_csv(StringIO(csv_labor))

    # --- LOOKUPS CORREGIDOS ---
    
    def get_er(self, country):
        row = self.countries_df[self.countries_df['Country'] == country]
        return float(row.iloc) if not row.empty else 1.0
        
    def get_currency_code(self, country):
        row = self.countries_df[self.countries_df['Country'] == country]
        return str(row.iloc['Currency']) if not row.empty else "USD"

    def get_uplift(self, country, slc):
        scope = "Brazil" if country == "Brazil" else "no brazil"
        # CORRECCIÓN DE SINTAXIS AQUÍ:
        mask = (self.slc_df == scope) & (self.slc_df == slc)
        row = self.slc_df[mask]
        return float(row.iloc['UpliftFactor']) if not row.empty else 1.0

    def get_labor_rate(self, country, rr_type, definition):
        # 1. Definir Scope
        if rr_type == "Brand Rate Full":
            target_scope = "ALL"
        else:
            target_scope = "Brazil" if country == "Brazil" else "no brazil"
            
        # 2. Filtrar Fila
        mask = (self.labor_df == target_scope) & (self.labor_df == rr_type) & (self.labor_df == definition)
        row = self.labor_df[mask]
        
        if row.empty: return 0.0
        
        # 3. Extraer valor de columna País
        # Si el país no está en las columnas (ej. error de nombre), retorna 0
        if country in row.columns:
            val = row.iloc[country]
            return float(val) if pd.notna(val) else 0.0
        return 0.0

# Instanciar Loader
db = PricingDataLoader()

# ==========================================
# 3. SIDEBAR (General Info)
# ==========================================
with st.sidebar:
    st.markdown("### 1. General Info")
    country = st.selectbox("Country", db.countries_df['Country'].unique(), index=3)
    currency_mode = st.radio("Currency Mode",, horizontal=True)
    
    er = db.get_er(country)
    curr_code = db.get_currency_code(country)
    st.caption(f"Tasa {curr_code}: {er:,.2f}")
    
    # Fechas
    c1, c2 = st.columns(2)
    start_date = c1.date_input("Start", date.today())
    end_date = c2.date_input("End", date.today().replace(year=date.today().year + 1))
    
    # Cálculo duración meses
    delta = relativedelta(end_date, start_date)
    months = delta.years * 12 + delta.months
    if delta.days > 0: months += 1 # Redondeo hacia arriba
    st.info(f"Period: **{months} months**")
    
    qa_risk = st.selectbox("QA Risk", ["Low (2%)", "Medium (5%)", "High (8%)"])
    risk_map = {"Low (2%)": 0.02, "Medium (5%)": 0.05, "High (8%)": 0.08}
    risk_pct = risk_map[qa_risk]
    
    dist_cost = st.number_input("Distributed Cost", 0.0, step=0.0, format="%.2f")
    st.divider()
    target_gp = st.slider("Target GP %", 0.0, 1.0, 0.40)

# ==========================================
# 4. HEADER
# ==========================================
c_h1, c_h2 = st.columns()
with c_h2:
    st.markdown("<h1 style='text-align: right; color: #1565C0;'>LacostWeb V20 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top:0; border-color:#1565C0'>", unsafe_allow_html=True)

# ==========================================
# 5. INPUT COSTS (Servicios + Labor)
# ==========================================
st.markdown("### 2. Input Costs")
tab_srv, tab_lab = st.tabs()

# --- TABLA SERVICIOS ---
with tab_srv:
    if "df_srv" not in st.session_state:
        st.session_state.df_srv = pd.DataFrame(columns=)
    
    # Autocorrección Del
    if "Del" not in st.session_state.df_srv.columns: st.session_state.df_srv = False

    with st.expander("➕ Nuevo Servicio", expanded=False):
        c1, c2 = st.columns()
        in_off = c1.selectbox("Offering", db.offering_df['Offering'].unique())
        # Filtrar SLC según scope para que el usuario no elija mal
        scope_target = "Brazil" if country == "Brazil" else "no brazil"
        slc_opts = db.slc_df == scope_target].unique()
        in_slc = c2.selectbox("SLC", slc_opts)
        
        c3, c4 = st.columns(2)
        in_qty = c3.number_input("Qty", 1, 9999, 1)
        in_cost = c4.number_input("Unit USD", 0.0)
        
        if st.button("Agregar Fila", key="add_s"):
            new_row = {"Offering": in_off, "SLC": in_slc, "Unit USD": in_cost, "Unit Local": 0.0, "Qty": in_qty, "Del": False}
            st.session_state.df_srv = pd.concat()], ignore_index=True)
            st.rerun()

    # Editor
    col_cfg_srv = {
        "Offering": st.column_config.TextColumn(width="large", disabled=True),
        "Del": st.column_config.CheckboxColumn("🗑️", width="small")
    }
    edited_srv = st.data_editor(st.session_state.df_srv, column_config=col_cfg_srv, use_container_width=True, num_rows="fixed")
    
    # Borrado
    if not edited_srv.empty and edited_srv.any():
        st.session_state.df_srv = edited_srv].reset_index(drop=True)
        st.rerun()

# --- TABLA LABOR ---
with tab_lab:
    if "df_lab" not in st.session_state:
        st.session_state.df_lab = pd.DataFrame(columns=)
    if "Del" not in st.session_state.df_lab.columns: st.session_state.df_lab = False

    with st.expander("➕ Nueva Labor", expanded=False):
        l1, l2, l3, l4 = st.columns(4)
        in_type = l1.selectbox("Type",)
        # Filtrar definiciones disponibles en la DB para ese tipo
        avail_defs = db.labor_df == in_type].unique()
        in_def = l2.selectbox("Def", avail_defs)
        in_lqty = l3.number_input("Hrs/Qty", 1, 10000, 1)
        
        if l4.button("Agregar Labor", key="add_l"):
            # Buscar tarifa base
            rate = db.get_labor_rate(country, in_type, in_def)
            new_lrow = {"Type": in_type, "Def": in_def, "Base Rate": rate, "Qty": in_lqty, "Del": False}
            st.session_state.df_lab = pd.concat()], ignore_index=True)
            st.rerun()

    # Editor Labor
    col_cfg_lab = {
        "Del": st.column_config.CheckboxColumn("🗑️", width="small"),
        "Base Rate": st.column_config.NumberColumn(format="%.2f")
    }
    edited_lab = st.data_editor(st.session_state.df_lab, column_config=col_cfg_lab, use_container_width=True, num_rows="fixed")
    
    # Borrado
    if not edited_lab.empty and edited_lab.any():
        st.session_state.df_lab = edited_lab].reset_index(drop=True)
        st.rerun()

# ==========================================
# 6. ENGINE DE CÁLCULO
# ==========================================

tot_srv_usd = 0.0
tot_lab_usd = 0.0

# Cálculo Servicios
num_srv = len(edited_srv)
dist_unit = dist_cost / num_srv if num_srv > 0 else 0

for idx, row in edited_srv.iterrows():
    # Lógica Moneda Independiente
    u_usd = row
    u_loc = row["Unit Local"]
    
    if currency_mode == "USD":
        base = u_usd
    else:
        # Si es local, convertir a USD para sumar
        base = u_loc / er if er else 0.0
        
    uplift = db.get_uplift(country, row)
    line = (base * row["Qty"] * months * uplift) + dist_unit
    tot_srv_usd += line

# Cálculo Labor
for idx, row in edited_lab.iterrows():
    # Fórmula V6: (Machine Category / (E/R) * Qty)
    # Base Rate viene de la DB (en moneda local usualmente)
    rate = row
    qty = row["Qty"]
    
    if er > 0:
        line_lab = (rate / er) * qty
    else:
        line_lab = 0
    tot_lab_usd += line_lab

GRAND_TOTAL = tot_srv_usd + tot_lab_usd

# ==========================================
# 7. VISUALIZACIÓN FINAL
# ==========================================

st.divider()
st.subheader("3. & 4. Total Cost & Pricing")

contingency = GRAND_TOTAL * risk_pct
sell_price = (GRAND_TOTAL + contingency) / (1 - target_gp) if target_gp < 1 else 0
final_price = sell_price * (1 + 0.0) # Tax logic placeholder

# Ajuste visual moneda
d_fac = er if currency_mode == "Local" else 1.0
sym = curr_code if currency_mode == "Local" else "USD"

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f"<div class='kpi-card'><div class='kpi-val'>{tot_srv_usd*d_fac:,.0f}</div><div class='kpi-lbl'>Servicios ({sym})</div></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='kpi-card'><div class='kpi-val'>{tot_lab_usd*d_fac:,.0f}</div><div class='kpi-lbl'>Labor ({sym})</div></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='kpi-card'><div class='kpi-val' style='color:#E67E22'>{contingency*d_fac:,.0f}</div><div class='kpi-lbl'>Risk</div></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='kpi-card'><div class='kpi-val' style='color:#27AE60'>{sell_price*d_fac:,.0f}</div><div class='kpi-lbl'>Total Price</div></div>", unsafe_allow_html=True)
