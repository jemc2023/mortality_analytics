import pandas as pd

ruta_excel_original = "../../data/raw/ine/defunciones_2015.xlsx"
ruta_csv_destino = "../../data/raw/ine/csv/defunciones_2015.csv"

try:
    df = pd.read_excel(ruta_excel_original)
    
    df.to_csv(
        ruta_csv_destino, 
        index=False,       
        sep=",",           
        encoding="utf-8"   
    )
    
except Exception as e:
    print(f"Error al convertir el archivo: {e}")