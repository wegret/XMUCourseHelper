from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from .infer import decode_five_symbols, load_image_array
from .safe_eval import evaluate_expression
from .splitter import cut_first_five_symbols


def recognize_expression(image: str | Path | np.ndarray) -> Tuple[str, list[float]]:
    arr = load_image_array(image)
    symbol_images = cut_first_five_symbols(arr)
    expr, confidences = decode_five_symbols(symbol_images)
    if len(expr) != 5:
        raise ValueError(f"Expression length must be 5, got {len(expr)}")
    return expr, confidences


def solve_captcha(image: str | Path | np.ndarray) -> int:
    expr, _ = recognize_expression(image)
    return evaluate_expression(expr)


def solve_captcha_with_detail(image: str | Path | np.ndarray) -> Dict[str, Any]:
    expr, confidences = recognize_expression(image)
    result = evaluate_expression(expr)
    return {
        "expression": expr,
        "result": result,
        "confidences": confidences,
        "mean_confidence": float(sum(confidences) / len(confidences)),
    }
