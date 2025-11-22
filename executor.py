"""
🤖 EXECUTOR SERVICE - Selenium Grid Remote Execution
Servicio HTTP que ejecuta código Python con Selenium conectándose a Selenium Grid.
Chrome se ejecuta en el Node del Grid, no localmente.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import sys
import io
import traceback
from datetime import datetime
from typing import Optional
import builtins

app = FastAPI(title="QA Executor Service", version="2.0.0")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🌐 CONFIGURACIÓN DE SELENIUM GRID
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SELENIUM_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444/wd/hub")

class ExecutionRequest(BaseModel):
    script: str
    test_name: str = "test"
    browser: str = "chrome"
    headless: bool = False

class ExecutionResponse(BaseModel):
    status: str
    data: dict

def create_remote_driver(headless: bool = False) -> webdriver.Remote:
    """
    Crea un WebDriver remoto conectado al Selenium Grid Hub.
    Chrome se ejecuta en el Node del Grid.
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Opciones para entorno containerizado
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    print(f"🌐 Conectando a Selenium Grid: {SELENIUM_HUB_URL}")
    
    try:
        driver = webdriver.Remote(
            command_executor=SELENIUM_HUB_URL,
            options=chrome_options
        )
        print(f"✅ Conectado al Grid - Session ID: {driver.session_id}")
        return driver
        
    except Exception as e:
        print(f"❌ Error conectando a Grid: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar a Selenium Grid en {SELENIUM_HUB_URL}. Verifica que el Hub esté corriendo."
        )

def execute_selenium_code(script: str, test_name: str, headless: bool = False) -> dict:
    """
    Ejecuta código Python con Selenium usando Remote WebDriver.
    """
    driver = None
    output_buffer = io.StringIO()
    original_stdout = sys.stdout
    screenshot_path = None
    
    try:
        # Crear driver remoto
        driver = create_remote_driver(headless=headless)
        
        # Redirigir stdout para capturar prints
        sys.stdout = output_buffer
        
        # Preparar entorno de ejecución
        exec_globals = {
            "__builtins__": builtins,
            "driver": driver,
            "webdriver": webdriver,
            "Options": Options,
            "print": print,
        }
        
        # Ejecutar script
        exec(script, exec_globals)
        
        # Capturar screenshot final
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{test_name}_{timestamp}.png"
        screenshot_path = os.path.join("results", screenshot_filename)
        
        os.makedirs("results", exist_ok=True)
        driver.save_screenshot(screenshot_path)
        
        output = output_buffer.getvalue()
        
        return {
            "message": "✅ Ejecución exitosa",
            "output": output if output else "Sin output",
            "screenshot": screenshot_path,
            "session_id": driver.session_id
        }
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error durante ejecución:\n{error_trace}")
        
        # Intentar capturar screenshot del error
        if driver:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_filename = f"{test_name}_ERROR_{timestamp}.png"
                screenshot_path = os.path.join("results", screenshot_filename)
                os.makedirs("results", exist_ok=True)
                driver.save_screenshot(screenshot_path)
            except:
                pass
        
        return {
            "message": f"❌ Error: {str(e)}",
            "output": output_buffer.getvalue(),
            "error": error_trace,
            "screenshot": screenshot_path
        }
        
    finally:
        sys.stdout = original_stdout
        if driver:
            try:
                driver.quit()
                print(f"✅ WebDriver cerrado correctamente")
            except Exception as quit_error:
                print(f"⚠️ Error al cerrar driver: {quit_error}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📡 ENDPOINTS HTTP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/")
async def root():
    return {
        "service": "QA Executor with Selenium Grid",
        "version": "2.0.0",
        "selenium_hub": SELENIUM_HUB_URL,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Verifica conexión con Selenium Grid"""
    try:
        driver = create_remote_driver(headless=True)
        session_id = driver.session_id
        driver.quit()
        
        return {
            "status": "healthy",
            "selenium_hub": SELENIUM_HUB_URL,
            "grid_connection": "ok",
            "test_session_id": session_id
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "selenium_hub": SELENIUM_HUB_URL,
            "grid_connection": "failed",
            "error": str(e)
        }

@app.post("/execute", response_model=ExecutionResponse)
async def execute_test(request: ExecutionRequest):
    """
    Ejecuta código Selenium en el Grid.
    Chrome se ejecuta en el Node del Grid, no en el Executor.
    """
    print(f"\n{'='*80}")
    print(f"🚀 NUEVA EJECUCIÓN: {request.test_name}")
    print(f"🌐 Hub: {SELENIUM_HUB_URL}")
    print(f"👁️ Headless: {request.headless}")
    print(f"{'='*80}\n")
    
    try:
        result = execute_selenium_code(
            script=request.script,
            test_name=request.test_name,
            headless=request.headless
        )
        
        status = "success" if "error" not in result else "failed"
        
        return ExecutionResponse(
            status=status,
            data=result
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error en endpoint /execute:\n{error_trace}")
        
        return ExecutionResponse(
            status="error",
            data={
                "message": f"Error: {str(e)}",
                "error": error_trace
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
