FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY ticket_server ./ticket_server
RUN pip install --no-cache-dir .

EXPOSE 8001
CMD ["python", "-m", "ticket_server"]
