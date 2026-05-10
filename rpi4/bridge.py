"""
FarmWatch Bridge — Raspberry Pi 4 (FULL HARDWARE VERSION)

Hardware setup:
  - INMP441 I2S microphone connected to the Pi (GPIO 18/19/20 + 3.3V/GND)
  - ESP32-CAM with buzzer on GPIO 4 (via transistor) and camera
  - Pi GPIO 17 optionally drives a local relay/buzzer (kept as backup)

Three threads run in parallel:
  1. sound_loop      — captures audio from the I2S mic, sends to Flask AI,
                       reports bird detections to Spring Boot
  2. camera_loop     — pulls snapshots from ESP32-CAM, sends to Flask AI
                       for visual confirmation, reports detections
  3. siren_sync_loop — polls Spring Boot for the siren state and triggers
                       the ESP32-CAM buzzer (and optionally the Pi GPIO)
"""

import datetime
import threading
import time
import os

import cv2
import numpy as np
import requests
import sounddevice as sd

# ── Optional: Raspberry Pi GPIO ─────────────────────────────
# Set USE_PI_GPIO = False if you don't want a local relay/buzzer on the Pi.
USE_PI_GPIO = True
SIREN_GPIO_PIN = 17

if USE_PI_GPIO:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SIREN_GPIO_PIN, GPIO.OUT)
        GPIO.output(SIREN_GPIO_PIN, GPIO.LOW)
    except (ImportError, RuntimeError) as e:
        print(f"⚠️  Pi GPIO unavailable ({e}); local buzzer disabled")
        USE_PI_GPIO = False

# ── Network configuration ───────────────────────────────────
FLASK_URL      = "http://localhost:4000"          # serveur_complet.py on the Pi
SPRINGBOOT_URL = "http://192.168.100.15:8082"     # Spring Boot on your PC
ESPCAM_IP      = "192.168.100.37"                 # ESP32-CAM IP

USERNAME = "admin"
PASSWORD = "admin123"
SECTOR_ID = 1

# ── Audio (INMP441 I2S) ─────────────────────────────────────
# The INMP441 outputs stereo 32-bit samples at 48 kHz on the I2S bus.
# We record at the native rate and downsample to 16 kHz for the model.
NATIVE_RATE      = 48000
NATIVE_CHANNELS  = 2
NATIVE_DTYPE     = "int32"
TARGET_RATE      = 16000
DURATION         = 1               # seconds per audio chunk
SILENCE_RMS      = 0.005           # below this energy → ignore (silence)
CONSECUTIVE_BIRD = 3               # require N consecutive positive frames
                                    # before reporting (filters false positives)

# ── Camera ─────────────────────────────────────────────────
CAMERA_FPS         = 1             # analyze 1 frame per second
DETECTION_COOLDOWN = 5             # seconds between camera reports

# ── Capture directory ──────────────────────────────────────
CAPTURE_DIR = "/home/islem/captures/oiseau"
os.makedirs(CAPTURE_DIR, exist_ok=True)

# ════════════════════════════════════════════════════════════
# JWT TOKEN MANAGEMENT
# ════════════════════════════════════════════════════════════
_token = None
_token_lock = threading.Lock()

def get_token(force_refresh=False):
    global _token
    with _token_lock:
        if _token and not force_refresh:
            return _token
        try:
            r = requests.post(
                f"{SPRINGBOOT_URL}/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD},
                timeout=5,
            )
            r.raise_for_status()
            _token = r.json().get("token")
            print("🔑 JWT token obtained")
            return _token
        except Exception as e:
            print(f"❌ Failed to get JWT token: {e}")
            return None

def auth_headers():
    t = get_token()
    return {"Authorization": f"Bearer {t}"} if t else {}

# ════════════════════════════════════════════════════════════
# ESP32-CAM BUZZER CONTROL
# ════════════════════════════════════════════════════════════
def esp_siren(on: bool):
    """Send /siren/on or /siren/off to the ESP32-CAM."""
    endpoint = "on" if on else "off"
    try:
        requests.get(f"http://{ESPCAM_IP}:82/siren/{endpoint}", timeout=2)
        print(f"🔊 ESP32-CAM siren {endpoint.upper()}")
    except Exception as e:
        print(f"⚠️  ESP32-CAM siren {endpoint} error: {e}")

def pi_siren(on: bool):
    """Drive the local Pi GPIO (optional)."""
    if not USE_PI_GPIO:
        return
    try:
        GPIO.output(SIREN_GPIO_PIN, GPIO.HIGH if on else GPIO.LOW)
        print(f"🔊 Pi GPIO siren {'ON' if on else 'OFF'}")
    except Exception as e:
        print(f"⚠️  Pi GPIO error: {e}")

def activate_siren():
    esp_siren(True)
    pi_siren(True)

def deactivate_siren():
    esp_siren(False)
    pi_siren(False)

# ════════════════════════════════════════════════════════════
# REPORT DETECTION TO SPRING BOOT
# ════════════════════════════════════════════════════════════
def report_detection(method, confidence, species="Bird", image_path=None):
    payload = {
        "sectorId":   SECTOR_ID,
        "method":     method,
        "confidence": round(float(confidence), 2),
        "speciesEst": species,
        "imagePath":  image_path,
        "detectedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        r = requests.post(
            f"{SPRINGBOOT_URL}/api/detections",
            json=payload,
            headers=auth_headers(),
            timeout=5,
        )
        if r.status_code == 401:
            get_token(force_refresh=True)
            r = requests.post(
                f"{SPRINGBOOT_URL}/api/detections",
                json=payload,
                headers=auth_headers(),
                timeout=5,
            )
        if r.status_code == 200:
            print(f"  ✅ Detection reported: {method} {confidence:.1f}%")
        else:
            print(f"  ⚠️  Backend HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  ❌ Report error: {e}")

# ════════════════════════════════════════════════════════════
# AUDIO DEVICE (INMP441 I2S)
# ════════════════════════════════════════════════════════════
def find_i2s_input_device():
    """Find the I2S microphone device id (googlevoicehat-soundcard)."""
    try:
        for i, dev in enumerate(sd.query_devices()):
            name = dev["name"].lower()
            if dev["max_input_channels"] > 0 and (
                "googlevoice" in name or "snd_rpi" in name or "i2s" in name
            ):
                return i, dev
    except Exception as e:
        print(f"⚠️  Device enumeration failed: {e}")
    return None, None

# ════════════════════════════════════════════════════════════
# SOUND DETECTION LOOP (INMP441)
# ════════════════════════════════════════════════════════════
def sound_loop():
    print("🎙️  Sound loop starting…")

    device_id, dev = find_i2s_input_device()
    if device_id is None:
        print("❌ No I2S microphone found.")
        print("   → Run `arecord -l` on the Pi.")
        print("   → Verify /boot/firmware/config.txt has: dtoverlay=googlevoicehat-soundcard")
        print("   → Reboot, then restart this script.")
        return
    print(f"   Using device [{device_id}] {dev['name']}")

    consecutive = 0

    while True:
        try:
            # Record stereo 32-bit audio at native rate
            audio = sd.rec(
                int(NATIVE_RATE * DURATION),
                samplerate=NATIVE_RATE,
                channels=NATIVE_CHANNELS,
                dtype=NATIVE_DTYPE,
                device=device_id,
            )
            sd.wait()

            # INMP441 outputs on the LEFT channel when L/R pin is tied to GND
            left = audio[:, 0].astype(np.float32)

            # Normalize int32 → float [-1.0, 1.0]
            left /= 2_147_483_648.0

            # Downsample 48 kHz → 16 kHz (every 3rd sample)
            audio_16k = left[::3]

            # Skip silence
            energy = float(np.sqrt(np.mean(audio_16k ** 2)))
            if energy < SILENCE_RMS:
                consecutive = 0
                continue

            # Send to Flask AI
            r = requests.post(
                f"{FLASK_URL}/analyser",
                json={"audio": audio_16k.tolist()},
                timeout=10,
            )
            result = r.json()

            label   = result.get("label", "?")
            prob    = result.get("probabilite", 0.0)
            is_bird = result.get("oiseau", False)
            print(f"  🎧 SOUND  {label:6s}  prob={prob*100:.1f}%  rms={energy:.3f}")

            if is_bird:
                consecutive += 1
                if consecutive >= CONSECUTIVE_BIRD:
                    print(f"🐦 BIRD CONFIRMED via sound (×{consecutive})")
                    report_detection("SOUND", prob * 100, species="Bird")
                    consecutive = 0
            else:
                consecutive = 0

        except Exception as e:
            print(f"  ❌ Sound loop error: {e}")
            time.sleep(1)

# ════════════════════════════════════════════════════════════
# CAMERA DETECTION LOOP (ESP32-CAM stream)
# ════════════════════════════════════════════════════════════
def camera_loop():
    print("📷 Camera loop starting…")

    stream_url = f"http://{ESPCAM_IP}:81/stream"
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"❌ Cannot open ESP32-CAM stream at {stream_url}")
        return

    last_detection = 0
    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                print("❌ Frame read failed, reconnecting in 2s…")
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(stream_url)
                continue

            now = time.time()
            if now - last_detection < DETECTION_COOLDOWN:
                time.sleep(0.5)
                continue

            # Encode and send to Flask
            _, img_encoded = cv2.imencode(".jpg", frame)
            r = requests.post(
                f"{FLASK_URL}/predict",
                data=img_encoded.tobytes(),
                headers={"Content-Type": "image/jpeg"},
                timeout=10,
            )
            result = r.json()

            if result.get("label") == "OISEAU":
                conf = result["confiance"]
                print(f"🐦 BIRD CONFIRMED via camera  conf={conf:.1f}%")

                # Save snapshot for the dashboard
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                snap_path = f"{CAPTURE_DIR}/snap_{ts}.jpg"
                cv2.imwrite(snap_path, frame)

                report_detection("CAMERA", conf, species="Bird",
                                 image_path=snap_path)
                last_detection = now

            time.sleep(1.0 / CAMERA_FPS)

        except Exception as e:
            print(f"  ❌ Camera loop error: {e}")
            time.sleep(1)

# ════════════════════════════════════════════════════════════
# SIREN SYNC LOOP
# ════════════════════════════════════════════════════════════
# Polls Spring Boot's /api/siren/status once per second and mirrors the
# state to the physical hardware (ESP32-CAM buzzer + optional Pi GPIO).
def siren_sync_loop():
    print("🔔 Siren sync loop starting…")
    last_state = False

    while True:
        try:
            r = requests.get(
                f"{SPRINGBOOT_URL}/api/siren/status",
                headers=auth_headers(),
                timeout=3,
            )
            if r.status_code == 401:
                get_token(force_refresh=True)
                time.sleep(1)
                continue

            current_state = bool(r.json().get("active", False))
            if current_state != last_state:
                if current_state:
                    activate_siren()
                else:
                    deactivate_siren()
                last_state = current_state

        except Exception as e:
            print(f"  ❌ Siren sync error: {e}")
            time.sleep(1)
            continue

        time.sleep(1)

# ════════════════════════════════════════════════════════════
# STARTUP CHECKS
# ════════════════════════════════════════════════════════════
def startup_checks():
    print("=" * 60)
    print("🌉 FarmWatch Bridge — full hardware version")
    print("=" * 60)

    try:
        r = requests.get(f"{FLASK_URL}/status", timeout=5)
        print(f"✅ Flask AI:       {r.json()}")
    except Exception as e:
        print(f"⚠️  Flask AI unreachable — start serveur_complet.py first ({e})")

    try:
        requests.get(f"{SPRINGBOOT_URL}/api/sectors", timeout=5)
        print(f"✅ Spring Boot:    {SPRINGBOOT_URL}")
    except Exception as e:
        print(f"⚠️  Spring Boot unreachable ({e})")

    try:
        requests.get(f"http://{ESPCAM_IP}:82/status", timeout=3)
        print(f"✅ ESP32-CAM:      {ESPCAM_IP}")
    except Exception as e:
        print(f"⚠️  ESP32-CAM control server (port 82) unreachable ({e})")

    # JWT
    if get_token() is None:
        print("⚠️  JWT auth failed — bridge will retry continuously.")

    # I2S mic
    dev_id, dev = find_i2s_input_device()
    if dev_id is not None:
        print(f"✅ I2S mic:        [{dev_id}] {dev['name']}")
    else:
        print(f"⚠️  I2S mic not found — sound detection disabled")

    print()

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    startup_checks()
    print("🚀 Starting all loops…  (Ctrl+C to stop)\n")

    threads = [
        threading.Thread(target=sound_loop,      daemon=True),
        threading.Thread(target=camera_loop,     daemon=True),
        threading.Thread(target=siren_sync_loop, daemon=True),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping…")
        deactivate_siren()
        if USE_PI_GPIO:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        print("Bye.")
