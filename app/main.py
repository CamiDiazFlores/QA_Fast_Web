from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, Base, engine
from app.utils.logger import setup_logger

# Importar TODOS los modelos ANTES de crear las tablas
from app.models.case_model import TestCase
from app.models.result_model import TestResult
from app.models.prompt_model import Prompt

# Importar rutas
from app.routes import cases, execute, dashboard


# Crear tablas si no existen
try:
    print("[DB] Conectando a base de datos...")
    Base.metadata.create_all(bind=engine)
    print("[DB] Tablas creadas exitosamente")
except Exception as e:
    print(f"[ERROR] Error al crear tablas: {e}")

# Configurar aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend de automatización QA con Selenium + IA (Manus)"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar logger
logger = setup_logger("main")
logger.info("[INICIO] Servidor QA Automation Backend")
logger.info(f"[EXECUTOR] URL: {settings.AGENT_EXECUTOR_URL}")


# Registrar rutas
app.include_router(cases.router, prefix="/api/cases", tags=["Casos de prueba"])
app.include_router(execute.router, prefix="/api/execute", tags=["Ejecución de pruebas"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Endpoint raíz
@app.get("/")
def root():
    logger.info("[OK] API raiz consultada")
    return {
        "message": "QA Automation Backend activo",
        "version": settings.PROJECT_VERSION,
        "executor_service": settings.AGENT_EXECUTOR_URL,
       
    }