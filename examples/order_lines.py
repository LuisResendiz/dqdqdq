"""Messy purchase-order lines: currency and unit normalization with review flags.

uv run python examples/order_lines.py
"""

from typing import Annotated

import pandas as pd
from dotenv import load_dotenv

from okayish import Fuzzy, FuzzyModel, JevBackend
from okayish.contrib.currencies import Currency
from okayish.contrib.units import Unit

load_dotenv()


class OrderLine(FuzzyModel):
    currency: Annotated[Currency, Fuzzy(source="currency")]
    unit: Annotated[Unit, Fuzzy(source="unit")]


lines = pd.DataFrame(
    {
        "currency": ["US dollars", "pesos mx", "$", "Dólar estadounidense", "moneda de la reina", "Yuan"],
        "unit": ["pcs", "5 piezas", "kilogramz", "docena", "cajas de 12", "botellas de medio litro"],
    }
)
out = OrderLine.parse_frame(lines, columns=["currency", "unit"], backend=JevBackend())
print(out.round(2).to_string())
