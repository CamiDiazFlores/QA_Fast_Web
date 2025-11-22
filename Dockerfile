# ==========================
#  Etapa 1: Imagen base
# ==========================
FROM python:3.11-slim AS base

# Evita crear archivos .pyc y asegura logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# ==========================
#  Etapa 2: Instalar dependencias del sistema
# ==========================
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# ==========================
#  Etapa 3: Instalar dependencias Python
# ==========================
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ==========================
#  Etapa 4: Copiar código fuente
# ==========================
COPY app/ /app/app/

# ==========================
#  Etapa 5: Variables de entorno (opcional)
# ==========================
# Puedes cambiar estas según tus valores reales
ENV APP_ENV=production
ENV DATABASE_URL=mysql+pymysql://root:root@mysql_db:3306/qa_db
ENV AGENT_URL=http://qa-agent:8081
ENV MANUS_IA_URL=https://api.manus.ai/v1/generate
ENV MANUS_API_KEY=tu_token_aqui

# ==========================
#  Etapa 6: Exponer puerto
# ==========================
EXPOSE 8080

# ==========================
#  Etapa 7: Comando de inicio (modo producción)
# ==========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
