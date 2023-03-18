FROM python:3.9-alpine

RUN apt-get update && \
    apt-get install ffmpeg -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/app

COPY --chown=appuser . .
RUN pip install -r requirements.txt --no-cache-dir

CMD ["python", "bot/main.py"]