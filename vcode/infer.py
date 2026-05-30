from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

import numpy as np
import onnxruntime
from PIL import Image

from .preprocess import PreprocessConfig, preprocess_to_array

OPERATOR_ID2SYMBOL = {0: "+", 1: "-", 2: "*"}
MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
DIGIT_ONNX_PATH = MODEL_DIR / "digit_model.onnx"
OPERATOR_ONNX_PATH = MODEL_DIR / "operator_model.onnx"
DIGIT_META_PATH = MODEL_DIR / "digit_model.meta.json"
OPERATOR_META_PATH = MODEL_DIR / "operator_model.meta.json"


def load_image_array(image: str | Path | np.ndarray) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image
    with Image.open(str(image)) as img:
        return np.array(img)


@lru_cache(maxsize=4)
def load_session(onnx_path: str) -> onnxruntime.InferenceSession:
    return onnxruntime.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])


def load_meta(meta_path: Path) -> dict:
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def _softmax(logits: np.ndarray) -> np.ndarray:
    max_logits = np.max(logits, axis=1, keepdims=True)
    exp_logits = np.exp(logits - max_logits)
    return exp_logits / np.sum(exp_logits, axis=1, keepdims=True)


def classify_symbol(image: np.ndarray, onnx_path: Path, meta_path: Path) -> Tuple[int, float]:
    session = load_session(str(onnx_path))
    meta = load_meta(meta_path)

    cfg = PreprocessConfig(
        image_size=int(meta.get("image_size", 28)),
        threshold_method=str(meta.get("threshold_method", "otsu")),
    )
    x = preprocess_to_array(image, cfg)
    input_name = session.get_inputs()[0].name
    logits = session.run(None, {input_name: x})[0]
    probs = _softmax(logits)
    pred = int(np.argmax(probs, axis=1)[0])
    confidence = float(probs[0, pred])
    return pred, confidence


def predict_digit(image: np.ndarray) -> Tuple[int, float]:
    return classify_symbol(image, DIGIT_ONNX_PATH, DIGIT_META_PATH)


def predict_operator(image: np.ndarray) -> Tuple[str, float]:
    idx, confidence = classify_symbol(image, OPERATOR_ONNX_PATH, OPERATOR_META_PATH)
    if idx not in OPERATOR_ID2SYMBOL:
        raise ValueError(f"Invalid operator class index: {idx}")
    return OPERATOR_ID2SYMBOL[idx], confidence


def decode_five_symbols(symbol_images: List[np.ndarray]) -> Tuple[str, List[float]]:
    if len(symbol_images) != 5:
        raise ValueError(f"Expected 5 symbols, got {len(symbol_images)}")

    chars: List[str] = []
    confidences: List[float] = []
    for idx, symbol in enumerate(symbol_images, start=1):
        if idx in (1, 3, 5):
            digit, confidence = predict_digit(symbol)
            chars.append(str(digit))
            confidences.append(confidence)
        else:
            op, confidence = predict_operator(symbol)
            chars.append(op)
            confidences.append(confidence)

    expr = "".join(chars)
    return expr, confidences
