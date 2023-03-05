FROM python:3.10-slim

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/

ENV PATH="/home/appuser/.local/bin:$PATH"
RUN pip install --user pipenv

WORKDIR /home/appuser/app
COPY . .
COPY .env .

USER root
RUN apt-get update && apt-get install ffmpeg -y
USER appuser

RUN pipenv install --system --deploy --ignore-pipfile

CMD ["python", "main.py"]