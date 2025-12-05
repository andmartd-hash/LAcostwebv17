import streamlit as st
import pandas as pd
from datetime import date
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="LacostWeb ver19", layout="wide", page_icon="🌐")

# --- ESTILOS CSS (Ajustes Visuales) ---
st.markdown("""
    <style>
    /* 1. Reducir espacio superior (Subir secciones) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
    }
    
    /* 2. Reducir tamaño fuente Sidebar */
    section[data-testid="stSidebar"] {
        font-size: 11px !important;
        width: 260px !important;
        padding-top: 0rem !important; /* Subir contenido del sidebar también */
    }
    section[data-testid="stSidebar"] label {
        font-size: 11px !important;
        font-weight: bold;
    }
    section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] select {
        font-size: 11px !important;
        height: 1.8rem;
        min-height: 1.8rem;
    }
    
    /* 3. Quitar botones +/- de inputs numéricos */
    /* Para navegadores Webkit (Chrome, Safari) */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    /* Para Firefox */
    input[type=number] {
        -moz-appearance: textfield;
    }
    /* Ocultar botones de Streamlit específicamente */
    [data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {
        display: none !important;
    }
    
    /* 4. Tabla Ancho Completo */
    .stDataFrame, iframe[title="streamlit.data_editor"] {
        width: 100% !important;
    }
    
    /* 5. Botones de acción visibles y grandes */
    div.stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASES DE DATOS (V5 Data)
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
    "Relocation Services - Packaging": {"L40": "6942-54E", "Conga": "Location Based Services"},
    "1-HWMA MVS SPT other Prod": {"L40": "6942-0IC", "Conga": "Conga by CSV"}
}

DB_RISK = {"Low": 0.02, "Medium": 0.05, "High": 0.08}

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
# 2. LOGICA DE NEGOCIO
# ==========================================

def get_slc_factor(country, slc_code):
    if not slc_code or pd.isna(slc_code) or str(slc_code).strip() == "":
        return 1.0
    scope_key = "Brasil" if country == "Brazil" else "no brasil"
    slc_str = str(slc_code).strip()
    for item in DB_SLC:
        try:
            if item["Scope"].lower() == scope_key.lower() and slc_str in str(item["SLC"]):
                return float(item.get("Factor", 1.0))
        except: continue
    return 1.0

def calc_months(start, end):
    if not start or not end: return 0.0
    try:
        d_start = pd.to_datetime(start).date() if isinstance(start, (pd.Timestamp, str)) else start
        d_end = pd.to_datetime(end).date() if isinstance(end, (pd.Timestamp, str)) else end
        if d_end < d_start: return 0.0
        days = (d_end - d_start).days
        return round(days / 30.44, 1)
    except: return 0.0

# ==========================================
# 3. INTERFAZ: SIDEBAR
# ==========================================

st.title("🌐 LacostWeb ver19")

with st.sidebar:
    st.markdown("### Initial Information")  # CAMBIO REALIZADO
    
    country = st.selectbox("Country", list(DB_COUNTRIES.keys()), index=3)
    country_data = DB_COUNTRIES[country]
    er_val = country_data['ER'] if country_data['ER'] else 1.0
    
    # Este selector ahora solo controla la vista, ambos campos son editables
    currency_mode = st.radio("Currency Mode", ["USD", "Local"], horizontal=True)
    st.caption(f"Tasa {country_data['Curr']}: {er_val:,.2f}")

    risk_col1, risk_col2 = st.columns([0.7, 0.3])
    qa_risk = risk_col1.selectbox("QA Risk", list(DB_RISK.keys()))
    risk_pct = DB_RISK[qa_risk]
    risk_col2.markdown(f"<div style='padding-top:1.5rem;font-size:10px;font-weight:bold'>{risk_pct*100}%</div>", unsafe_allow_html=True)

    customer_name = st.text_input("Customer Name", "Cliente Ejemplo")
    customer_number = st.text_input("Customer Number", "000000")
    
    col_d1, col_d2 = st.columns(2)
    start_date = col_d1.date_input("Start Date", date.today())
    end_date = col_d2.date_input("End Date", date.today().replace(year=date.today().year + 1))
    
    contract_period = calc_months(start_date, end_date)
    st.text_input("Period (Months)", value=f"{contract_period}", disabled=True)
    
    # Input Póliza sin botones +/- (step=0.0 elimina los controles en Streamlit)
    dist_cost = st.number_input("Distributed Cost (Poliza)", min_value=0.0, value=100.0, step=0.0)
    
    st.markdown("---")
    target_gp = st.slider("Target GP %", 0.0, 1.0, 0.40, 0.01)

# ==========================================
# 4. GESTIÓN DE ESTADO Y TABLA
# ==========================================

st.subheader("📋 TABLA DE DATOS (CENTRO)")

# Inicializar Dataframe
if "df_data" not in st.session_state:
    data = {
        "Offering": ["IBM Customized Support for Multivendor Hardware Services"],
        "L40": ["6942-76T"],
        "Go to Conga": ["Location Based Services"],
        "Description": ["Soporte Base"],
        "QTY": [1],
        "Start Service Date": [date.today()],
        "End Service Date": [date.today().replace(year=date.today().year + 1)],
        "Duration": [12.0],
        "SLC": ["9X5NBD"],
        "Unit Cost USD": [100.0],
        "Unit Cost Local": [100.0 * er_val]
    }
    st.session_state.df_data = pd.DataFrame(data)

# --- BOTONES DE ACCIÓN (VISIBLES ARRIBA) ---
col_act1, col_act2, col_act3 = st.columns([1, 1, 5])
with col_act1:
    if st.button("➕ Agregar Fila", use_container_width=True):
        new_row = pd.DataFrame({
            "Offering": ["IBM Customized Support for Multivendor Hardware Services"],
            "L40": [""], "Go to Conga": [""], "Description": [""],
            "QTY": [1], "Start Service Date": [date.today()], "End Service Date": [date.today().replace(year=date.today().year + 1)],
            "Duration": [12.0], "SLC": ["9X5NBD"],
            "Unit Cost USD": [0.0], "Unit Cost Local": [0.0]
        })
        st.session_state.df_data = pd.concat([st.session_state.df_data, new_row], ignore_index=True)
        st.rerun()

with col_act2:
    if st.button("🗑️ Eliminar Fila", use_container_width=True):
        if len(st.session_state.df_data) > 0:
            st.session_state.df_data = st.session_state.df_data.iloc[:-1]
            st.rerun()

# --- CONFIGURACIÓN DE COLUMNAS ---
# Ambos costos son editables (disabled=False por defecto)
col_config = {
    "Offering": st.column_config.SelectboxColumn("Offering", options=list(DB_OFFERINGS.keys()), width="medium", required=True),
    "L40": st.column_config.TextColumn("L40", width="small", disabled=True),
    "Go to Conga": st.column_config.TextColumn("Go to Conga", width="small", disabled=True),
    "Description": st.column_config.TextColumn("Description", width="small"),
    "QTY": st.column_config.NumberColumn("QTY", width="small", min_value=1),
    "Start Service Date": st.column_config.DateColumn("Start Date", width="small"),
    "End Service Date": st.column_config.DateColumn("End Date", width="small"),
    "Duration": st.column_config.NumberColumn("Dur.", width="small", disabled=True),
    "SLC": st.column_config.SelectboxColumn("SLC", options=["9X5NBD", "24X7SD", "24X7 4h Resp", "24X7 6h Fix"], width="small"),
    # AMBOS CAMPOS EDITABLES
    "Unit Cost USD": st.column_config.NumberColumn("Unit USD", width="small", required=True),
    "Unit Cost Local": st.column_config.NumberColumn("Unit Local", width="small", required=True)
}

# --- EDITOR DE DATOS ---
# Usamos num_rows="fixed" para que los botones controlen la filas
edited_df = st.data_editor(
    st.session_state.df_data,
    num_rows="fixed", 
    use_container_width=True,
    column_config=col_config,
    key="main_editor"
)

# ==========================================
# 5. ENGINE DE CÁLCULO (Bidireccional)
# ==========================================

if not edited_df.empty:
    
    # Detectar cambios específicos para sincronizar monedas
    # Accedemos al estado del editor para saber qué celda cambió exactamente
    editor_state = st.session_state.get("main_editor", {})
    edited_rows = editor_state.get("edited_rows", {})
    
    # Flag para saber si necesitamos actualizar la tabla visualmente
    needs_rerun = False
    
    # Procesamiento
    rows_count = len(edited_df)
    dist_cost_per_row = dist_cost / rows_count if rows_count > 0 else 0
    
    calculated_rows = []
    total_cost_usd_accum = 0.0
    
    for idx, row in edited_df.iterrows():
        
        # 1. Lógica de Sincronización de Moneda
        # Si el usuario editó esta fila en el editor...
        u_cost_usd = float(row.get("Unit Cost USD", 0))
        u_cost_local = float(row.get("Unit Cost Local", 0))
        
        if idx in edited_rows:
            changes = edited_rows[idx]
            if "Unit Cost Local" in changes:
                # Usuario editó Local -> Recalcular USD
                u_cost_local = float(changes["Unit Cost Local"])
                u_cost_usd = u_cost_local / er_val if er_val else 0.0
                # Actualizamos el dataframe base para persistir el cambio
                st.session_state.df_data.at[idx, "Unit Cost USD"] = u_cost_usd
                st.session_state.df_data.at[idx, "Unit Cost Local"] = u_cost_local
                needs_rerun = True
            elif "Unit Cost USD" in changes:
                # Usuario editó USD -> Recalcular Local
                u_cost_usd = float(changes["Unit Cost USD"])
                u_cost_local = u_cost_usd * er_val
                st.session_state.df_data.at[idx, "Unit Cost USD"] = u_cost_usd
                st.session_state.df_data.at[idx, "Unit Cost Local"] = u_cost_local
                needs_rerun = True
        
        # Si no hubo edición directa, aseguramos consistencia basada en el modo actual
        # (Opcional: Si cambias de país, esto actualiza todo)
        # Por defecto confiamos en el valor que está en el DF
        
        # 2. Resto de cálculos
        off_name = str(row.get("Offering", ""))
        off_db = DB_OFFERINGS.get(off_name, {"L40": "", "Conga": ""})
        
        s_date = row.get("Start Service Date")
        e_date = row.get("End Service Date")
        duration_line = calc_months(s_date, e_date)
        
        slc_val = row.get("SLC", "")
        slc_factor = get_slc_factor(country, slc_val)
        
        try: qty = float(row.get("QTY", 1))
        except: qty = 1.0
            
        base_line = (u_cost_usd * qty * duration_line * slc_factor)
        line_total_usd = base_line + dist_cost_per_row
        total_cost_usd_accum += line_total_usd
        
        calculated_rows.append({
            **row,
            "L40": off_db["L40"],
            "Go to Conga": off_db["Conga"],
            "Duration": duration_line,
            "Unit Cost USD": u_cost_usd,
            "Unit Cost Local": u_cost_local,
            "_LineTotalUSD": line_total_usd
        })

    # Si hubo sincronización de monedas, recargamos la app para que la tabla se actualice
    if needs_rerun:
        st.rerun()

    # ==========================================
    # 6. RESULTADOS
    # ==========================================
    
    st.divider()
    st.subheader("💰 Resumen Financiero")
    
    contingency_val = total_cost_usd_accum * risk_pct
    cost_base = total_cost_usd_accum + contingency_val
    safe_gp = 0.99 if target_gp >= 1.0 else target_gp
    sell_price = cost_base / (1 - safe_gp)
    taxes = sell_price * country_data['Tax']
    final_price = sell_price + taxes
    
    # Visualización
    factor = er_val if currency_mode == "Local" else 1.0
    sym = country_data['Curr'] if currency_mode == "Local" else "USD"
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("TOTAL COST", f"{total_cost_usd_accum * factor:,.2f} {sym}")
    k2.metric(f"CONTINGENCY ({risk_pct*100}%)", f"{contingency_val * factor:,.2f} {sym}")
    k3.metric(f"SELL PRICE (Revenue)", f"{sell_price * factor:,.2f} {sym}")
    k4.metric("FINAL PRICE (+Tax)", f"{final_price * factor:,.2f} {sym}")
    
    if st.button("💾 Descargar Excel Calculado"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export = pd.DataFrame(calculated_rows)
            if "_LineTotalUSD" in df_export.columns: df_export = df_export.drop(columns=["_LineTotalUSD"])
            df_export.to_excel(writer, sheet_name='Input Processed', index=False)
            
            summary_data = {
                "KPI": ["Customer", "Risk", "Total Cost USD", "Sell Price USD", "Final Price USD", "GP Target"],
                "Value": [customer_name, risk_pct, total_cost_usd_accum, sell_price, final_price, target_gp]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Pricing Summary', index=False)
            
        st.download_button("📥 Click para descargar", output, f"Lacost_{customer_name}_V19.xlsx", "application/vnd.ms-excel")
