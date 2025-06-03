from flask import Flask, Response, render_template_string, jsonify
import cv2
import boto3
import threading
from botocore.config import Config
import time
from datetime import datetime

app = Flask(__name__)

# AWS S3 setup with forced Signature Version 4
my_config = Config(signature_version='s3v4')
s3 = boto3.client('s3', region_name='eu-north-1', config=my_config)
BUCKET_NAME = 'motion-detect-pi'  # Replace with your actual S3 bucket

# Motion control
last_motion_time = 0
motion_cooldown = 10  # seconds
cooldown_active = False

# Camera setup
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not camera.isOpened():
    print("Could not open camera!")
    exit()

# Camera lock
camera_lock = threading.Lock()

# Motion detection function
def detect_motion():
    global last_motion_time, cooldown_active

    time.sleep(2)  # Camera warm-up

    with camera_lock:
        ret, frame1 = camera.read()
        ret, frame2 = camera.read()

    print("Motion detection started in background.")

    while True:
        current_time = time.time()
        with camera_lock:
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours and (current_time - last_motion_time > motion_cooldown):
            last_motion_time = current_time
            cooldown_active = True

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"motion_{timestamp}.jpg"
            with camera_lock:
                cv2.imwrite(filename, frame1)
            print(f"Motion detected! Saved: {filename}")

            with open(filename, 'rb') as f:
                s3.upload_fileobj(f, BUCKET_NAME, f"uploads/{filename}")
            print("Uploaded to S3.")

            time.sleep(2)
            with camera_lock:
                ret, frame1 = camera.read()
                ret, frame2 = camera.read()

        else:
            with camera_lock:
                frame1 = frame2
                ret, frame2 = camera.read()

            if cooldown_active and (current_time - last_motion_time > motion_cooldown):
                print("Cooldown ended. Ready to detect new motion.")
                cooldown_active = False

# Start motion detection in a background thread
detection_thread = threading.Thread(target=detect_motion, daemon=True)
detection_thread.start()

# Flask route to serve the gallery and stream trigger
@app.route('/')
def index():
    return render_template_string('''
    <html>
    <head>
        <title>Smart Security Camera</title>
        <style>
            body { display: flex; }
            .left { width: 60%; padding: 10px; }
            .right { width: 40%; padding: 10px; overflow-y: scroll; height: 90vh; }
            img { max-width: 100%; height: auto; margin-bottom: 5px; }
            .gallery-item { margin-bottom: 20px; }
            .timestamp { font-size: 12px; color: #555; text-align: center; margin-top: 5px; }
            button { margin: 5px 0; padding: 10px; }
        </style>
        <script>
            async function loadGallery() {
                const response = await fetch('/gallery');
                const images = await response.json();
                const gallery = document.getElementById('gallery');
                gallery.innerHTML = images.map(item => 
                    `<div class="gallery-item">
                        <img class="gallery-img" src="${item.url}" alt="Motion Capture">
                        <div class="timestamp">${item.timestamp}</div>
                    </div>`
                ).join('');
            }

            function startStream() {
                const streamContainer = document.getElementById('streamContainer');
                streamContainer.innerHTML = '<img src="/stream?rand=' + Math.random() + '">';
            }

            function refreshGalleryAndStream() {
                loadGallery();
                startStream();
            }

            function refreshStream() {
                startStream();
            }

            window.onload = loadGallery;
        </script>
    </head>
    <body>
        <div class="left">
            <h1>Motion Captures</h1>
            <button onclick="refreshGalleryAndStream()">Refresh Gallery + Stream</button>
            <div id="gallery"></div>
        </div>
        <div class="right">
            <h2>Live Stream</h2>
            <button onclick="startStream()">Start Live Stream</button>
            <button onclick="refreshStream()">Refresh Live Stream</button>
            <div id="streamContainer"></div>
        </div>
    </body>
    </html>
    ''')

@app.route('/stream')
def stream():
    def generate_frames():
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
        while True:
            with camera_lock:
                success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.07)  # limit FPS to ~14

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/gallery')
def gallery():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='uploads/')
    images = []

    if 'Contents' in response:
        for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:20]:
            url = s3.generate_presigned_url('get_object',
                                            Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']},
                                            ExpiresIn=3600)
            # Extract timestamp from filename
            key_name = obj['Key'].split('/')[-1]
            if key_name.startswith('motion_') and key_name.endswith('.jpg'):
                timestamp_str = key_name.replace('motion_', '').replace('.jpg', '')
                timestamp_formatted = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_formatted = 'Unknown Time'
            images.append({'url': url, 'timestamp': timestamp_formatted})

    return jsonify(images)

if __name__ == '__main__':
    print("Starting Flask server with motion detection and gallery...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False, threaded=True)
