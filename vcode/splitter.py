from __future__ import annotations

from typing import List

import numpy as np


# Must be identical to cut/cut_symbols.py.
X_BOUNDS = [0, 20, 33, 52, 62, 82]


def cut_first_five_symbols(image: np.ndarray) -> List[np.ndarray]:
    if image.ndim not in (2, 3):
        raise ValueError(f"Unsupported image ndim: {image.ndim}")

    symbols: List[np.ndarray] = []
    height = image.shape[0]
    for left, right in zip(X_BOUNDS[:-1], X_BOUNDS[1:]):
        symbols.append(image[0:height, left:right].copy())

    if len(symbols) != 5:
        raise RuntimeError(f"Expected 5 symbols, got {len(symbols)}")

    return symbols
