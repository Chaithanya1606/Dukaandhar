FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and static files
COPY backend /app/backend

# Create directory for persistent data
RUN mkdir -p /app/data

# Environment variable for database path (allows mounting persistent volume if needed)
ENV DB_PATH=/app/data/cement_store.db
ENV PORT=8000

EXPOSE 8000

CMD ["python", "backend/run_server.py"]
