"""Second example: support-ticket triage. Free text -> severity and department, with review flags.

uv run python examples/ticket_triage.py            # uses Jev if TYPESAFE_API_KEY is set
"""

import pandas as pd
from dotenv import load_dotenv

from dqdqdq import ChoiceField, JevBackend, classify_frame

load_dotenv()

SEVERITY = ChoiceField(
    choices={
        "low": "Cosmetic issue or question, no impact on work",
        "medium": "Feature degraded, workaround exists",
        "high": "Service down or data loss, many users affected",
    },
    instructions="How severe is this support ticket?",
)
DEPARTMENT = ChoiceField(
    choices={
        "billing": "Payments, invoices, refunds, pricing",
        "technical": "Bugs, outages, errors, performance",
        "account": "Login, permissions, profile, cancellations",
    },
    instructions="Which team should handle this support ticket?",
)

tickets = pd.DataFrame(
    {
        "text": [
            "Site is down for all EU customers since 09:00",
            "I was charged twice for my March invoice",
            "The logo looks blurry on the settings page",
            "cant log in after password reset, tried 3 times",
            "low",
            "Exports crash randomly but re-running works",
        ]
    }
)

try:
    backend = JevBackend()
except ValueError:
    backend = None
    print("No key found: only exact labels resolve.\n")

out = classify_frame(tickets, "text", SEVERITY, "severity", backend)
out = classify_frame(out, "text", DEPARTMENT, "department", backend)
out["text"] = out["text"].str.slice(0, 40)
print(out.round(2).to_string())
