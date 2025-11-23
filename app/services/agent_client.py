import requests
import os
import re
from typing import Dict, Any

class AgentClient:
    """
    Cliente para comunicarse con el Agente Executor de Selenium.
    """
    def __init__(self):
        self.executor_url = os.getenv("AGENT_EXECUTOR_URL", "https://executer-qa-fast-web-server.onrender.com/execute")
    
    def extract_python_code(self, text: str) -> str:
        """
        Extrae código Python ejecutable de una respuesta de texto.
        
        Args:
            text: Respuesta completa de Manus
            
        Returns:
            Código Python extraído y limpio
        """
        if not text:
            return ""
        
        print(f"🔍 Extrayendo código de texto ({len(text)} chars)")
        
        # Estrategia 1: Buscar bloques ```python
        python_block_match = re.search(r'```python\s*\n(.*?)```', text, re.DOTALL)
        if python_block_match:
            code = python_block_match.group(1).strip()
            print(f"✓ Código extraído de bloque ```python (tamaño: {len(code)})")
            return code
        
        # Estrategia 2: Buscar bloques ``` genéricos
        code_block_match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
        if code_block_match:
            potential_code = code_block_match.group(1).strip()
            if self._looks_like_python_code(potential_code):
                print(f"✓ Código extraído de bloque ``` (tamaño: {len(potential_code)})")
                return potential_code
        
        # Estrategia 3: Buscar desde "# Configuración" hasta el final del código
        if '# Configuración' in text:
            start_idx = text.index('# Configuración')
            code_section = text[start_idx:]
            
            # Buscar fin del código (antes de texto explicativo)
            end_markers = [
                '\n\n## ',
                '\n\n### ',
                '\n\n**',
                '\n\nEste código',
                '\n\nEl código',
                '\n\nNota:',
                '\n\nRecomendaciones',
                '\n\nHallazgos'
            ]
            
            end_idx = len(code_section)
            for marker in end_markers:
                if marker in code_section:
                    marker_idx = code_section.index(marker)
                    if marker_idx < end_idx:
                        end_idx = marker_idx
            
            code = code_section[:end_idx].strip()
            if len(code) > 100:
                print(f"✓ Código extraído desde '# Configuración' (tamaño: {len(code)})")
                return code
        
        # Estrategia 4: Filtrar líneas de código vs texto explicativo
        lines = text.split('\n')
        code_lines = []
        skip_phrases = [
            'entendido', 'voy a generar', 'aquí está', 'código generado',
            'código python generado', 'he ejecutado', 'a continuación',
            'test de qa', 'resultado del test', 'hallazgos', 'recomendaciones',
            '##', '###', '**', 'prioridad', 'evidencia'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Saltar líneas explicativas
            if any(phrase in line_lower for phrase in skip_phrases):
                continue
            
            # Incluir si parece código Python
            if any([
                line.strip().startswith('#'),
                line.strip().startswith('import '),
                line.strip().startswith('from '),
                '=' in line and not line.strip().startswith('='),
                'driver.' in line,
                'print(' in line,
                'time.sleep(' in line,
                line.startswith('    '),  # línea indentada
                line.startswith('\t')
            ]):
                code_lines.append(line)
        
        extracted = '\n'.join(code_lines).strip()
        
        if len(extracted) > 100 and self._looks_like_python_code(extracted):
            print(f"✓ Código extraído por filtrado de líneas (tamaño: {len(extracted)})")
            return extracted
        
        print(f"⚠️ No se pudo extraer código Python válido")
        return ""
    
    def _looks_like_python_code(self, text: str) -> bool:
        """
        Verifica si un texto parece código Python.
        """
        if not text or len(text) < 50:
            return False
        
        # Debe contener elementos típicos de código Python
        python_indicators = [
            'import ',
            'from ',
            'def ',
            'class ',
            '=',
            'print(',
            'driver.',
            'By.',
            'time.sleep(',
            'WebDriverWait'
        ]
        
        indicator_count = sum(1 for indicator in python_indicators if indicator in text)
        
        # Debe tener al menos 3 indicadores
        if indicator_count < 3:
            return False
        
        # No debe empezar con frases conversacionales
        first_line = text.split('\n')[0].lower().strip()
        conversational = ['entendido', 'voy a', 'aquí está', 'generado', 'he ejecutado']
        
        if any(phrase in first_line for phrase in conversational):
            return False
        
        return True
        
    def execute_code(self, script_code: str, test_name: str = "automated_test", headless: bool = False) -> Dict[str, Any]:
        """
        Envía el código generado por Manus al Agente Executor para ejecutarlo con Selenium.
        
        Args:
            script_code: Código Python con Selenium generado por Manus (puede contener texto extra)
            test_name: Nombre del test
            headless: Si se ejecuta sin interfaz gráfica
            
        Returns:
            Resultado de la ejecución con logs y screenshots
        """
        # ✅ Extraer código limpio antes de enviar
        clean_code = self.extract_python_code(script_code)
        
        if not clean_code:
            return {
                "success": False,
                "output": "❌ No se pudo extraer código Python ejecutable de la respuesta de Manus",
                "logs": f"Respuesta original ({len(script_code)} chars):\n{script_code[:500]}...",
                "screenshot_path": None
            }
        
        print(f"✅ Código limpio extraído: {len(clean_code)} chars")
        print(f"🚀 Enviando al Executor...")
        
        payload = {
            "script": clean_code,
            "test_name": test_name,
            "browser": "chrome",
            "headless": headless
        }
        
        try:
            response = requests.post(
                self.executor_url,
                json=payload,
                timeout=600  # 10 minutos de timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": result.get("status") == "success",
                "output": result.get("data", {}).get("message", "Ejecución completada"),
                "logs": str(result.get("data", {})),
                "screenshot_path": result.get("data", {}).get("screenshot")
            }
            
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "output": "❌ No se pudo conectar con el Agente Executor. Verifica que esté corriendo en http://localhost:8001",
                "logs": "ConnectionError: El servicio de ejecución no está disponible",
                "screenshot_path": None
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "output": "⏱️ Timeout: La ejecución tardó más de 10 minutos",
                "logs": "Timeout al ejecutar el script",
                "screenshot_path": None
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error al ejecutar: {str(e)}",
                "logs": str(e),
                "screenshot_path": None
            }