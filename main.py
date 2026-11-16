
import csv
import os
import time
import json
import queue
import threading

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np


# ================= SETTINGS =================

CAMERA_INDEX = 1
SAMPLE_RADIUS = 5

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

SAVE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "colors.csv"
)

BLACK_V_MAX = 50
GREY_S_MAX = 40
WHITE_V_MIN = 200

FONT = cv2.FONT_HERSHEY_SIMPLEX

# Queue for transferring colors to Figma
color_queue = queue.Queue()


# ================= COLOR DETECTION =================

def get_color_name(h, s, v):

    if v < BLACK_V_MAX:
        return "BLACK"

    if s < GREY_S_MAX:
        return "WHITE" if v >= WHITE_V_MIN else "GREY"

    if h < 5 or h >= 170:
        return "PINK" if (s < 130 and v >= 150) else "RED"

    if h < 22:
        return "BROWN" if v < 200 else "ORANGE"

    if h < 33:
        return "YELLOW"

    if h < 78:
        return "GREEN"

    if h < 95:
        return "CYAN"

    if h < 131:
        return "BLUE"

    return "PINK" if (h >= 155 and v >= 150) else "PURPLE"


# ================= CSV =================

def save_reading(name, r, g, b, h, s, v):

    new_file = not os.path.exists(SAVE_FILE)

    with open(SAVE_FILE, "a", newline="") as f:

        writer = csv.writer(f)

        if new_file:
            writer.writerow([
                "time", "color", "R", "G", "B",
                "hex", "H", "S", "V"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            r, g, b,
            f"#{r:02X}{g:02X}{b:02X}",
            h, s, v
        ])


# ================= LOCAL SERVER =================

class FigmaHandler(BaseHTTPRequestHandler):

    def send_json(self, data):

        response = json.dumps(data).encode("utf-8")

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(response)

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    def do_GET(self):

        # Root endpoint
        if self.path == "/" or self.path == "/health":

            self.send_json({
                "status": "connected",
                "message": "OpenCV Color Detection Server is running"
            })

            return

        # Get next color from queue
        if self.path == "/next":

            try:

                color = color_queue.get_nowait()

                self.send_json({
                    "available": True,
                    "color": color
                })

            except queue.Empty:

                self.send_json({
                    "available": False
                })

            return

        self.send_error(404)

    def log_message(self, format, *args):
        pass


# ================= START SERVER =================

def start_server():

    server = ThreadingHTTPServer(
        (SERVER_HOST, SERVER_PORT),
        FigmaHandler
    )

    print(
        f"Figma server running at "
        f"http://{SERVER_HOST}:{SERVER_PORT}"
    )

    server.serve_forever()


server_thread = threading.Thread(
    target=start_server,
    daemon=True
)

server_thread.start()

time.sleep(0.5)


# ================= CAMERA =================

cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_AVFOUNDATION
)

if not cap.isOpened():

    print("Camera could not be opened!")

    raise SystemExit(1)


cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

saved_until = 0


# ================= MAIN LOOP =================

while True:

    ok, frame = cap.read()

    if not ok:

        print("Cannot read from camera.")

        break

    height, width, _ = frame.shape

    cx = width // 2
    cy = height // 2

    # Sample average color
    n = SAMPLE_RADIUS

    patch = frame[
        max(0, cy - n):min(height, cy + n + 1),
        max(0, cx - n):min(width, cx + n + 1)
    ]

    mean_bgr = patch.reshape(-1, 3).mean(axis=0)

    b, g, r = (
        int(x) for x in mean_bgr
    )

    # Convert to HSV
    hsv = cv2.cvtColor(
        np.uint8([[[b, g, r]]]),
        cv2.COLOR_BGR2HSV
    )[0, 0]

    h, s, v = (
        int(x) for x in hsv
    )

    # Detect color
    name = get_color_name(h, s, v)

    hex_color = f"#{r:02X}{g:02X}{b:02X}"

    # Text contrast
    brightness = (
        0.114 * b +
        0.587 * g +
        0.299 * r
    )

    text_color = (
        (0, 0, 0)
        if brightness > 140
        else (255, 255, 255)
    )

    hint = (
        "Saved to Figma + CSV"
        if time.time() < saved_until
        else "S = SAVE TO FIGMA    ESC = QUIT"
    )

    # Color panel
    cv2.rectangle(
        frame,
        (10, 10),
        (400, 170),
        (b, g, r),
        -1
    )

    cv2.rectangle(
        frame,
        (10, 10),
        (400, 170),
        (128, 128, 128),
        2
    )

    cv2.putText(
        frame,
        name,
        (25, 70),
        FONT,
        2,
        text_color,
        4
    )

    cv2.putText(
        frame,
        f"RGB: {r}, {g}, {b}",
        (25, 105),
        FONT,
        0.6,
        text_color,
        2
    )

    cv2.putText(
        frame,
        f"HEX: {hex_color}",
        (25, 130),
        FONT,
        0.6,
        text_color,
        2
    )

    cv2.putText(
        frame,
        f"HSV: {h}, {s}, {v}",
        (25, 155),
        FONT,
        0.6,
        text_color,
        2
    )

    # Center marker
    cv2.circle(
        frame,
        (cx, cy),
        8,
        (255, 255, 255),
        2
    )

    cv2.circle(
        frame,
        (cx, cy),
        6,
        (0, 0, 0),
        2
    )

    # Save hint
    cv2.putText(
        frame,
        hint,
        (10, height - 20),
        FONT,
        0.55,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "OpenCV Color Detection",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    # ================= SAVE TO FIGMA =================

    if key == ord("s"):

        color_data = {
            "name": name,
            "r": r,
            "g": g,
            "b": b,
            "hex": hex_color,
            "h": h,
            "s": s,
            "v": v,
            "time": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        # Save CSV
        save_reading(
            name, r, g, b, h, s, v
        )

        # Send to Figma queue
        color_queue.put(color_data)

        print(
            f"[SAVED] {name} | "
            f"{hex_color} | RGB({r}, {g}, {b})"
        )

        saved_until = time.time() + 1.5

    elif key == 27 or key == ord("q"):

        break


# ================= CLEANUP =================

cap.release()

cv2.destroyAllWindows()

print("Color Detection stopped.")
