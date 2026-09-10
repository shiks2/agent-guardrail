# Agent Guardrail — hardened container
FROM python:3.12-slim

# Create dedicated non-root user
RUN groupadd -g 1000 guardrail && \
    useradd -u 1000 -g guardrail -m -s /bin/sh guardrail

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=guardrail:guardrail src/ ./src/

ENV AGENT_GUARDRAIL_HOST=0.0.0.0
ENV AGENT_GUARDRAIL_PORT=8080
EXPOSE 8080

VOLUME ["/app/src"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os, sys; port = os.getenv('AGENT_GUARDRAIL_PORT', '8080'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz').status == 200 else 1)"

USER guardrail

WORKDIR /app/src
CMD ["sh", "-c", "uvicorn policy_engine:app --host ${AGENT_GUARDRAIL_HOST} --port ${AGENT_GUARDRAIL_PORT}"]