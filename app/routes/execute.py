from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.schemas.result_schema import ExecutionResponse
from app.models.case_model import TestCase
from app.models.result_model import TestResult
from app.models.prompt_model import Prompt
from app.services.prompt_builder import PromptBuilder
from app.services.ia_client import IAClient
from app.services.agent_client import AgentClient
from app.config import get_db
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import re
from datetime import datetime

router = APIRouter()

def extract_python_code(text: str) -> str:
    """
    Extrae código Python de la respuesta de Manus con múltiples estrategias.
    """
    if not text or not text.strip():
        return ""
    
    # Estrategia 1: Buscar bloques ```python
    python_blocks = re.findall(r'```python\s*\n(.*?)\n```', text, re.DOTALL | re.IGNORECASE)
    if python_blocks:
        print(f"✓ Encontrado código en bloque ```python (tamaño: {len(python_blocks[0])} chars)")
        return python_blocks[0].strip()
    
    # Estrategia 2: Buscar bloques ``` sin especificar lenguaje
    code_blocks = re.findall(r'```\s*\n(.*?)\n```', text, re.DOTALL)
    if code_blocks:
        for block in code_blocks:
            if any(keyword in block for keyword in ['import', 'driver', 'print(', 'time.sleep']):
                print(f"✓ Encontrado código en bloque ``` (tamaño: {len(block)} chars)")
                return block.strip()
    
    # Estrategia 3: Si no hay bloques pero el texto parece código Python
    if any(keyword in text for keyword in ['driver.', 'print(', 'time.sleep', '# Config']):
        print(f"✓ Texto detectado como código directo (tamaño: {len(text)} chars)")
        return text.strip()
    
    print("⚠️ No se detectó código Python ejecutable en la respuesta")
    return ""

@router.post("/{case_id}", response_model=ExecutionResponse)
async def execute_case(case_id: int, db: Session = Depends(get_db)):
    """
    Ejecuta un caso de prueba usando Manus IA + Agente Selenium.
    Guarda el prompt y resultado en la base de datos.
    """
    test_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    
    if not test_case:
        raise HTTPException(status_code=404, detail="Caso de prueba no encontrado")

    # Variables para tracking
    start_time = datetime.now()
    prompt_record = None
    result_record = None

    try:
        # 1️⃣ Generar el prompt
        prompt_builder = PromptBuilder()
        prompt_text = prompt_builder.build_prompt(test_case)

        # 💾 Guardar prompt en BD
        prompt_record = Prompt(
            test_case_id=test_case.id,
            prompt_text=prompt_text,
            generated_code=None
        )
        db.add(prompt_record)
        db.commit()
        db.refresh(prompt_record)
        print(f"✅ Prompt guardado en BD (ID: {prompt_record.id})")

        # 2️⃣ Enviar prompt a Manus IA
        ia_client = IAClient()
        
        try:
            manus_response = ia_client.generate_code(
                prompt=prompt_text,
                agent_profile="manus-1.5"
            )
        except Exception as manus_error:
            # 💾 Guardar resultado de error
            result_record = TestResult(
                test_case_id=test_case.id,
                status="error",
                logs=f"Error Manus: {str(manus_error)}",
                screenshot_path=None,
                execution_time="0s",
                executed_by_agent=False
            )
            db.add(result_record)
            db.commit()
            
            return ExecutionResponse(
                case_id=test_case.id,
                code="",
                output=f"❌ Error al comunicarse con Manus IA:\n{str(manus_error)}",
                success=False,
                logs=f"Error: {str(manus_error)}\n\nVerifica:\n1. MANUS_API_KEY en .env\n2. MANUS_API_URL=https://api.manus.ai/v1\n3. Conexión a internet"
            )
        
        task_id = manus_response.get("task_id")
        share_url = manus_response.get("share_url")
        
        if not task_id:
            result_record = TestResult(
                test_case_id=test_case.id,
                status="error",
                logs=f"Manus no devolvió task_id: {manus_response}",
                screenshot_path=None,
                execution_time="0s",
                executed_by_agent=False
            )
            db.add(result_record)
            db.commit()
            
            return ExecutionResponse(
                case_id=test_case.id,
                code="",
                output="❌ Manus no devolvió un task_id válido",
                success=False,
                logs=f"Respuesta de Manus: {manus_response}"
            )
        
        print(f"📊 Tarea creada: {task_id}")
        print(f"🔗 Ver en: {share_url}")
        
        # 3️⃣ Polling para obtener el código generado
        max_attempts = 60
        attempt = 0
        task_completed = False
        generated_code = ""
        
        while attempt < max_attempts and not task_completed:
            time.sleep(10)
            attempt += 1
            
            try:
                task_status = ia_client.get_task_status(task_id)
                status = task_status.get("status")
                
                print(f"🔄 Intento {attempt}/{max_attempts} - Estado: {status}")
                
                if status == "completed":
                    task_completed = True
                    generated_code = task_status.get("code_text", "")
                    print(f"✅ Tarea completada. Código recibido: {len(generated_code)} chars")
                    
                    # 💾 Actualizar código generado en el prompt
                    if prompt_record:
                        prompt_record.generated_code = generated_code
                        db.commit()
                        print(f"✅ Código guardado en prompt (ID: {prompt_record.id})")
                                    
                elif status == "failed":
                    error = task_status.get("error", "Error desconocido")
                    raise HTTPException(status_code=500, detail=f"Manus falló: {error}")
                    
            except HTTPException:
                raise
            except Exception as e:
                print(f"⚠️ Error al consultar estado: {str(e)}")
        
        # Si no se completó a tiempo
        if not task_completed or not generated_code.strip():
            result_record = TestResult(
                test_case_id=test_case.id,
                status="error",
                logs=f"Timeout o sin código. Intentos: {attempt}/{max_attempts}",
                screenshot_path=None,
                execution_time=f"{(datetime.now() - start_time).seconds}s",
                executed_by_agent=False
            )
            db.add(result_record)
            db.commit()
            
            return ExecutionResponse(
                case_id=test_case.id,
                code=f"# Tarea en progreso o sin código\n# Task ID: {task_id}",
                output=f"⏳ La tarea {'aún se está procesando' if not task_completed else 'no devolvió código ejecutable'}.\n\n🔗 Ver: {share_url}",
                success=False,
                logs=f"Task ID: {task_id}\nIntentos: {attempt}/{max_attempts}"
            )
        
        # 4️⃣ Extraer código Python limpio
        python_code = extract_python_code(generated_code)
        
        if not python_code or len(python_code) < 50:
            result_record = TestResult(
                test_case_id=test_case.id,
                status="error",
                logs=f"Código no extraíble. Respuesta: {generated_code[:500]}",
                screenshot_path=None,
                execution_time=f"{(datetime.now() - start_time).seconds}s",
                executed_by_agent=False
            )
            db.add(result_record)
            db.commit()
            
            return ExecutionResponse(
                case_id=test_case.id,
                code=generated_code[:2000],
                output=f"❌ No se pudo extraer código ejecutable.\n\n🔗 Ver respuesta completa: {share_url}",
                success=False,
                logs=f"Respuesta de Manus:\n{generated_code[:1000]}..."
            )

        # 5️⃣ Enviar al Agente Executor
        print(f"🚀 Enviando código al Agente Executor ({len(python_code)} chars)...")
        
        agent = AgentClient()
        execution_result = agent.execute_code(
            script_code=python_code,
            test_name=f"case_{test_case.id}_{test_case.name[:20].replace(' ', '_')}",
            headless=False
        )

        # 6️⃣ Calcular tiempo de ejecución
        execution_time = f"{(datetime.now() - start_time).seconds}s"
        
        # 💾 Guardar resultado en BD
        result_record = TestResult(
            test_case_id=test_case.id,
            status="passed" if execution_result.get("success") else "failed",
            logs=execution_result.get("logs", ""),
            screenshot_path=execution_result.get("screenshot_path"),
            execution_time=execution_time,
            executed_by_agent=True
        )
        db.add(result_record)
        db.commit()
        db.refresh(result_record)
        print(f"✅ Resultado guardado en BD (ID: {result_record.id}, Status: {result_record.status})")

        # 7️⃣ Retornar respuesta
        return ExecutionResponse(
            case_id=test_case.id,
            code=python_code[:2000] + "..." if len(python_code) > 2000 else python_code,
            output=execution_result.get("output", "Sin output"),
            success=execution_result.get("success", False),
            logs=f"🔗 Manus: {share_url}\n⏱️ Tiempo: {execution_time}\n📊 Result ID: {result_record.id}\n\n📊 Logs:\n{execution_result.get('logs', '')}",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error en execute_case:\n{error_trace}")
        
        # 💾 Guardar error en BD si no se guardó resultado
        if not result_record:
            result_record = TestResult(
                test_case_id=test_case.id,
                status="error",
                logs=error_trace,
                screenshot_path=None,
                execution_time=f"{(datetime.now() - start_time).seconds}s",
                executed_by_agent=False
            )
            db.add(result_record)
            db.commit()
        
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
