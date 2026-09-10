FROM python:3.12-slim

WORKDIR /monorepo

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

# Copia o monorepo inteiro para que "actions.*", "tasks.*" etc sejam importáveis
COPY . .

WORKDIR /monorepo/apps/api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
