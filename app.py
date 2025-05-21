from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary
from skimage import exposure
import numpy as np
import pytesseract
from PIL import Image
import io
import os
import cv2
import re
import subprocess



app = Flask(__name__)

# Конфигурация базы данных (пример)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TextCleaner:
    def __init__(self):
        # Список матерных слов и их форм (можно расширить)
        self.profanity_words = {
            'блять', 'бля', 'бляха', 'бл', 'сука', 'суки', 'нихуя', 'хуй', 'хуя', 'пизд',
            'пиздец', 'еб', 'ебан', 'выеб', 'заеб', 'отсосел', 'кончил',
            'мудак', 'дебил', 'гандон', 'шлюха', 'мразь'
        }

        self.profanity_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(word) for word in self.profanity_words) + r')\b',
            re.IGNORECASE
        )

    def clean_text(self, text):
        # Простая замена через регулярные выражения
        return self.profanity_pattern.sub('***', text)

def enhance_image(image):
    """Улучшение качества изображения"""
    image = exposure.adjust_gamma(image, gamma=0.8)
    image = exposure.adjust_log(image, inv=True)
    image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    return image

def preprocess_image(image):
    """Предварительная обработка изображения"""
    image = enhance_image(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((1, 1), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return thresh


# Модель для хранения изображений и результатов OCR
class OcrResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_data = db.Column(LargeBinary)
    text_result = db.Column(db.Text)
    filename = db.Column(db.String(100))


# Инициализация базы данных
with app.app_context():
    db.create_all()

# Укажите явный путь (вариант для Docker)
TESSERACT_PATH = '/usr/bin/tesseract'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

@app.route("/")
def header():
    return render_template("header.html")


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            # Чтение изображения
            text_cleaner = TextCleaner()

            # Конвертация в numpy array
            image_bytes = file.read()
            image = Image.open(io.BytesIO(image_bytes))

            # Конвертация PIL.Image -> numpy array (в формате BGR для OpenCV)
            image_np = np.array(image)
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

            # Обработка изображения
            processed = enhance_image(image_np)

            # Применение Tesseract OCR
            text = pytesseract.image_to_string(processed, lang='rus')

            # Очистка текста
            text = text_cleaner.clean_text(text)
            text = re.sub(r'[^\w\sА-Яа-яЁё.,!?;:-]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            # Сохранение в базу данных
            new_result = OcrResult(
                image_data=image_bytes,  # сохраняем оригинальные байты
                text_result=text,
                filename=file.filename
            )
            db.session.add(new_result)
            db.session.commit()

            return jsonify({
                'text': text,
                'id': new_result.id
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/results/<int:result_id>')
def get_result(result_id):
    result = OcrResult.query.get_or_404(result_id)
    return jsonify({
        'text': result.text_result,
        'filename': result.filename
    })


if __name__ == '__main__':
    app.run(debug=True)