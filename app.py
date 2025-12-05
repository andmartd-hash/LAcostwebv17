import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import io

# Configuración de página
st.set_page_config(page_title="LACOSWEB V17", layout="wide", page_icon="📊")

st.title("📊 LACOSWEB V17 - Cloud Engine")
st.markdown("Cálculo de costos basado en **INPUT cost** y **Parameters** (Lógica V09).")

# --- FUNCIONES DE LÓGICA DE NEGOCIO (EL CORAZÓN DEL SISTEMA) ---

def get_contingency_cost(risk_level, df_params):
    """
    Replica la lógica de la celda I3:
    IF(H3="low", Parameters!J226, IF(H3="Med", Parameters!J227, IF(H3="High", Parameters!J228, 0)))
    """
    # Excel usa base-1, Pandas usa base-0. J226 es fila 225, col 9.
    try:
        val_low = df_params.iloc[225, 9]  # J226
        val_med = df_params.iloc[226, 9]  # J227
        val_high = df_params.iloc[227, 9] # J228
        
        risk = str(risk_level).lower().strip()
        
        if risk == 'low': return val_low
        elif risk == 'med': return val_med
        elif risk == 'high': return val_high
        return 0.0
    except Exception:
        return 0.0

def calculate_duration(start_date, end_date):
    """
    Replica la lógica de la celda E8:
    IF(EndDate<StartDate, "Not Valid", ROUND(DATEDIF logic...))
    """
    if pd.isnull(start_date) or pd.isnull(end_date):
        return 0
    
    if end_date < start_date:
        return "Not Valid"
    
    # Lógica aproximada de DATEDIF "m" + fracción
    days = (end_date - start_date).days
    months = days / 30.437 # Promedio días mes
    return round(months, 1)

def perform_vlookups(df_input, df_params):
    """
    Replica los VLOOKUP de filas 14 a 20.
    Busca D14 en Parameters!$K$436:$N$458 y trae columnas 3 y 4.
    """
    # 1. Extraer la tabla de referencia (Lookup Table) de Parameters
    # K436:N458 -> Filas 435:458, Cols 10:14 (K, L, M, N)
    # Columna K es el índice (clave de búsqueda)
    try:
        lookup_table = df_params.iloc[435:458, 10:14].copy()
        lookup_table.columns = ['Key', 'Col2', 'Val_Col3', 'Val_Col4'] # Renombrar para facilitar
        
        # Limpiar datos para asegurar el cruce
        lookup_table['Key'] = lookup_table['Key'].astype(str).str.strip()
    except Exception as e:
        st.error(f"Error extrayendo tabla de parámetros (K436:N458): {e}")
        return df_input

    # 2. Aplicar VLOOKUP fila por fila en INPUT cost (asumiendo datos desde fila 13 en adelante python index)
    # Buscamos en columna D (índice 3)
    
    # Creamos listas para los resultados
    res_b = []
    res_h = []
    
    # Iteramos sobre las filas relevantes (ejemplo 14 a 20, indices 13-19)
    # Nota: En un Excel real esto suele ser dinámico, aquí lo haremos para el rango detectado
    for index, row in df_input.iterrows():
        if index < 13: # Saltar encabezados (Filas 1-13 de Excel)
            res_b.append(row.iloc[1] if len(row) > 1 else "")
            res_h.append(row.iloc[7] if len(row) > 7 else "")
            continue
            
        search_key = str(row.iloc[3]).strip() # Columna D
        
        # Buscar en la tabla
        match = lookup_table[lookup_table['Key'] == search_key]
        
        if not match.empty:
            val_b = match.iloc[0]['Val_Col4'] # Excel col 4 -> Pandas 'Val_Col4'
            val_h = match.iloc[0]['Val_Col3'] # Excel col 3 -> Pandas 'Val_Col3'
        else:
            val_b = "" # IFERROR -> ""
            val_h = ""
            
        res_b.append(val_b)
        res_h.append(val_h)

    # Asignar resultados a columnas B (1) y H (7)
    df_input.iloc[:, 1] = res_b
    df_input.iloc[:, 7] = res_h
    
    return df_input

# --- INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader("📂 Sube tu archivo Excel (LACOST+V09...)", type=["xlsm", "xlsx"])

if uploaded_file:
    try:
        # Cargar hojas SIN cabeceras (header=None) para usar coordenadas puras (A1, B2...)
        df_input_raw = pd.read_excel(uploaded_file, sheet_name='INPUT cost', header=None)
        df_params_raw = pd.read_excel(uploaded_file, sheet_name='Parameters', header=None)
        
        st.success("✅ Archivo cargado. Procesando lógica V09...")
        
        # --- 1. PROCESAR CONTINGENCY COST (Celda I3) ---
        risk_value = df_input_raw.iloc[2, 7] # H3
        contingency = get_contingency_cost(risk_value, df_params_raw)
        
        # Escribir resultado en I3 (fila 2, col 8)
        df_input_raw.iloc[2, 8] = contingency
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Riesgo (H3)", risk_value)
        col2.metric("Costo Contingencia (Calc I3)", f"${contingency:,.2f}")

        # --- 2. PROCESAR DURACIÓN (Celda E8) ---
        # Asumimos que StartDate y EndDate son nombrados. 
        # Si no están definidos, usamos selectores para probar.
        st.subheader("📅 Cálculo de Tiempos")
        c_dates1, c_dates2 = st.columns(2)
        start_date = c_dates1.date_input("Start Date", date.today())
        end_date = c_dates2.date_input("End Date", date.today())
        
        duration = calculate_duration(pd.to_datetime(start_date), pd.to_datetime(end_date))
        
        # Simulamos escribir en E8 (Fila 7, Col 4)
        df_input_raw.iloc[7, 4] = duration
        st.info(f"Duración calculada (E8 Logic): **{duration} meses**")

        # --- 3. PROCESAR VLOOKUPS (Filas 14-20) ---
        st.subheader("🔍 Procesando VLOOKUPs (Tabla Parameters K436:N458)")
        
        # Ejecutar la lógica de cruce
        df_final = perform_vlookups(df_input_raw.copy(), df_params_raw)
        
        # Mostrar vista previa de la zona afectada (Filas 14-20, Cols A-H)
        # Pandas indices 13-20
        st.dataframe(df_final.iloc[13:21, [0,1,3,7]]) # Mostrando Cols A, B, D, H
        
        # --- 4. DESCARGA ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, sheet_name='INPUT cost_Calc', index=False, header=False)
            df_params_raw.to_excel(writer, sheet_name='Parameters', index=False, header=False)
            
        st.download_button(
            label="📥 Descargar Excel Calculado",
            data=buffer,
            file_name="LACOSWEB_Processed.xlsx",
            mime="application/vnd.ms-excel"
        )

    except Exception as e:

        st.error(f"Error crítico: {e}")

