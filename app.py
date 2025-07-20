from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import json
import uuid
import shutil
import requests
from progress_hook import progress_writer

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ Cloudflare Turnstile doğrulama
def verify_turnstile(token):
    secret_key = "0x4AAAAAABlvkAABpBjavLJPU2Dwa4JKJkM"
    payload = {'secret': secret_key, 'response': token}
    r = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=payload)
    result = r.json()
    return result.get("success", False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    token = request.form.get('cf-turnstile-response')
    if not verify_turnstile(token):
        return jsonify({'status': 'error', 'message': 'Doğrulama başarısız'}), 403

    url = request.form['url']
    format_choice = request.form['format']
    resolution = request.form['resolution']

    user_id = str(uuid.uuid4())
    user_dir = os.path.join(DOWNLOAD_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    outtmpl = os.path.join(user_dir, '%(title)s.%(ext)s')
    progress_file = os.path.join(user_dir, 'progress.json')

    cookie_file = "cookies.txt"  # ✅ Kullanıcı tarafından yüklenmiş olmalı

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
        'cookiesfromfile': cookie_file,  # ✅ Cookie dosyası dahil edildi
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
                # ✅ Cookie dosyasını da sil (isteğe bağlı)
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)
                    print("✅ cookies.txt dosyası silindi.")
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
