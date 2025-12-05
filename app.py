import streamlit as st
import pandas as pd
from datetime import date
import io

# ==========================================
# 0. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="LAcostWeb V19 - Master", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1 { color: #0F62FE; }
    div[data-testid="stMetric"] { background-color: #ffffff; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASES DE DATOS (INTEGRADAS DEL V5)
# ==========================================

# DB COUNTRIES (De tu archivo countries.csv)
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

# DB RISK (De tu archivo QA Risk.csv)
DB_RISK = pd.DataFrame({
    "Risk_Level": ["Low", "Medium", "High"],
    "Contingency": [0.02, 0.05, 0.08]
})

# DB OFFERINGS (De tu archivo Offering.csv - Simulando columna Scope)
# NOTA: He agregado la columna 'Scope' basada en tu lógica (Brasil vs No Brasil)
data_offerings = [
    {"Offering": "IBM Hardware Resell-Lenovo", "L40": "6942-1BT", "Scope": "no brasil"},
    {"Offering": "1-HWMA MVS SPT other Prod",  "L40": "6942-0IC", "Scope": "no brasil"},
    {"Offering": "SWMA MVS SPT other Prod",    "L40": "6942-76O", "Scope": "no brasil"},
    {"Offering": "IBM Support for Red Hat",    "L40": "6948-B73", "Scope": "all"},
    {"Offering": "Servicio Especial Brasil",   "L40": "BR-9999",  "Scope": "brasil"}, # Ejemplo
    {"Offering": "Relocation Services",        "L40": "6942-54E", "Scope": "no brasil"}
]
DB_OFFERINGS = pd.DataFrame(data_offerings)

# ==========================================
# 2. FUNCIONES DE LÓGICA DE NEGOCIO
# ==========================================

def get_country_params(country):
    """Obtiene Tasa de Cambio y Tax Rate del país seleccionado"""
    row = DB_COUNTRIES[DB_COUNTRIES["Country"] == country]
    if not row.empty:
        return row.iloc[0]["Exchange_Rate"], row.iloc[0]["Tax_Rate"], row.iloc[0]["Currency_Code"]
    return 1.0, 0.0, "USD"

def calcular_meses(start, end):
    """Calcula meses entre fechas"""
    try:
        if pd.isnull(start) or pd.isnull(end): return 0.0
        # Aseguramos formato fecha
        s = pd.to_datetime(start)
        e = pd.to_datetime(end)
        days = (e - s).days
        if days < 0: return 0.0
        return round(days / 30.44, 2)
    except:
        return 0.0

def procesar_costos(df, er_sidebar):
    """
    Hoja COST: Aplica reglas de normalización y excepción Ecuador.
    """
    # 1. Calcular Duración
    df['Duration (Months)'] = df.apply(lambda x: calcular_meses(x.get('Start Date'), x.get('End Date')), axis=1)

    # 2. Lógica Costo Unitario Real
    def calc_unit_real(row):
        costo = pd.to_numeric(row.get('Unit Cost', 0), errors='coerce') or 0.0
        moneda = str(row.get('Currency', '')).strip().upper()
        # ER de la fila (si existe) o del Sidebar
        er_row = pd.to_numeric(row.get('ER', 0), errors='coerce')
        er_used = er_row if er_row > 0 else er_sidebar
        
        # Limpieza Unit Loc
        raw_loc = str(row.get('Unit Loc', '')).strip()
        unit_loc = raw_loc.split('.')[0].upper()
        
        # Regla Excepción
        es_excepcion = unit_loc in ['10', 'ECUADOR']
        es_dolar = moneda in ['US', 'USD']

        # FÓRMULA COSTO:
        # Si es US y NO es excepción -> Dividir por ER (según tu lógica previa)
        # Nota: Ajusta esto si tu lógica V5 cambió. Asumo que mantenemos la V18.
        if es_dolar and not es_excepcion:
            return costo / er_used if er_used else 0
        else:
            return costo

    df['Norm. Unit Cost (USD)'] = df.apply(calc_unit_real, axis=1)
    
    # 3. Costo Total
    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(1)
    df['Total Cost (USD)'] = df['Norm. Unit Cost (USD)'] * df['Qty'] * df['Duration (Months)']
    
    return df

def procesar_pricing(df, risk_val, tax_rate, gp_percent):
    """
    Hoja PRICING: Aplica Risk, GP y Tax.
    """
    gp_decimal = gp_percent / 100.0
    divisor = 1 - gp_decimal
    if divisor <= 0: divisor = 1 # Evitar div/0
    
    # 1. Costo Total (viene de la fase anterior)
    costo_total = df['Total Cost (USD)']
    
    # 2. Risk Amount
    df['Risk Contingency'] = costo_total * risk_val
    
    # 3. Base Price (Antes de Tax)
    # Fórmula: (Costo + Risk) / (1 - GP)
    df['Base Price'] = (costo_total + df['Risk Contingency']) / divisor
    
    # 4. Tax Amount
    df['Tax Amount'] = df['Base Price'] * tax_rate
    
    # 5. Final Price
    df['Final Price'] = df['Base Price'] + df['Tax Amount']
    
    return df

# ==========================================
# 3. INTERFAZ (SIDEBAR - VARIABLES GLOBALES)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/51/IBM_logo.svg", width=80)
    st.header("1. Configuración Global")
    
    # Selección de País (Define Tax y Scope)
    country_opts = sorted(DB_COUNTRIES["Country"].unique())
    sel_country = st.selectbox("País del Negocio", country_opts, index=country_opts.index("Colombia") if "Colombia" in country_opts else 0)
    
    # Obtener datos del país
    er_default, tax_default, curr_code = get_country_params(sel_country)
    
    # Inputs manuales (con valores por defecto del país)
    er_input = st.number_input("Tasa Cambio (ER)", value=float(er_default))
    tax_input = st.number_input("Impuestos (Tax %)", value=float(tax_default), format="%.4f")
    
    st.markdown("---")
    st.header("2. Variables Financieras")
    
    # Riesgo
    risk_name = st.selectbox("Nivel de Riesgo", DB_RISK["Risk_Level"])
    risk_val = float(DB_RISK[DB_RISK["Risk_Level"] == risk_name]["Contingency"].iloc[0])
    st.caption(f"Contingencia aplicada: {risk_val:.1%}")
    
    # GP
    gp_input = st.number_input("GP Objetivo (%)", value=40.0, step=1.0)
    
    st.markdown("---")
    st.info(f"Modo: {'BRASIL' if sel_country == 'Brazil' else 'LATAM GENERAL'}")

# ==========================================
# 4. ÁREA PRINCIPAL
# ==========================================
st.title(f"Cotizador V19: {sel_country}")

# Subida del Archivo
uploaded_file = st.file_uploader("Cargar Archivo 'Input' (Excel/CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    # --- 1. LECTURA Y LIMPIEZA ---
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df_input = pd.read_csv(uploaded_file)
                if len(df_input.columns) < 2: 
                    uploaded_file.seek(0)
                    df_input = pd.read_csv(uploaded_file, sep=';')
            except:
                uploaded_file.seek(0)
                df_input = pd.read_csv(uploaded_file, sep=';')
        else:
            # Detectar si hay filas vacías arriba (la tabla sidebar del excel)
            # Leemos las primeras 10 filas para buscar donde empieza el encabezado "Unit Loc"
            preview = pd.read_excel(uploaded_file, nrows=10, header=None)
            header_row = 0
            for idx, row in preview.iterrows():
                # Buscamos la fila que tenga "Unit Loc" o "Offering"
                row_str = row.astype(str).str.upper().tolist()
                if any("UNIT LOC" in s for s in row_str) or any("OFFERING" in s for s in row_str):
                    header_row = idx
                    break
            
            df_input = pd.read_excel(uploaded_file, header=header_row)

        # Normalizar columnas
        df_input.columns = [str(c).strip() for c in df_input.columns]
        
        # Validar columnas mínimas
        req_cols = ['Unit Loc', 'Offering', 'Unit Cost', 'Currency']
        if not all(c in df_input.columns for c in req_cols):
            st.error(f"Faltan columnas clave. Se requiere al menos: {req_cols}")
            st.stop()
            
        # --- 2. PROCESAMIENTO ---
        
        # TABLA 1: INPUT (Limpieza)
        # Filtramos offerings según Scope (Brasil vs No Brasil)
        scope_filter = "brasil" if sel_country == "Brazil" else "no brasil"
        # Nota: Aquí podríamos validar si los offerings del Excel son válidos, 
        # pero por ahora solo procesamos lo que suben.
        
        # TABLA 2: COST
        df_cost = procesar_costos(df_input.copy(), er_input)
        
        # TABLA 3: PRICING
        df_pricing = procesar_pricing(df_cost.copy(), risk_val, tax_input, gp_input)

        # --- 3. VISUALIZACIÓN POR PESTAÑAS ---
        tab_input, tab_cost, tab_price = st.tabs(["📂 1. Input Data", "💰 2. Cost Analysis", "🏷️ 3. Pricing Final"])
        
        with tab_input:
            st.subheader("Datos de Entrada")
            st.dataframe(df_input)
            st.caption(f"Filas cargadas: {len(df_input)}")

        with tab_cost:
            st.subheader("Cálculo de Costos (Normalizado)")
            cols_cost = ['Unit Loc', 'Offering', 'Start Date', 'End Date', 'Duration (Months)', 'Norm. Unit Cost (USD)', 'Total Cost (USD)']
            # Mostrar solo columnas que existan
            cols_show = [c for c in cols_cost if c in df_cost.columns]
            st.dataframe(df_cost[cols_show])
            
            total_costo = df_cost['Total Cost (USD)'].sum()
            st.metric("Costo Total del Proyecto (USD)", f"${total_costo:,.2f}")

        with tab_price:
            st.subheader("Estructura de Precio Final")
            cols_price = ['Offering', 'Total Cost (USD)', 'Risk Contingency', 'Base Price', 'Tax Amount', 'Final Price']
            st.dataframe(df_pricing[cols_price])
            
            # KPI Finales
            grand_total = df_pricing['Final Price'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Precio Final Total", f"${grand_total:,.2f}")
            col2.metric("Margen (GP)", f"{gp_input}%")
            col3.metric("Tax Aplicado", f"{tax_input:.1%}")

        # --- 4. EXPORTACIÓN EXCEL COMPLETO ---
        st.divider()
        st.subheader("📥 Descargar Cotización Completa")
        
        # Generar Excel en memoria con múltiples hojas
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_input.to_excel(writer, sheet_name='INPUT', index=False)
            df_cost.to_excel(writer, sheet_name='COST', index=False)
            df_pricing.to_excel(writer, sheet_name='PRICING', index=False)
            
        st.download_button(
            label="Descargar Reporte Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Cotizacion_{sel_country}_V19.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
