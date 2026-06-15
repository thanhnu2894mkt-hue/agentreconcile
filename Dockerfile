# Agent doi soat ZION <-> SACOMBANK — Claw-a-thon 2026 (GreenNode AgentBase)
FROM python:3.11-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source + Brain + du lieu
COPY config.py run.py agent.py CLAUDE.md ./
COPY src ./src
COPY data ./data

ENV INPUT_DIR=/app/data/input OUTPUT_DIR=/app/data/output
EXPOSE 8080

# Mac dinh: chay agent server (endpoint public cho AgentBase).
# Chay batch 1 lan thay vi server:  docker run ... python run.py
CMD ["python", "agent.py"]
