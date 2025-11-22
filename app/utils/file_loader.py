import pandas as pd
from typing import List, Dict
import io

def load_excel_cases(file) -> List[Dict]:
    """
    Carga casos de prueba desde un archivo Excel.
    
    Estructura esperada del Excel:
    - module_name: Nombre del módulo (ej: "Login")
    - case_name: Nombre del caso (ej: "Login con Google Auth")
    - description: Descripción del caso
    - input_data: Datos de entrada en formato JSON o texto
    - expected_result: Resultado esperado
    - active: Si el caso está activo (VERDADERO/FALSO)
    
    Args:
        file: Archivo de tipo UploadFile de FastAPI
        
    Returns:
        Lista de diccionarios con los casos de prueba
    """
    try:
        # Leer el contenido del archivo en memoria
        contents = file.read()
        
        # Crear un objeto BytesIO para pandas
        excel_buffer = io.BytesIO(contents)
        
        # Leer el archivo Excel desde el buffer
        df = pd.read_excel(excel_buffer, engine='openpyxl')
        
        # Resetear el puntero del archivo por si se necesita usar después
        file.seek(0)
        
        # Normalizar nombres de columnas (quitar espacios y convertir a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas
        required_columns = ['module_name', 'case_name', 'input_data', 'expected_result']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            available_cols = ', '.join(df.columns.tolist())
            raise ValueError(
                f"❌ Faltan columnas requeridas: {', '.join(missing_columns)}. "
                f"Columnas encontradas: {available_cols}"
            )
        
        # Convertir DataFrame a lista de diccionarios
        cases = []
        for index, row in df.iterrows():
            # Validar que la fila no esté vacía
            if pd.isna(row.get('case_name')) or pd.isna(row.get('input_data')):
                continue  # Saltar filas vacías
            
            # Verificar si el caso está activo
            is_active = True  # Por defecto activo
            if 'active' in df.columns and pd.notna(row.get('active')):
                active_value = str(row['active']).upper().strip()
                # Aceptar: VERDADERO, TRUE, 1, YES, SI, SÍ
                is_active = active_value in ['VERDADERO', 'TRUE', '1', 'YES', 'SI', 'SÍ', 'ACTIVO']
            
            # Solo agregar casos activos
            if is_active:
                # Combinar module_name y case_name para el nombre del caso
                module = str(row['module_name']).strip() if pd.notna(row.get('module_name')) else ''
                case_name = str(row['case_name']).strip()
                full_name = f"{module} - {case_name}" if module else case_name
                
                # Obtener descripción
                description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
                
                # Obtener input_data (puede ser JSON o texto)
                input_data = str(row['input_data']).strip()
                
                # Obtener expected_result
                expected = str(row['expected_result']).strip() if pd.notna(row.get('expected_result')) else ''
                
                # Extraer URL si está en el input_data (formato JSON)
                url = None
                if '"url"' in input_data or "'url'" in input_data:
                    try:
                        import json
                        # Intentar parsear como JSON
                        input_json = json.loads(input_data.replace("'", '"'))
                        url = input_json.get('url')
                    except:
                        pass  # Si no es JSON válido, continuar sin URL
                
                case = {
                    'name': full_name,
                    'description': description,
                    'steps': input_data,  # input_data se guarda como steps
                    'expected_result': expected,
                    'url': url
                }
                cases.append(case)
        
        if not cases:
            raise ValueError("❌ No se encontraron casos de prueba activos en el archivo Excel")
        
        return cases
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"❌ Error al procesar el archivo Excel: {str(e)}")
