FROM python:3.12-slim

WORKDIR /monorepo

COPY apps/workers/requirements.txt apps/workers/requirements.txt
RUN pip install --no-cache-dir -r apps/workers/requirements.txt

# Copia o monorepo inteiro para que "data.ingestion.*" seja importável
COPY . .

WORKDIR /monorepo/apps/workers

CMD ["python", "run_ingestion.py"]
