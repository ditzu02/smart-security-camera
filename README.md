
# Smart Security Camera with Motion Detection and Live Streaming

A Raspberry Pi-based smart security camera system with motion detection and real-time live streaming. Captured motion events are automatically uploaded to AWS S3 and can be browsed in a web gallery.

---

## Features

- **Live Stream**: View real-time video feed in a web browser.
- **Motion Detection**: Detects motion and captures frames.
- **AWS S3 Upload**: Captured frames are automatically uploaded to a configured S3 bucket.
- **Motion Event Gallery**: View the gallery of captured motion events.
- **Thread-Safe Camera Access**: Uses threading locks to safely share the camera between motion detection and streaming.

---

## Demo

|Motion Gallery |
|----------------|
|![motion_20250602_171451](https://github.com/user-attachments/assets/a54a50cd-d3ef-42b2-b687-9743da93a664)|

---

## Requirements

- Raspberry Pi (or any Linux-based machine)
- USB Webcam
- Python 3.7+
- AWS Account (S3 bucket)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ditzu02/smart-security-camera.git
cd smart-security-camera
```

### 2. Install Dependencies

```bash
pip install flask opencv-python boto3
```

For Raspberry Pi additional dependencies:

```bash
sudo apt-get install libatlas-base-dev libjasper-dev libqtgui4 python3-pyqt5
```

### 3. AWS Setup

- Create an S3 bucket (e.g., `motion-detect-pi`).
- Create an IAM user and attach the following policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::motion-detect-pi",
        "arn:aws:s3:::motion-detect-pi/uploads/*"
      ]
    }
  ]
}
```

- Configure AWS credentials:

```bash
aws configure
```

or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=eu-north-1
```

---

## Running the Application

### 1. Development (Flask)

```bash
python3 app.py
```

### 2. Production (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

---

## Usage

1. Access the web application at:
   ```
   http://<raspberry-pi-ip>:5000
   ```

2. **Live Stream**:
   - Click `Start Live Stream` to view real-time video.

3. **Gallery**:
   - Click `Refresh Gallery + Stream` to reload new captures.

Captured images are uploaded to S3 automatically when motion is detected.

---

## Project Structure

| File         | Description                             |
|--------------|-----------------------------------------|
| `app.py`     | Main Flask application.                 |
| `templates/` | Inline HTML templates (in the Python).  |
| `uploads/`   | S3 bucket path for captured images.      |

---

## Configuration

You can modify the following parameters in the `app.py` file:

| Parameter             | Description                       | Default         |
|------------------------|-----------------------------------|-----------------|
| `motion_cooldown`       | Time delay between captures       | `10` seconds    |
| `JPEG Quality`          | JPEG image compression quality    | `60%`           |
| `Frame Width/Height`    | Camera resolution                 | `640x480`       |
| `AWS_REGION`            | AWS S3 bucket region              | `eu-north-1`    |

---

## Known Issues

- Only one camera should be connected and available as `/dev/video0`.
- Make sure your AWS S3 bucket permissions are correctly configured.
- The server currently runs without authentication.

---

## Future Improvements

- Add authentication and user management.
- Add email or SMS alerts on motion detection.
- Integrate cloud archival or cleanup system.
- Secure the application with HTTPS.

---


## Acknowledgements

- [OpenCV](https://opencv.org/)
- [Flask](https://flask.palletsprojects.com/)
- [AWS S3](https://aws.amazon.com/s3/)
