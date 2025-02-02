FROM python:3.11-alpine

WORKDIR /app

# 必要なビルドツールをインストール
RUN apk add --no-cache build-base libffi-dev cmake geos-dev

ENV GEOS_CONFIG=/usr/bin/geos-config

# 必要なパッケージをインストール
RUN apk add --no-cache \
    libmagic \
    gcc \
    musl-dev \
    linux-headers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5200"]
