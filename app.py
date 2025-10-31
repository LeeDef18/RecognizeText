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

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TextCleaner:
    def __init__(self):
        self.profanity_words = {
            'блять', 'бля', 'бляха', 'бл', 'сука', 'суки', 'нихуя', 'хуй', 'хуя', 'пизд',
            'пиздец', 'еб', 'ебан', 'выеб', 'заеб', 'отсосел', 'кончил',
            'мудак', 'дебил', 'гандон', 'шлюха', 'мразь', 'В пизде', 'ебутся', 'мандей', 'сраку', 'жопа'
        }

        self.profanity_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(word) for word in self.profanity_words) + r')\b',
            re.IGNORECASE
        )

    def clean_text(self, text):
        return self.profanity_pattern.sub('***', text)

def enhance_image(image):
    image = exposure.adjust_gamma(image, gamma=0.8)
    image = exposure.adjust_log(image, inv=True)
    image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    return image

def preprocess_image(image):
    image = enhance_image(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((1, 1), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return thresh

class OcrResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_data = db.Column(LargeBinary)
    text_result = db.Column(db.Text)
    filename = db.Column(db.String(100))

with app.app_context():
    db.create_all()

try:
    subprocess.run(['tesseract', '--version'], check=True, capture_output=True)
except Exception as e:
    raise RuntimeError(f"Tesseract check failed: {e}")

TESSERACT_PATH = '/usr/bin/tesseract'
if not os.path.exists(TESSERACT_PATH):
    raise FileNotFoundError(f"Tesseract not found at {TESSERACT_PATH}")
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
            text_cleaner = TextCleaner()
            image_bytes = file.read()
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            processed = enhance_image(image_np)
            text = pytesseract.image_to_string(processed, lang='rus')
            text = text_cleaner.clean_text(text)
            text = re.sub(r'[^\w\sА-Яа-яЁё.,!?;:-]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            new_result = OcrResult(
                image_data=image_bytes,
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

