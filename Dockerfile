FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Statik dosyaları (CSS) toplar; WhiteNoise bunları gunicorn üzerinden sunar
RUN python manage.py collectstatic --noinput

# Container root olarak çalışmasın
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "otoradar_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]
