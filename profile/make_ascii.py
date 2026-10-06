"""One-off: converts profile/gnx.jpg into ascii_dark.txt / ascii_light.txt (full-frame, 16:9)."""
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
COLS, ROWS = 200, 60
RAMP = " .'`,:;-~=+*xoa%#&8WM@"  # sparse -> dense


def convert(dense_is_bright):
    g = cv2.imread(str(HERE / "gnx.jpg"), cv2.IMREAD_GRAYSCALE)
    g = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 4)).apply(g)
    g = cv2.resize(g, (COLS, ROWS), interpolation=cv2.INTER_AREA).astype(float) / 255
    v = g if dense_is_bright else 1 - g
    v = np.clip((v - 0.08) / 0.84, 0, 1) ** 1.3 * (0.72 if dense_is_bright else 1.0)
    return "\n".join("".join(RAMP[min(len(RAMP) - 1, int(p * len(RAMP)))] for p in row).rstrip() or " " for row in v)


(HERE / "ascii_dark.txt").write_text(convert(True), encoding="utf-8")
(HERE / "ascii_light.txt").write_text(convert(False), encoding="utf-8")
print("ok")
