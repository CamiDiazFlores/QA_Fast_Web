from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, Base, engine
from app.utils.logger import setup_logger

# ⚠️ IMPORTANTE: Importar TODOS los modelos ANTES de crear las tablas
from app.models.case_model import TestCase
from app.models.result_model import TestResult
from app.models.prompt_model import Prompt

# Importar rutas
from app.routes import cases, execute, dashboard

# Crear tablas si no existen
try:
    print("🔌 Conectando a base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente")
except Exception as e:
    print(f"❌ Error al crear tablas: {e}")

# ===============================
# CONFIGURAR APLICACIÓN FASTAPI
# ===============================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend de automatización QA con Selenium + IA (Manus)"
)

# ===============================
# CONFIGURAR CORS
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# CONFIGURAR LOG
# ===============================
logger = setup_logger("main")
logger.info("Iniciando servidor QA Automation Backend...")

# ===============================
# REGISTRAR RUTAS
# ===============================
app.include_router(cases.router, prefix="/api/cases", tags=["Casos de prueba"])
app.include_router(execute.router, prefix="/api/execute", tags=["Ejecución de pruebas"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# ===============================
# ENDPOINT RAÍZ
# ===============================
@app.get("/")
def root():
    logger.info("API raiz consultada")
    return {"message": "QA Automation Backend activo", "version": settings.PROJECT_VERSION}
