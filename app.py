from flask import Flask, render_template, request
import subprocess
import os

app = Flask(__name__)

# Ana sayfa
@app.route('/')
def index():
    return render_template('index.html')

# Video indirme işlemi
@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('video_url')

    if not video_url:
        return render_template('result.html', status="Lütfen geçerli bir bağlantı girin.")

    command = [
        'yt-dlp',
        '--cookies', 'cookies.txt',
        video_url
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            if "confirm you're not a bot" in result.stderr.lower():
                status = "Bu video, YouTube tarafından erişim kısıtlamasına tabi tutulmuş olabilir. Lütfen farklı bir bağlantı deneyin."
            else:
                status = f"İndirme hatası oluştu:\n{result.stderr}"
        else:
            status = "Video başarıyla indirildi!"
    
    except Exception as e:
        status = f"Beklenmeyen bir hata oluştu:\n{str(e)}"

    return render_template('result.html', status=status)

# Uygulama başlatma
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
