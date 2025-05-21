# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr \
        tesseract-ocr-rus \
        tesseract-ocr-eng \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgl1-mesa-glx \
        libopencv-dev \
        poppler-utils \
        gcc && \
    echo "Tesseract path: $(which tesseract)" && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY . .


ENV TESSERACT_CMD=/usr/bin/tesseract
ENV FLASK_APP=app.py


EXPOSE 5000


CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

RUN tesseract --version && echo "Tesseract installed successfully"