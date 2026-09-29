"""Third example: rate your own CV against several roles.

uv run python examples/rate_my_cv.py [cv.txt]

Self-assessment tool, not a hiring filter: it has not been validated for screening candidates,
and it should not be used to accept or reject people.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from dqdqdq import JevBackend

load_dotenv()

LEVELS = [
    "No relevant experience for this role",
    "Some transferable skills, major gaps",
    "Partial fit: meets some core requirements",
    "Good fit: meets most core requirements",
    "Strong fit: meets core requirements and shows depth or impact",
]
ROLES = {
    "Data engineer": "Builds and operates data pipelines, warehouses and data-quality checks.",
    "Data analyst": "Answers business questions with SQL, dashboards and clear communication.",
    "ML engineer": "Trains, deploys and monitors machine learning models in production.",
    "Product manager": "Owns product strategy, prioritization and cross-functional delivery.",
    "Frontend developer": "Builds accessible, performant web interfaces in modern JavaScript frameworks.",
}

cv = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("sample_cv.txt")).read_text()
backend = JevBackend()


def rate(role: str):
    instructions = f"How well does this CV fit the role '{role}'? {ROLES[role]} Judge only skills and experience."
    return role, backend.score(cv, LEVELS, instructions)


with ThreadPoolExecutor() as pool:
    results = sorted(pool.map(rate, ROLES), key=lambda r: -r[1].expected)

top = len(LEVELS) - 1
print(f"{'Role':<20}{'Score':>7}{'Level':>7}{'Conf':>7}  Review")
for role, r in results:
    print(f"{role:<20}{r.expected / top * 100:>6.0f}%{r.score:>5}/{top}{r.confidence:>7.2f}  "
          f"{'yes' if r.confidence < 0.7 else ''}")
