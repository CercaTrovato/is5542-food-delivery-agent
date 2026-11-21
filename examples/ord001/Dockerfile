FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir \
    langgraph==1.2.19 \
    langchain==1.4.9 \
    langchain-openai==1.7.4 \
    starlette==1.10.0 \
    uvicorn==0.54.0 \
    python-multipart==0.0.20 \
    httpx==0.28.1

ENV PORT=7860
ENV ORD001_PRODUCTION_MODE=1
ENV ORD001_STRICT_SOD=1
VOLUME ["/data"]
EXPOSE 7860

CMD ["sh", "-c", "mkdir -p /data && python ord001_web.py --host 0.0.0.0 --port ${PORT:-7860} --db ${ORD001_DB_PATH:-/data/ord001-prod.sqlite3}"]
