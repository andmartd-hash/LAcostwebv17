import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuración global para visualización de DataFrames
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', '{:.4f}'.format)

class LacosWebConfig:
    """
    Clase de configuración para constantes y parámetros globales.
    """
    DEFAULT_GP_PERCENTAGE = 0.64
    BRAZIL_COUNTRY_NAME = "Brazil"
    NO_BRAZIL_SCOPE = "no brazil"
    BRAZIL_SCOPE = "Brazil"
    ALL_SCOPE = "ALL"

class PricingDataLoader:
    """
    Responsable de analizar los datos crudos (CSV) y preparar las estructuras de búsqueda.
    En un entorno real, esto leería archivos.csv o consultaría una base de datos SQL.
    """
    def __init__(self):
        self.countries_df = None
        self.qa_risk_df = None
        self.slc_df = None
        self.offering_df = None
        self.labor_df = None
        
    def load_simulated_data(self):
        """
        Carga los datos proporcionados en los snippets de investigación.[1, 1, 1, 1, 1]
        Se utilizan cadenas de texto (StringIO) para simular los archivos CSV.
        """
        # 1. TABLA DE PAÍSES 
        # Nota: Se normaliza Ecuador con E/R = 1.0 según regla de negocio.
        countries_data = """Country,Currency,ER,Tax
Argentina,ARS,1428.948633,0.0529
Brazil,BRL,5.341035,0.1425
Chile,CLP,934.704,0
Colombia,COP,3775.22225,0.01
Ecuador,USD,1.0,0
Peru,PEN,3.3729225,0
Mexico,MXN,18.420365,0
Uruguay,UYU,39.73184,0
Venezuela,VES,235.28249,0.0155"""
        self.countries_df = pd.read_csv(StringIO(countries_data))
        
        # 2. TABLA DE RIESGO QA 
        risk_data = """Level,Percentage
Low,0.02
Medium,0.05
High,0.08"""
        self.qa_risk_df = pd.read_csv(StringIO(risk_data))
        
        # 3. TABLA SLC 
        # Se incluye una muestra representativa de ambos alcances (Brazil/No Brazil)
        slc_data = """Scope,KEY,SLC,UpliftFactor
no brazil,9X5NBDOn-site arrival time,M1A,1
no brazil,9X5SBDOn-site arrival time,M16,1
no brazil,24X7SDOn-site arrival time,M19,1
no brazil,24X71Contact time (call back time),M5B,1.05
no brazil,24X74On-site Response time,M47,1.5
no brazil,24X772Fix time,MJ7,1.1
no brazil,24X748Fix time,M3F,1.15
no brazil,24X724Fix time,M3B,1.2
no brazil,24X712Fix time,M33,1.3
no brazil,24X78Fix time,M2F,1.4
no brazil,24X76Fix time,M2B,1.6
no brazil,24X74Fix time,M23,1.7
Brazil,9X5NBDOn-site arrival time,M1A,1
Brazil,24X7SDOn-site arrival time,M19,1
Brazil,24X74On-site Response time,M47,1.5
Brazil,NStdSBD6x24,NStdSBD6x24,1.266
Brazil,NStdFix4 7x24,NStdFix4 7x24,1.458"""
        self.slc_df = pd.read_csv(StringIO(slc_data))
        
        # 4. TABLA DE OFERTAS 
        offering_data = """Offering,L40,GoToConga
IBM Customized Support for Hardware Services-Logo,6942-76V,Location Based Services
IBM Support for Red Hat,6948-B73,Conga by CSV
System Technical Support Service-MVS-STSS,6942-1FN,Location Based Services
Relocation Services - Packaging,6942-54E,Location Based Services"""
        self.offering_df = pd.read_csv(StringIO(offering_data))

        # 5. TABLA LABORAL 
        # Se simula la estructura compleja con columnas por país.
        # Def 'A' = System Z, 'C' = Power HE, etc. según.
        labor_data = """Scope,MC_RR,Def,Argentina,Brazil,Chile,Colombia,Ecuador,Peru,Mexico,Uruguay,Venezuela
no brazil,Machine Category,A,304504.2,,2165270.415,2054058.998,991.20735,1284.609,12857.25,30167.39,102721.98
no brazil,Machine Category,C,194856.48,,486361.26,540008.96,340.52,505.85,5857.95,18987.51,40555.17
Brazil,Machine Category,1,,2803.85,,,,,,,
Brazil,Machine Category,2,,1516.61,,,,,,,
ALL,Brand Rate Full,B1,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99,15247.99"""
        self.labor_df = pd.read_csv(StringIO(labor_data))

    # --- MÉTODOS DE BÚSQUEDA (LOOKUP) ---

    def get_exchange_rate(self, country):
        """Devuelve la tasa de cambio para el país dado."""
        row = self.countries_df[self.countries_df['Country'] == country]
        if not row.empty:
            return float(row.iloc)
        # Retorno seguro 1.0 si no se encuentra, asumiendo USD o error de config
        return 1.0

    def get_uplift_factor(self, country, slc_code):
        """
        Determina el factor de incremento basado en el país y el código SLC.
        Aplica la lógica de ramificación Brasil vs No Brasil.
        """
        scope = LacosWebConfig.BRAZIL_SCOPE if country == LacosWebConfig.BRAZIL_COUNTRY_NAME else LacosWebConfig.NO_BRAZIL_SCOPE
        
        # Filtrar SLC por alcance y código
        row = self.slc_df == scope) & (self.slc_df == slc_code)]
        
        if not row.empty:
            return float(row.iloc['UpliftFactor'])
        
        print(f"ADVERTENCIA: Código SLC '{slc_code}' no encontrado para el alcance '{scope}'. Retornando Uplift 1.0 por defecto.")
        return 1.0

    def get_risk_percentage(self, risk_level):
        """Convierte el nivel de riesgo (Texto) a porcentaje (Float)."""
        row = self.qa_risk_df[self.qa_risk_df['Level'] == risk_level]
        if not row.empty:
            return float(row.iloc['Percentage'])
        try:
            # Soporte por si el input ya es numérico (ej. 0.02)
            return float(risk_level)
        except:
            return 0.0

    def get_labor_rate(self, country, category_def, rr_br_type):
        """
        Recupera la tarifa laboral local.
        Maneja la lógica compleja de RR/BR y la ramificación de alcances.
        """
        # Determinar el alcance objetivo
        if rr_br_type == "Brand Rate Full":
            target_scope = LacosWebConfig.ALL_SCOPE
        else:
            target_scope = LacosWebConfig.BRAZIL_SCOPE if country == LacosWebConfig.BRAZIL_COUNTRY_NAME else LacosWebConfig.NO_BRAZIL_SCOPE
        
        # Filtrar el DataFrame Laboral
        subset = self.labor_df == target_scope) & 
            (self.labor_df == category_def)
        ]
        
        if subset.empty:
            print(f"ERROR: No se encontró tarifa laboral para {country}, Def: {category_def}, Tipo: {rr_br_type}")
            return 0.0
        
        # Extraer el valor de la columna específica del país
        if country in subset.columns:
            val = subset.iloc[country]
            if pd.isna(val) or val == '':
                # Intento de fallback para 'ALL' si la columna país falla, pero el CSV sugiere columnas explícitas.
                return 0.0
            return float(val)
        else:
            print(f"ERROR: El país {country} no existe como columna en la tabla Laboral.")
            return 0.0

class PricingCalculator:
    """
    Motor de cálculo que implementa las fórmulas matemáticas definidas en Logic_rules.csv.
    """
    def __init__(self, data_loader):
        self.db = data_loader
    
    def calculate_duration(self, start_date_str, end_date_str):
        """Calcula la duración en meses entre dos fechas."""
        try:
            d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
            d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
            delta = relativedelta(d2, d1)
            # Lógica inclusiva: Si empieza en Ene 1 y termina Dic 31, son 12 meses.
            months = delta.years * 12 + delta.months
            # Ajuste de días: si hay días residuales, ¿se cobra mes extra? 
            # Asumiremos redondeo simple o +1 si es inclusivo completo. 
            # Para 2026-01-01 a 2026-12-31, relativedelta da 11 meses y 30 días.
            # La lógica de negocio suele dictar "meses calendario completos".
            if delta.days > 0 or (delta.years==0 and delta.months==0):
                months += 1
            return max(1, months) 
        except Exception as e:
            print(f"Error calculando duración: {e}")
            return 0

    def calculate_total_service_cost(self, usd_unit_cost, sqty, slc_uplf, duration):
        """
        Fórmula: USDunit cost * sqty * SLCuplf * duracion
        """
        return usd_unit_cost * sqty * slc_uplf * duration

    def calculate_total_labor_cost(self, country, labor_rate_local, lqty):
        """
        Fórmula: (Machine Category/(E/R)*lqty)
        """
        er = self.db.get_exchange_rate(country)
        if er == 0: 
            print("Error Crítico: Tasa de cambio es 0. Evitando división por cero.")
            er = 1 
        
        usd_labor_rate = labor_rate_local / er
        return usd_labor_rate * lqty

    def calculate_total_price(self, total_cost, risk_percentage, gp_percentage=LacosWebConfig.DEFAULT_GP_PERCENTAGE):
        """
        Fórmula: costo*(1+riesgo)/(1-GP)
        """
        numerator = total_cost * (1 + risk_percentage)
        denominator = (1 - gp_percentage)
        
        if denominator == 0:
            print("Error Crítico: Margen GP es 100%, división por cero imposible.")
            return 0
            
        return numerator / denominator

def run_lacosweb_engine_simulation():
    print("==============================================================")
    print("   INICIANDO MOTOR DE PRECIOS LACOSWEB V17 (Simulación)   ")
    print("==============================================================\n")

    # 1. Inicialización
    loader = PricingDataLoader()
    loader.load_simulated_data()
    engine = PricingCalculator(loader)
    
    # 2. Definición del Caso de Prueba 
    # Escenario: Contrato en Colombia, 12 meses, Servicio de Hardware IBM, Nivel 24x7
    test_case = {
        "general": {
            "Country": "Colombia",
            "Contract Start Date": "2026-01-01",
            "Contract End Date": "2026-12-31"
        },
        "service": {
            "Offering": "IBM Customized Support for Hardware Services-Logo",
            "L40": "6942-76V",
            "QA Risk": "Low",    # Nivel bajo (0.02)
            "SLC": "M19",        # 24X7SD On-site arrival time
            "USD Unit Cost": 10.0,
            "SQty": 1
        },
        "labor": {
            "RR/BR": "Machine Category",
            "Def": "A",          # System Z (según mapeo hipotético del L40)
            "LQty": 1
        }
    }

    print(f"Procesando cotización para: {test_case['general']['Country']}")
    print(f"Servicio: {test_case['service']['Offering']} (L40: {test_case['service']['L40']})")
    print("-" * 60)

    # 3. Ejecución de Cálculos Paso a Paso
    
    # A. Duración
    duration = engine.calculate_duration(
        test_case["general"],
        test_case["general"]
    )
    print(f" Duración Calculada: {duration} meses")

    # B. Factores (Uplift y E/R)
    country = test_case["general"]["Country"]
    er = loader.get_exchange_rate(country)
    uplift = loader.get_uplift_factor(country, test_case["service"])
    print(f" Tasa de Cambio (E/R): {er:,.4f} {country}/USD")
    print(f" Factor SLC ({test_case['service']}): {uplift}")

    # C. Costo de Servicio
    svc_cost = engine.calculate_total_service_cost(
        usd_unit_cost=test_case["service"],
        sqty=test_case["service"],
        slc_uplf=uplift,
        duration=duration
    )
    print(f" Costo Total Servicio: ${svc_cost:,.2f} USD")

    # D. Costo Laboral
    # Primero buscamos la tarifa en moneda local
    local_rate = loader.get_labor_rate(
        country=country,
        category_def=test_case["labor"],
        rr_br_type=test_case["labor"]
    )
    print(f" Tarifa Laboral Local: {local_rate:,.2f} (Moneda Local)")
    
    # Convertimos a USD
    lab_cost = engine.calculate_total_labor_cost(
        country=country,
        labor_rate_local=local_rate,
        lqty=test_case["labor"]["LQty"]
    )
    print(f" Costo Total Laboral (Normalizado): ${lab_cost:,.2f} USD")

    # E. Total y Precio Final
    total_cost = svc_cost + lab_cost
    risk_pct = loader.get_risk_percentage(test_case["service"])
    final_price = engine.calculate_total_price(total_cost, risk_pct)
    
    print("-" * 60)
    print(f"   RESULTADOS FINALES")
    print(f"   ------------------")
    print(f"   COSTO TOTAL (Total Cost):    ${total_cost:,.2f} USD")
    print(f"   PRECIO FINAL (Total Price):  ${final_price:,.2f} USD")
    print(f"   (Incluye Riesgo {risk_pct*100}% y Margen GP {LacosWebConfig.DEFAULT_GP_PERCENTAGE*100}%)")
    print("==============================================================")

if __name__ == "__main__":
    run_lacosweb_engine_simulation()
