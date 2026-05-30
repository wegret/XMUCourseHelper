from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass
class PreprocessConfig:
    image_size: int = 28
    threshold_method: str = "otsu"
    fixed_threshold: int = 127
    invert_foreground: bool = True
    center_margin_ratio: float = 0.12


def ensure_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.uint8)
    if image.ndim == 3 and image.shape[2] in (3, 4):
        pil_img = Image.fromarray(image[..., :3].astype(np.uint8))
        return np.array(pil_img.convert("L"), dtype=np.uint8)
    raise ValueError(f"Unsupported image shape: {image.shape}")


def otsu_threshold(gray: np.ndarray) -> int:
    hist = np.bincount(gray.flatten(), minlength=256).astype(np.float64)
    total = gray.size
    sum_total = np.dot(np.arange(256), hist)
    sum_b = 0.0
    w_b = 0.0
    max_var = -1.0
    threshold = 127

    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = t
    return threshold


def binarize(gray: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    if cfg.threshold_method.lower() == "otsu":
        threshold = otsu_threshold(gray)
    else:
        threshold = int(cfg.fixed_threshold)

    binary = np.where(gray > threshold, 255, 0).astype(np.uint8)

    if cfg.invert_foreground:
        white_ratio = float((binary > 0).mean())
        if white_ratio > 0.5:
            binary = (255 - binary).astype(np.uint8)

    return binary


def crop_and_center(binary: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    ys, xs = np.where(binary > 0)
    target = cfg.image_size
    canvas = np.zeros((target, target), dtype=np.uint8)

    if len(xs) == 0:
        return canvas

    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    width = x1 - x0 + 1
    height = y1 - y0 + 1
    roi = binary[y0 : y0 + height, x0 : x0 + width]

    margin = max(1, int(target * cfg.center_margin_ratio))
    max_dim = max(height, width)
    if max_dim <= 0:
        return canvas

    scale = min((target - 2 * margin) / max_dim, 1.0)
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))

    resized = np.array(
        Image.fromarray(roi, mode="L").resize((new_w, new_h), resample=Image.Resampling.NEAREST),
        dtype=np.uint8,
    )
    start_x = (target - new_w) // 2
    start_y = (target - new_h) // 2
    canvas[start_y : start_y + new_h, start_x : start_x + new_w] = resized
    return canvas


def preprocess_to_array(image: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    gray = ensure_gray(image)
    binary = binarize(gray, cfg)
    centered = crop_and_center(binary, cfg)
    normalized = centered.astype(np.float32) / 255.0
    return np.expand_dims(np.expand_dims(normalized, 0), 0).astype(np.float32)
