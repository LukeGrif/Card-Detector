"""
ESP32-S3 AI Camera  →  OpenAI Vision  (MicroPython)

FIRMWARE REQUIRED:
  Standard MicroPython does NOT include camera support.
  Flash this firmware first (pick the .bin for your board):
  https://github.com/lemariva/micropython-camera-driver/releases

CAMERA PINS:
  Change the values in init_camera() to match your board.
  Common boards:
    - Freenove ESP32-S3-WROOM : see FREENOVE_PINS below
    - XIAO ESP32-S3 Sense      : see XIAO_PINS below
    - AiThinker (original CAM) : different chip, use Arduino instead

FILES NEEDED ON BOARD:
  Upload both main.py and secrets.py to the board using Thonny or ampy.
"""

import network
import urequests
import ujson
import ubinascii
import camera
import time
from secrets import WIFI_SSID, WIFI_PASS, OPENAI_API_KEY

# ── What to ask OpenAI about each image ──────────────────────────────────────
QUESTION = "What do you see in this image? Describe it in one or two sentences."

# ── Image capture settings ────────────────────────────────────────────────────
# Lower resolution = smaller file = less memory needed.
# FRAME_QVGA (320x240) is a good balance of quality vs memory.
FRAME_SIZE  = camera.FRAME_QVGA
JPEG_QUALITY = 10   # 10 = lower quality, smaller file. Range: 10–63

# ── Camera pin configs — uncomment the block for YOUR board ──────────────────

# Freenove ESP32-S3-WROOM
CAMERA_PINS = dict(
    d0=11, d1=9, d2=8, d3=10, d4=12, d5=18, d6=17, d7=16,
    xclk=15, pclk=13, vsync=6, href=7,
    siod=4, sioc=5,
    reset=-1, pwdn=-1,
)

# XIAO ESP32-S3 Sense — uncomment if using this board
# CAMERA_PINS = dict(
#     d0=15, d1=17, d2=18, d3=16, d4=14, d5=12, d6=11, d7=48,
#     xclk=10, pclk=13, vsync=38, href=47,
#     siod=40, sioc=39,
#     reset=-1, pwdn=-1,
# )

# ── WiFi ──────────────────────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi…")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if wlan.isconnected():
        print("WiFi OK —", wlan.ifconfig()[0])
    else:
        raise RuntimeError("WiFi failed — check SSID/password in secrets.py")


# ── Camera ────────────────────────────────────────────────────────────────────

def init_camera():
    result = camera.init(
        0,
        format=camera.JPEG,
        framesize=FRAME_SIZE,
        quality=JPEG_QUALITY,
        xclk_freq=20_000_000,
        **CAMERA_PINS,
    )
    if not result:
        raise RuntimeError("Camera init failed — check CAMERA_PINS for your board")
    print("Camera OK")


def capture_image():
    """Return raw JPEG bytes from the camera."""
    buf = camera.capture()
    if not buf:
        raise RuntimeError("Capture failed")
    print(f"Captured {len(buf)} bytes")
    return buf


# ── OpenAI Vision ─────────────────────────────────────────────────────────────

def ask_openai(jpeg_bytes, question):
    """Send image to OpenAI gpt-4o-mini and return the text answer."""
    b64 = ubinascii.b2a_base64(jpeg_bytes).decode().strip()

    payload = ujson.dumps({
        "model": "gpt-4o-mini",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64," + b64},
                    },
                ],
            }
        ],
    })

    print("Sending to OpenAI…")
    response = urequests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + OPENAI_API_KEY,
            "Content-Type": "application/json",
        },
        data=payload,
    )

    data = response.json()
    response.close()

    if "error" in data:
        raise RuntimeError("OpenAI error: " + data["error"]["message"])

    return data["choices"][0]["message"]["content"]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    connect_wifi()
    init_camera()

    # Discard the first frame — cameras often need one warm-up shot
    camera.capture()
    time.sleep(0.5)

    while True:
        try:
            img = capture_image()
            answer = ask_openai(img, QUESTION)
            print("\nOpenAI says:")
            print(answer)
            print()
        except Exception as e:
            print("Error:", e)

        # Wait before taking the next shot
        time.sleep(10)


main()
