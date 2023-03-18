FROM python:3.10-slim

RUN apt-get update && \
    apt-get install ffmpeg -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/
ENV PATH="/home/appuser/.local/bin:$PATH"

RUN pip install --user pipenv --no-cache-dir
COPY Pipfile* ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY app ./
CMD ["python", "main.py"]
