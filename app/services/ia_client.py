# app/services/ia_client.py
import requests
import os
from typing import Dict, Any, List

class IAClient:
    def __init__(self):
        self.api_url = os.getenv("MANUS_API_URL", "https://api.manus.ai/v1")
        self.api_key = os.getenv("MANUS_API_KEY")
        
        if not self.api_key:
            raise ValueError("MANUS_API_KEY no está configurada en el archivo .env")

    def generate_code(self, prompt: str, agent_profile: str = "manus-1.5") -> Dict[str, Any]:
        """
        Envía el prompt a Manus IA y recibe la tarea generada.
        """
        headers = {
            "API_KEY": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "agentProfile": agent_profile,
            "taskMode": "agent",
            "hideInTaskList": False,
            "createShareableLink": True
        }

        try:
            response = requests.post(
                f"{self.api_url}/tasks", # https://api.manus.ai/v1/tasks
                headers=headers, #
                json=payload, 
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Devolver en formato consistente
            return {
                "task_id": data.get("task_id"),
                "task_title": data.get("task_title"),
                "task_url": data.get("task_url"),
                "share_url": data.get("share_url")
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al comunicarse con Manus API: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una tarea de Manus usando el ID específico.
        Extrae el código Python del campo output.
        """
        headers = {
            "API_KEY": self.api_key
        }
        
        task_url = f"{self.api_url}/tasks/{task_id}"
        
        try:
            print(f"🔍 Consultando tarea: GET {task_url}")
            response = requests.get(task_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            task_data = response.json()
            status = task_data.get("status")
            
            print(f"✓ Estado de tarea: {status}")
            
            # Extraer el código del output según la estructura de Manus
            code_text = self._extract_code_from_output(task_data.get("output", []))
            
            # Devolver en formato consistente con el anterior
            return {
                "id": task_data.get("id"),
                "status": status,
                "error": task_data.get("error"),
                "output": task_data.get("output", []),
                "code_text": code_text,  # Nuevo: código extraído
                "credit_usage": task_data.get("credit_usage"),
                "created_at": task_data.get("created_at"),
                "updated_at": task_data.get("updated_at")
            }
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error al consultar tarea: {str(e)}")
            return {
                "id": task_id,
                "status": "error",
                "error": str(e),
                "output": [],
                "code_text": ""
            }
    
    def _extract_code_from_output(self, output: List[Dict]) -> str:
        """
        Extrae el código Python del campo output de Manus.
        Ahora también maneja archivos generados (output_file).
        """
        import re
        import json
        import requests
        
        # ✅ DEBUG: Ver estructura completa (comentar después de debug)
        # print("=" * 80)
        # print("🔍 DEBUG - ESTRUCTURA COMPLETA DEL OUTPUT:")
        # print(json.dumps(output, indent=2, ensure_ascii=False))
        # print("=" * 80)
        
        code_parts = []
        file_url = None
        
        for message in output:
            # Solo procesar mensajes del asistente
            if message.get("role") != "assistant":
                continue
            
            content = message.get("content", [])
            
            for item in content:
                # 1️⃣ Buscar texto de código
                if item.get("type") == "output_text":
                    text = item.get("text", "")
                    if text.strip():
                        code_parts.append(text)
                
                # 2️⃣ ✅ NUEVO: Buscar archivos Python generados
                elif item.get("type") == "output_file":
                    file_name = item.get("fileName", "")
                    if file_name.endswith(".py"):
                        file_url = item.get("fileUrl")
                        print(f"🔍 Archivo Python detectado: {file_name}")
                        print(f"📥 URL del archivo: {file_url}")
        
        # 3️⃣ Si hay archivo, descargarlo
        if file_url:
            try:
                print(f"📥 Descargando código desde archivo...")
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                
                file_code = response.text
                print(f"✅ Código descargado del archivo: {len(file_code)} chars")
                
                # Retornar directamente el código del archivo
                return self._clean_downloaded_code(file_code)
                
            except Exception as e:
                print(f"❌ Error al descargar archivo: {e}")
                # Continuar con extracción de texto si falla descarga
        
        # 4️⃣ Si no hay archivo, procesar texto
        full_text = "\n".join(code_parts)
        
        if not full_text.strip():
            print(f"⚠️ No se encontró código ni en texto ni en archivos")
            return ""
        
        print(f"📝 Texto completo extraído: {len(full_text)} chars")
        print(f"📄 Primeros 300 chars: {full_text[:300]}")
        
        # ✅ LIMPIAR TEXTO CONVERSACIONAL
        
        # 1. Buscar bloques de código en markdown
        code_match = re.search(r'```python\s*\n(.*?)```', full_text, re.DOTALL)
        if code_match:
            clean_code = code_match.group(1).strip()
            print(f"✓ Código extraído de bloque markdown: {len(clean_code)} chars")
            return clean_code
        
        # 2. Buscar desde "# Configuración" hasta fin de código
        if '# Configuración' in full_text:
            start_idx = full_text.index('# Configuración')
            code_section = full_text[start_idx:]
            
            # Detener antes de texto explicativo
            end_markers = ['\n\n## ', '\n\n### ', '\n\n**', '\n\nEste código', '\n\nEl código']
            end_idx = len(code_section)
            
            for marker in end_markers:
                if marker in code_section:
                    marker_idx = code_section.index(marker)
                    if marker_idx < end_idx:
                        end_idx = marker_idx
            
            clean_code = code_section[:end_idx].strip()
            print(f"✓ Código extraído desde '# Configuración': {len(clean_code)} chars")
            return clean_code
        
        # 3. Filtrar líneas que parecen código vs explicaciones
        lines = full_text.split('\n')
        code_lines = []
        
        skip_phrases = [
            'voy a generar', 'código generado', 'código python', 
            'entendido', 'aquí está', 'a continuación'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Saltar líneas conversacionales
            if any(phrase in line_lower for phrase in skip_phrases):
                continue
            
            # Incluir líneas que parecen código
            if any([
                line.strip().startswith('#'),
                line.strip().startswith('import '),
                line.strip().startswith('from '),
                '=' in line and not line.strip().startswith('='),
                'driver.' in line,
                'print(' in line,
                'time.sleep(' in line,
                line.startswith('    '),
                line.startswith('\t')
            ]):
                code_lines.append(line)
        
        clean_code = '\n'.join(code_lines).strip()
        
        if len(clean_code) > 100:
            print(f"✓ Código limpiado por filtrado: {len(clean_code)} chars")
            return clean_code
        
        # Si todo falla, devolver el texto original
        print(f"⚠️ No se pudo limpiar, devolviendo texto original")
        return full_text
    
    def _clean_downloaded_code(self, code: str) -> str:
        """
        Limpia código descargado de archivos generados por Manus.
        """
        import re
        
        # Remover shebang si existe
        code = re.sub(r'^#!.*\n', '', code)
        
        # Remover comentarios al inicio tipo "# Generated by..."
        code = re.sub(r'^# Generated.*\n', '', code)
        
        # Si tiene múltiples líneas vacías al inicio, limpiarlas
        code = code.lstrip()
        
        # Verificar que tenga contenido válido
        if len(code) > 100 and any(keyword in code for keyword in ['driver', 'selenium', 'print(', 'time.sleep']):
            print(f"✅ Código del archivo limpiado: {len(code)} chars")
            return code
        
        print(f"⚠️ Código del archivo no parece válido")
        return code
    
    def create_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Crea un webhook en Manus para recibir notificaciones cuando las tareas se completen.
        
        Args:
            webhook_url: URL donde Manus enviará las notificaciones (ej: https://tuapp.com/api/webhooks/manus)
        """
        headers = {
            "API_KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "webhook": {
                "url": webhook_url
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/webhooks",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            print(f"✓ Webhook creado: {data.get('webhook_id')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al crear webhook: {str(e)}")
