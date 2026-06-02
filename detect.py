import cv2
import numpy as np
import urllib.request
import time
import base64
import json
import requests
from datetime import datetime
from config import GITHUB_TOKEN, GITHUB_USER, GITHUB_REPO, CAMERA_URL

# ─────────────────────────────────────────────
#  CONFIG — fill these in
# ─────────────────────────────────────────────
IMAGES_FOLDER = "detections"                   # folder inside repo
COOLDOWN_SECS = 5                              # min seconds between saves
# ─────────────────────────────────────────────

YOLO_WEIGHTS = r"./YOLO/yolov3.weights"
YOLO_CFG     = r"./YOLO/yolov3.cfg"
YOLO_NAMES   = r"./YOLO/coco.names"

# ── Load YOLO ────────────────────────────────
net = cv2.dnn.readNet(YOLO_WEIGHTS, YOLO_CFG)
with open(YOLO_NAMES, "r") as f:
    classes = [line.strip() for line in f.readlines()]

layer_names = net.getLayerNames()
out_layers_raw = net.getUnconnectedOutLayers()
if isinstance(out_layers_raw[0], (list, np.ndarray)):
    output_layers = [layer_names[i[0] - 1] for i in out_layers_raw]
else:
    output_layers = [layer_names[i - 1] for i in out_layers_raw]

colors = np.random.uniform(0, 255, size=(len(classes), 3))

# ── GitHub helpers ────────────────────────────
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

def upload_image_to_github(img_bytes: bytes, filename: str) -> bool:
    """Upload a JPEG to the detections/ folder in the repo."""
    path    = f"{IMAGES_FOLDER}/{filename}"
    api_url = f"{GITHUB_API}/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    b64     = base64.b64encode(img_bytes).decode()

    # Check if file already exists (need SHA to overwrite)
    sha = None
    r = requests.get(api_url, headers=HEADERS)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload = {"message": f"Add detection {filename}", "content": b64}
    if sha:
        payload["sha"] = sha

    r = requests.put(api_url, headers=HEADERS, data=json.dumps(payload))
    if r.status_code in (200, 201):
        raw_url = (f"https://raw.githubusercontent.com/{GITHUB_USER}/"
                   f"{GITHUB_REPO}/main/{path}")
        print(f"  ✓ Uploaded → {raw_url}")
        return True
    else:
        print(f"  ✗ Upload failed ({r.status_code}): {r.text[:200]}")
        return False


# ── YOLO detection ────────────────────────────
def detect_objects(frame):
    h, w, _ = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []
    person_detected = False

    for output in layer_outputs:
        for detection in output:
            scores    = detection[5:]
            class_id  = int(np.argmax(scores))
            confidence = float(scores[class_id])
            if confidence > 0.3:
                cx = int(detection[0] * w)
                cy = int(detection[1] * h)
                bw = int(detection[2] * w)
                bh = int(detection[3] * h)
                boxes.append([cx - bw//2, cy - bh//2, bw, bh])
                confidences.append(confidence)
                class_ids.append(class_id)
                if classes[class_id] == "person":
                    person_detected = True

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.3, 0.4)
    if len(indexes) > 0:
        if isinstance(indexes, np.ndarray):
            indexes = indexes.flatten()
        for i in indexes:
            x, y, bw, bh = boxes[i]
            label  = classes[class_ids[i]]
            conf   = confidences[i]
            color  = colors[class_ids[i]]
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return frame, person_detected


# ── Main loop ─────────────────────────────────
def main():
    print("ESP32-CAM Person Detector starting…")
    print(f"  Cooldown : {COOLDOWN_SECS}s between saves")
    print(f"  Repo     : github.com/{GITHUB_USER}/{GITHUB_REPO}")
    print(f"  Gallery  : https://{GITHUB_USER}.github.io/{GITHUB_REPO}/detections.html\n")

    last_save_time = 0
    cv2.namedWindow("Object Detection", cv2.WINDOW_AUTOSIZE)

    while True:
        try:
            img_resp = urllib.request.urlopen(CAMERA_URL, timeout=5)
            imgnp   = np.array(bytearray(img_resp.read()), dtype=np.uint8)
            frame   = cv2.imdecode(imgnp, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            frame, person_detected = detect_objects(frame)
            now = time.time()

            if person_detected and (now - last_save_time) >= COOLDOWN_SECS:
                last_save_time = now
                ts       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"person_{ts}.jpg"
                print(f"[{ts}] Person detected — uploading…")
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    upload_image_to_github(buf.tobytes(), filename)

            cv2.imshow("Object Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()