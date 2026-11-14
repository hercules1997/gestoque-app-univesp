FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
ENV DISABLE_VISUAL_EDITS=true DISABLE_EMERGENT_OVERLAY=true
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt
COPY backend/ ./
COPY --from=frontend /build/dist ./static
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}"]
