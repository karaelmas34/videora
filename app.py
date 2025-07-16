from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import json
import uuid
import shutil
import threading
import time
from progress_hook import progress_writer

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cookie-test')
def cookie_test():
    return jsonify({'cookie_exists': os.path.exists("cookies.txt")})

@app.route('/download', methods=['POST'])
def download():
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

        # Gecikmeli temizlik
        def delayed_cleanup(path):
            time.sleep(20)
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"Temizlik hatası: {e}")

        threading.Thread(target=delayed_cleanup, args=(user_dir,), daemon=True).start()

        return jsonify({'status': 'success', 'user_id': user_id})

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
    app.run(host='0.0.0.0', port=10000, debug=True)
