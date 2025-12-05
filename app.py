import streamlit as st
import pandas as pd
from datetime import date
import io

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="LAcostWeb V20 - AutoFix", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1 { color: #0F62FE; }
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASES DE DATOS
# ==========================================
DB_COUNTRIES = pd.DataFrame([
    {"Country": "Argentina", "Currency_Code": "ARS", "Exchange_Rate": 1428.95, "Tax_Rate": 0.0529},
    {"Country": "Brazil",    "Currency_Code": "BRL", "Exchange_Rate": 5.34,    "Tax_Rate": 0.1425},
    {"Country": "Chile",     "Currency_Code": "CLP", "Exchange_Rate": 934.70,  "Tax_Rate": 0.0},
    {"Country": "Colombia",  "Currency_Code": "COP", "Exchange_Rate": 3775.22, "Tax_Rate": 0.01},
    {"Country": "Ecuador",   "Currency_Code": "USD", "Exchange_Rate": 1.0,     "Tax_Rate": 0.0},
    {"Country": "Peru",      "Currency_Code": "PEN", "Exchange_Rate": 3.37,    "Tax_Rate": 0.0},
    {"Country": "Mexico",    "Currency_Code": "MXN", "Exchange_Rate": 18.42,   "Tax_Rate": 0.0},
    {"Country": "Uruguay",   "Currency_Code": "UYU", "Exchange_Rate": 39.73,   "Tax_Rate": 0.0},
    {"Country": "Venezuela", "Currency_Code": "VES", "Exchange_Rate": 235.28,  "Tax_Rate": 0.0155},
    {"Country": "USA",       "Currency_Code": "USD", "Exchange_Rate": 1.0,     "Tax_Rate": 0.0}
])

DB_RISK = pd.DataFrame({
    "Risk_Level": ["Low", "Medium", "High"],
    "Contingency": [0.02, 0.05, 0.08]
})

# ==========================================
# 2. FUNCIONES INTELIGENTES
# ==========================================

def encontrar_encabezado(file_obj, es_csv=False):
    """Busca en las primeras 20 filas dónde empiezan los datos reales"""
    try:
        if es_csv:
            # Prueba con coma y punto y coma
            preview = pd.read_csv(file_obj, nrows=20, header=None, sep=None, engine='python')
        else:
            preview = pd.read_excel(file_obj, nrows=20, header=None)
        
        # Buscamos la fila que tenga 'Currency' y 'Unit Cost' (ignorando mayúsculas)
        for idx, row in preview.iterrows():
            row_str = row.astype(str).str.upper().tolist()
            # Criterio: Debe tener al menos estas 2 palabras clave
            if any("CURRENCY" in s for s in row_str) and any("COST" in s for s in row_str):
                return idx
        return 0 # Si no encuentra, asume fila 0
    except:
        return 0

def normalizar_columnas(df):
    """Renombra columnas parecidas al estándar requerido"""
    # 1. Quitar espacios
    df.columns = [str(c).strip() for c in df.columns]
    
    # 2. Mapa de sinónimos
    mapa = {
        'UNIT COST': 'Unit Cost', 'COSTO UNITARIO': 'Unit Cost', 'COST': 'Unit Cost',
        'CURRENCY': 'Currency', 'MONEDA': 'Currency', 'CURR': 'Currency',
        'UNIT LOC': 'Unit Loc', 'LOCATION': 'Unit Loc', 'PAIS': 'Unit Loc', 'COUNTRY': 'Unit Loc',
        'OFFERING': 'Offering', 'SERVICIO': 'Offering', 'ITEM': 'Offering',
        'ER': 'ER', 'TASA': 'ER', 'EXCHANGE RATE': 'ER'
    }
    
    new_cols = {}
    for col in df.columns:
        upper_col = col.upper()
        if upper_col in mapa:
            new_cols[col] = mapa[upper_col]
            
    return df.rename(columns=new_cols)

# ==========================================
# 3. INTERFAZ Y LÓGICA
# ==========================================

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/51/IBM_logo.svg", width=80)
    st.header("Configuración Global")
    
    country_opts = sorted(DB_COUNTRIES["Country"].unique())
    sel_country = st.selectbox("País", country_opts, index=country_opts.index("Colombia") if "Colombia" in country_opts else 0)
    
    row_country = DB_COUNTRIES[DB_COUNTRIES["Country"] == sel_country].iloc[0]
    er_default = float(row_country["Exchange_Rate"])
    tax_default = float(row_country["Tax_Rate"])
    
    er_input = st.number_input("Tasa Cambio (ER)", value=er_default)
    tax_input = st.number_input("Impuestos (%)", value=tax_default, format="%.4f")
    
    st.markdown("---")
    gp_input = st.number_input("GP Objetivo (%)", value=40.0)
    risk_sel = st.selectbox("Riesgo", DB_RISK["Risk_Level"])
    risk_val = float(DB_RISK[DB_RISK["Risk_Level"] == risk_sel]["Contingency"].iloc[0])

st.title(f"Cotizador V20: {sel_country}")

uploaded_file = st.file_uploader("Cargar Archivo Input", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # 1. Detectar dónde empieza la tabla
        es_csv = uploaded_file.name.endswith('.csv')
        start_row = encontrar_encabezado(uploaded_file, es_csv)
        
        # Volver al inicio del archivo para leerlo bien
        uploaded_file.seek(0)
        
        # 2. Leer archivo desde la fila detectada
        if es_csv:
            df_input = pd.read_csv(uploaded_file, header=start_row, sep=None, engine='python')
        else:
            df_input = pd.read_excel(uploaded_file, header=start_row)

        # 3. Normalizar nombres
        df_input = normalizar_columnas(df_input)
        
        # 4. Validar
        req_cols = ['Unit Loc', 'Offering', 'Unit Cost', 'Currency']
        missing = [c for c in req_cols if c not in df_input.columns]

        if missing:
            st.error("❌ Error de Columnas")
            st.write(f"No encuentro estas columnas: **{missing}**")
            st.warning("Columnas que SÍ leí en tu archivo:")
            st.code(list(df_input.columns))
            st.info("Tip: Asegúrate de que los encabezados estén en una sola fila.")
        else:
            st.success(f"✅ Archivo leído correctamente (Encabezados en fila {start_row + 1})")
            
            # --- PROCESAMIENTO ---
            
            # A. Lógica Costos
            def calc_cost(row):
                c = pd.to_numeric(row.get('Unit Cost', 0), errors='coerce') or 0
                er_row = pd.to_numeric(row.get('ER', 0), errors='coerce')
                er_final = er_row if er_row > 0 else er_input
                
                mon = str(row.get('Currency', '')).upper().strip()
                loc = str(row.get('Unit Loc', '')).upper().split('.')[0].strip()
                
                # Excepción
                if mon in ['US', 'USD'] and loc not in ['10', 'ECUADOR']:
                    return c / er_final
                return c

            df_input['Norm. Cost (USD)'] = df_input.apply(calc_cost, axis=1)
            
            # Cantidad y Duración (simulada si falta)
            if 'Qty' not in df_input.columns: df_input['Qty'] = 1
            df_input['Total Cost Base'] = df_input['Norm. Cost (USD)'] * df_input['Qty']

            # B. Lógica Pricing
            gp_dec = gp_input / 100.0
            divisor = 1 - gp_dec if (1 - gp_dec) > 0 else 1
