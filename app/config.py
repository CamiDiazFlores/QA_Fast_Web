from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "QA Automation Backend"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://qa_db_aenc_user:RcxAQ6lXjQivUS5jQ0v9XiiUHdeNdh8B@dpg-d4hbjv6mcj7s73bttn50-a.oregon-postgres.render.com/qa_db_aenc?sslmode=require")
    MANUS_IA_API: str = os.getenv("MANUS_IA_API", "https://api.manusia.com/v1/generate")
    AGENT_EXECUTOR_URL: str = os.getenv("AGENT_EXECUTOR_URL", "https://executer-qa-fast-web-server.onrender.com/execute")
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:4200,http://127.0.0.1:4200"
    BACKEND_PORT: int = 8081

    @property
    def origins_list(self) -> List[str]:
        """Retorna ALLOWED_ORIGINS como lista"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
        return self.ALLOWED_ORIGINS

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Evitar validación extra de variables de entorno
        extra = "allow"

settings = Settings()

# Configuración de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica la conexión antes de usar
    pool_recycle=3600,   # Recicla conexiones cada hora
    echo=False           # No mostrar todas las consultas SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Test connection to PostgreSQL using psycopg
DATABASE_URL = "postgresql+psycopg://qa_db_aenc_user:RcxAQ6lXjQivUS5jQ0v9XiiUHdeNdh8B@dpg-d4hbjv6mcj7s73bttn50-a.oregon-postgres.render.com/qa_db_aenc"

try:
    conn = psycopg.connect(DATABASE_URL)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
