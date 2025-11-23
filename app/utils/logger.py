import logging
from logging.handlers import RotatingFileHandler
import os

# Usar carpeta segura y escribible en cualquier plataforma (Render, Railway, Docker)
LOG_DIR = "/tmp/logs"

# Crear directorio sin romper si no hay permisos (fallback a /tmp)
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    LOG_DIR = "/tmp"

def setup_logger(name: str) -> logging.Logger:
    """
    Configura un logger con rotación de archivos.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, f"{name}.log"),
        maxBytes=2_000_000,
        backupCount=5
    )

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
