# Agent Guardrail — zero-setup container
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV AGENT_GUARDRAIL_PORT=8080
EXPOSE 8080

WORKDIR /app/src
CMD ["sh", "-c", "uvicorn policy_engine:app --host 0.0.0.0 --port ${AGENT_GUARDRAIL_PORT}"]