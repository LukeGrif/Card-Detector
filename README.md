# ESP32 IoT Monitor

> University of Limerick · Electronic & Computer Engineering  
> **Luke Griffin** · June 2026

A dual-sensor IoT dashboard hosted on GitHub Pages, combining an IR-based card detector and an ESP32-CAM person detection system into a single web interface.

---

## What it does

| Tab | Hardware | How it works |
|-----|----------|--------------|
| **Card Detector** | ESP32 + IR sensor | ESP32 writes JSON to a GitHub Gist; dashboard polls it every 30s and shows a green/red indicator |
| **Person Detections** | ESP32-CAM | `detect.py` runs YOLOv3 locally, detects people in the camera stream, uploads annotated frames to this repo, dashboard shows the latest capture |

---

## Repository structure

```
├── index.html            # Merged dashboard (Card + Person tabs)
├── docs/
│   └── ul-crest.svg      # UL crest logo
├── detections/
│   └── .gitkeep          # Keeps folder in repo; images uploaded here by detect.py
├── detect.py             # Person detection script (run locally)
├── config.py             # Local secrets — gitignored, never committed
├── config.example.py     # Safe template for config.py
└── .gitignore
```

---

## Setup

### 1. GitHub Pages

1. Create a new **public** repo on GitHub
2. Go to **Settings → Pages** → source: `main` branch, root folder → Save
3. Your dashboard will be live at `https://YOUR_USERNAME.github.io/YOUR_REPO/`

### 2. GitHub Personal Access Token

1. GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Give it a note, an expiry, and tick only the **`repo`** scope
4. Copy it immediately — GitHub shows it only once
5. Paste it into `config.py` on your local machine only

### 3. config.py (local only — never commit this)

```python
GITHUB_TOKEN  = "ghp_yourtoken..."
GITHUB_USER   = "your-github-username"
GITHUB_REPO   = "your-repo-name"
CAMERA_URL    = "http://192.168.x.x/cam.jpg"
```

### 4. Update index.html

Find the script block at the bottom of `index.html` and set:

```js
const GITHUB_USER  = 'your-github-username';
const GITHUB_REPO  = 'your-repo-name';
```

### 5. Install Python dependencies

```bash
pip install requests opencv-python numpy
```

---

## Running person detection

```bash
python detect.py
```

- Streams frames from the ESP32-CAM over your local network
- Runs YOLOv3 detection on each frame
- When a person is detected, waits for the cooldown (default **5 seconds**) before saving
- Uploads the annotated JPEG to `detections/person_YYYY-MM-DD_HH-MM-SS.jpg`
- The dashboard picks it up on its next 30-second refresh

Press **Q** in the OpenCV window to stop.

### Key settings in detect.py

| Setting | Default | Description |
|---------|---------|-------------|
| `COOLDOWN_SECS` | `5` | Min seconds between saves after a detection |
| `IMAGES_FOLDER` | `detections` | Folder in the repo where images are stored |
| `CAMERA_URL` | `http://...` | ESP32-CAM stream URL on your local network |

---

## Dashboard

### Card Detector tab

- Polls a GitHub Gist URL (configured via the on-page panel) every 30 seconds
- Displays a colour-coded ring — green for card present, red for absent
- Shows last updated time, device name, and raw sensor value
- Gist URL is saved to `localStorage` so it persists between visits

Expected Gist JSON:
```json
{"card_present": true, "timestamp": "2026-06-02T14:30:00", "device": "ESP32"}
```

### Person Detections tab

- Fetches the `detections/` folder listing via the GitHub Contents API
- Sorts by filename (newest first) and displays only the most recent capture
- All images are kept in the repo; only the latest is shown
- Refreshes every 30 seconds; image URL is cache-busted to always show the freshest version

---

## Security

- `config.py` is listed in `.gitignore` and must never be committed — it contains your token
- If you accidentally expose a token, revoke it immediately in GitHub → Developer settings
- GitHub automatically scans public repos for exposed tokens and may auto-revoke them
- The token only needs the `repo` scope — do not grant broader permissions
- `config.example.py` is the safe, committed template others can use to set up their own config

---

## Troubleshooting

**404 errors on images**  
Raw GitHub content can take a few minutes to propagate after first push. Wait 1–2 minutes and refresh.

**detect.py not uploading**  
Check that `GITHUB_TOKEN` is valid and has `repo` scope. Ensure the `detections/` folder exists in the repo. Check terminal output for the HTTP status code.

**Card Detector showing "Error"**  
Confirm the raw Gist URL is correct and the Gist is **public** (not secret). Test by pasting the URL into a browser — it should return plain JSON.

**Screen flickering during detection**  
YOLOv3 is CPU/GPU-intensive. Check temperatures with HWMonitor, ensure the laptop is plugged in, and keep vents clear.

---

## Tech stack

- **Hardware:** ESP32, ESP32-CAM
- **Detection:** YOLOv3 via OpenCV (`cv2.dnn`)
- **Backend:** Python (`detect.py`) + GitHub Contents API
- **Frontend:** Vanilla HTML/CSS/JS hosted on GitHub Pages
- **Data sources:** GitHub Gist (card status), GitHub repo contents API (detection images)