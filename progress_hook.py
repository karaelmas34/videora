import json

def progress_writer(d, path):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
        downloaded = d.get('downloaded_bytes', 0)
        percent = round(downloaded / total * 100, 2)
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)

        with open(path, 'w') as f:
            json.dump({'percent': percent, 'speed': speed, 'eta': eta}, f)