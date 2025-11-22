# Importar todos los modelos para que SQLAlchemy los registre
from app.models.case_model import TestCase
from app.models.result_model import TestResult
from app.models.prompt_model import Prompt

# Exportar los modelos
__all__ = ["TestCase", "TestResult", "Prompt"]
