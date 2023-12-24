FROM lwthiker/curl-impersonate:0.5-chrome-alpine AS builder

FROM python:3.9-alpine

ENV PYTHONFAULTHANDLER=1 \
     PYTHONUNBUFFERED=1 \
     PYTHONDONTWRITEBYTECODE=1 \
     PIP_DISABLE_PIP_VERSION_CHECK=on

COPY --from=builder /usr/local /usr/local

RUN apk --no-cache add ffmpeg build-base nss ca-certificates

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt --no-cache-dir

RUN apk del build-base

RUN ln -s /etc/ssl/certs/ca-certificates.crt /usr/local/lib/python3.9/site-packages/curl_cffi/cacert.pem

CMD ["python", "bot/main.py"]