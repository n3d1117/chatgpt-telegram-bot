FROM python:3.9

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libcurl4-openssl-dev \
    gcc \
    libc6-dev \
    libffi-dev \
    openssl \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt --no-cache-dir

CMD ["python", "bot/main.py"]
