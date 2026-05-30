from __future__ import annotations


def _parse_expression(expr: str) -> tuple[int, str, int, str, int]:
    if len(expr) != 5:
        raise ValueError(f"Expression length must be 5, got {len(expr)}")

    c1, op1, c2, op2, c3 = expr[0], expr[1], expr[2], expr[3], expr[4]
    if not (c1.isdigit() and c2.isdigit() and c3.isdigit()):
        raise ValueError(f"Expression digits are invalid: {expr}")
    if op1 not in "+-*" or op2 not in "+-*":
        raise ValueError(f"Expression operators are invalid: {expr}")

    return int(c1), op1, int(c2), op2, int(c3)


def evaluate_expression(expr: str) -> int:
    n1, op1, n2, op2, n3 = _parse_expression(expr)

    if op1 == "*":
        left = n1 * n2
        if op2 == "+":
            return left + n3
        if op2 == "-":
            return left - n3
        return left * n3

    if op2 == "*":
        right = n2 * n3
        if op1 == "+":
            return n1 + right
        return n1 - right

    if op1 == "+":
        left = n1 + n2
    else:
        left = n1 - n2

    if op2 == "+":
        return left + n3
    return left - n3
