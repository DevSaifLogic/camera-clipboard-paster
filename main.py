import os
import io
import base64
import pyautogui
from PIL import Image
from flask import Flask, render_template_string, request, jsonify

# Optional: Fix for Linux users using PyAutoGUI
# import xclip 

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

PHONE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phone Camera Paste</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 30px; background: #111; color: white; }
        video, canvas { width: 95%; max-width: 500px; border-radius: 10px; background: #000; }
        button { padding: 20px; font-size: 18px; width: 95%; max-width: 500px; margin-top: 20px; border: none; background: #ff4757; color: white; border-radius: 8px; font-weight: bold; }
        button:active { background: #ff6b81; }
        #status { margin-top: 15px; font-weight: bold; font-size: 18px; color: #ffa502; }
    </style>
</head>
<body>
    <h3>Cursor Auto-Paste Cam</h3>
    <video id="video" autoplay playsinline></video>
    <br>
    <button id="capture">📸 SNAP & PASTE AT CURSOR</button>
    <div id="status">Ready</div>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const captureButton = document.getElementById('capture');
        const statusDiv = document.getElementById('status');

        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
            .then(stream => { video.srcObject = stream; })
            .catch(err => { statusDiv.innerText = "Camera error: " + err.message; });

        captureButton.addEventListener('click', () => {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const imageData = canvas.toDataURL('image/jpeg');
            statusDiv.innerText = "Sending to cursor...";

            fetch('/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    statusDiv.innerText = "Pasted!";
                    setTimeout(() => { statusDiv.innerText = "Ready"; }, 1500);
                } else {
                    statusDiv.innerText = "Error pasting.";
                }
            })
            .catch(err => { statusDiv.innerText = "Network Error"; });
        });
    </script>
</body>
</html>
"""

# Dynamic clipboard paste function depending on OS
def paste_image_to_clipboard(img):
    output = io.BytesIO()
    img.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:] # Strip BMP header for Windows compatibility
    output.close()
    
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
    except ImportError:
        # Mac/Linux Fallback (Requires dependencies like 'xclip' on Linux)
        import subprocess
        if os.name == 'posix': # Mac
            img.save('/tmp/img.png')
            subprocess.run(["osascript", "-e", "set the clipboard to (read (POSIX file \"/tmp/img.png\") as JPEG picture)"])

@app.route('/')
def phone_camera():
    return render_template_string(PHONE_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('image'), str):
        return jsonify({'success': False}), 400

    try:
        # Decode phone image data
        header, encoded = data['image'].split(",", 1)
        image_bytes = base64.b64decode(encoded, validate=True)
        
        # Open image using Pillow
        image = Image.open(io.BytesIO(image_bytes))

        # 1. Force the image into the system clipboard
        paste_image_to_clipboard(image)

        # 2. Simulate the universal "Ctrl + V" shortcut (or Cmd + V for Mac)
        if os.name == 'posix': # Mac OS
            pyautogui.hotkey('command', 'v')
        else: # Windows / Linux
            pyautogui.hotkey('ctrl', 'v')

        print("[+] Automatically pasted image at cursor position!")
        return jsonify({'success': True})
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({'success': False}), 500

if __name__ == '__main__':
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    cert_file = os.environ.get("SSL_CERT_FILE")
    key_file = os.environ.get("SSL_KEY_FILE")
    if bool(cert_file) != bool(key_file):
        raise SystemExit("Set both SSL_CERT_FILE and SSL_KEY_FILE to enable HTTPS.")
    ssl_context = (cert_file, key_file) if cert_file else None
    app.run(host=host, port=port, ssl_context=ssl_context, debug=False)