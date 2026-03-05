#!/usr/bin/env python3
"""
 Tests for test_money.py
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from decimal import Decimal


# ----------------- Third Party Library -----------------
import pytest

# ----------------- Application Imports -----------------


# ----------------- Module-level Configuration -----------------
from bma_alpha.core.money import parse_money


# --------------------- Begin Tests ---------------------------

@pytest.mark.parametrize("input_val, expected", [
    ("$1,250.00", Decimal("1250.00")),
    ("Free",      Decimal("0.00")),
    (1250,        Decimal("1250.00")),
    ("    Free",  Decimal("0.00")),
    ("$0.99",     Decimal("0.99")),
    ("~800",      Decimal("800.00")),
    (29.99,       Decimal("29.99")),
    (Decimal("5"),Decimal("5.00")),
    (0,           Decimal("0.00")),
    ("0.125",     Decimal("0.13"))
])

def test_parse_money_valid(input_val, expected):
    assert parse_money(input_val) ==  expected

def test_none_raises():
    with pytest.raises(ValueError):
        parse_money(None)

@pytest.mark.parametrize("input_val, exc_type", [
    (None,      ValueError),
    ("",        ValueError),
    ([1, 2, 3], TypeError),
    (-1,        ValueError),
    ("N/A",     ValueError),
    ("12.3.4",  ValueError),
    ("$-10",    ValueError),
    ({},        TypeError),
])

def test_parse_money_invalid(input_val, exc_type):
    with pytest.raises(exc_type):
        parse_money(input_val)