from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import json
import uuid
import shutil
import threading
import time
import requests  # ✅ reCAPTCHA doğrulaması için gerekli
from progress_hook import progress_writer

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ reCAPTCHA doğrulama fonksiyonu
def verify_recaptcha(token):
    secret_key = "6LcEY4crAAAAADo4OS9wcJiR8aUUq-0qnhGP5zMS"
    payload = {
        'secret': secret_key,
        'response': token
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = r.json()
    return result.get('success', False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    # ✅ reCAPTCHA doğrulaması
    recaptcha_token = request.form.get('g-recaptcha-response')
    if not verify_recaptcha(recaptcha_token):
        return jsonify({'status': 'error', 'message': 'reCAPTCHA doğrulaması başarısız'}), 403

    url = request.form['url']
    format_choice = request.form['format']
    resolution = request.form['resolution']

    user_id = str(uuid.uuid4())
    user_dir = os.path.join(DOWNLOAD_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    outtmpl = os.path.join(user_dir, '%(title)s.%(ext)s')
    progress_file = os.path.join(user_dir, 'progress.json')

    with open(progress_file, 'w') as f:
        json.dump({'percent': 0, 'speed': 0, 'eta': 0}, f)

    def hook_with_id(d):
        progress_writer(d, progress_file)

    video_filter = (
        f'bestvideo[height<={resolution}]+bestaudio/best'
        if format_choice == 'mp4' else 'bestaudio/best'
    )

    ydl_opts = {
        'outtmpl': outtmpl,
        'format': video_filter,
        'merge_output_format': 'mp4' if format_choice == 'mp4' else None,
        'socket_timeout': 60,
        'progress_hooks': [hook_with_id],
        'cookiesfromfile': 'cookies.txt',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ] if format_choice == 'mp3' else [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }
        ]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        response_file = None
        for ext in ['.mp3', '.mp4']:
            for file in os.listdir(user_dir):
                if file.endswith(ext):
                    response_file = os.path.join(user_dir, file)
                    break

        if not response_file:
            return jsonify({'status': 'error', 'message': 'Dosya bulunamadı'}), 404

        response = send_file(response_file, as_attachment=True)

        def cleanup():
            try:
                shutil.rmtree(user_dir)
                print(f"✅ Klasör silindi: {user_id}")
            except Exception as e:
                print(f"❌ Temizlik hatası: {e}")

        response.call_on_close(cleanup)
        return response

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/progress/<user_id>')
def progress(user_id):
    progress_file = os.path.join(DOWNLOAD_DIR, user_id, 'progress.json')
    try:
        with open(progress_file, 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({'percent': 0, 'speed': 0, 'eta': 0})

@app.route('/file/<user_id>')
def file_download(user_id):
    user_dir = os.path.join(DOWNLOAD_DIR, user_id)
    try:
        for ext in ['.mp3', '.mp4']:
            for file in os.listdir(user_dir):
                if file.endswith(ext):
                    full_path = os.path.join(user_dir, file)
                    return send_file(full_path, as_attachment=True)
        return jsonify({'status': 'error', 'message': 'Dosya bulunamadı'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# app.py'nin en sonunda sadece bu olsun:
if __name__ == '__main__':
    pass  # Lokal test için buraya app.run() eklenebilir