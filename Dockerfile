FROM python:3.10-slim

RUN apt-get update && \
    apt-get install ffmpeg -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/

COPY --chown=appuser . .
RUN pip install -r requirements.txt --no-cache-dir

CMD ["python", "main.py"]