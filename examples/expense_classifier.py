"""Expense classifier: a receipt and a bank transaction in, category + reconciliation flags out.

uv run python examples/expense_classifier.py
"""

from enum import Enum
from typing import Annotated

import pandas as pd
from dotenv import load_dotenv

from dqdqdq import Fuzzy, FuzzyModel, JevBackend

load_dotenv()


class Category(str, Enum):
    meals = "meals"
    travel = "travel"
    software = "software"
    office = "office"
    other = "other"


class Expense(FuzzyModel):
    category: Annotated[
        Category,
        Fuzzy(
            "Which expense category does this purchase belong to?",
            descriptions={
                "meals": "Restaurants, coffee, catering",
                "travel": "Flights, hotels, taxis, fuel",
                "software": "Subscriptions, SaaS, cloud services",
                "office": "Supplies, furniture, equipment",
                "other": "Anything else",
            },
        ),
    ]
    is_business: Annotated[bool, Fuzzy("This looks like a business expense, not personal")]
    same_purchase: Annotated[
        bool, Fuzzy("The receipt and the bank transaction describe the same purchase")
    ]


expenses = pd.DataFrame(
    {
        "receipt": [
            "Blue Bottle Coffee, 2x latte + croissant, $14.50, 2026-09-03",
            "Delta Air Lines e-ticket SFO-JFK, $412.10, 2026-09-10",
            "Notion Labs invoice, Team plan 5 seats, $50.00",
            "Whole Foods, groceries, $86.20, 2026-09-12",
        ],
        "transaction": [
            "SQ *BLUE BOTTLE 4482 SAN FRANCISCO CA  -14.50",
            "DELTA 0062345678 ATLANTA GA  -412.10",
            "SHELL OIL 57444 OAKLAND CA  -50.00",
            "WHOLEFDS MKT 10352 -86.20",
        ],
    }
)
out = Expense.parse_frame(
    expenses, columns=["receipt", "transaction"], backend=JevBackend()
)
out["receipt"] = out["receipt"].str.slice(0, 28)
print(out.drop(columns="transaction").round(2).to_string())
