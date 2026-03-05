#!/usr/bin/env python3
"""
money parser
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ----------------- Third Party Library -----------------


# ----------------- Application Imports -----------------


# ----------------- Module-level Configuration -----------------

_STRIP_RE = re.compile(r"[$,~\s]")

def parse_money(value: object) -> Decimal:

    if value is None:
        raise ValueError("value must not be None")
    if isinstance(value, (Decimal, int, float)):
        d = Decimal(str(value))
        if d < 0:
            raise ValueError(f"Negative values are not allowed: {value}")
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
   
    if not isinstance(value, str):
        raise TypeError(f"unsupported type: {type(value).__name__}")
    
    cleaned = _STRIP_RE.sub("", value)

    if value.strip().lower().startswith("free"):
        return Decimal("0.00")
    
    if cleaned == "" or cleaned.lower() in ("n/a",):
        raise ValueError(f"non-numeric value: {value!r}")
    
    if cleaned.count(".") > 1:
        raise ValueError(f"multiple decimals in value: {value!r}")
    
    try:
        d = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Cannot parse as money: {value!r}")
    
    if d < 0:
        raise ValueError(f"Negative values are not allowed: {value}")
    
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
