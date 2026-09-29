"""Backend for TypeSafe's Jev decision model.

The public docs disagree on the base URL (api.typesafe.ai vs thejevai.com), so the
endpoint is configurable. The request/response shape follows the published
``systemone`` "choice" question type. Verify against your own early-access docs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

import httpx
from dotenv import load_dotenv

from .base import Decision, ScoreDecision

DEFAULT_URL = "https://api.typesafe.ai/v1/systemone"
MAX_CHOICES = 255


class JevBackend:
    def __init__(
        self,
        api_key: str | None = None,
        url: str = DEFAULT_URL,
        model: str = "jev-latest",
        timeout: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
        if not self.api_key and client is None:
            raise ValueError("Set TYPESAFE_API_KEY (or JEV_API_KEY) or pass api_key=")
        self.url = url
        self.model = model
        self._client = client or httpx.Client(timeout=timeout)

    def choose(self, text: str, choices: Mapping[str, str], instructions: str = "") -> Decision:
        if len(choices) > MAX_CHOICES:
            raise ValueError(f"Jev supports at most {MAX_CHOICES} choices, got {len(choices)}")
        body = {
            "model": self.model,
            "state": text,
            "questions": {
                "q": {"type": "choice", "instructions": instructions, "criteria": dict(choices)}
            },
        }
        return _parse(self._post(body), choices)

    def score(self, text: str, levels: Sequence[str], instructions: str = "") -> ScoreDecision:
        if not 2 <= len(levels) <= 10:
            raise ValueError(f"Jev scores need 2-10 levels, got {len(levels)}")
        body = {
            "model": self.model,
            "state": text,
            "questions": {
                "q": {"type": "score", "instructions": instructions, "criteria": list(levels)}
            },
        }
        a = self._post(body)["answers"]["q"]
        probs = {int(k): float(v) for k, v in a.get("probabilities", {}).items()}
        expected = sum(k * v for k, v in probs.items()) / (sum(probs.values()) or 1.0)
        return ScoreDecision(int(a["score"]), expected, float(a["confidence"]), probs or None)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = self._client.post(self.url, json=body, headers=headers)
        resp.raise_for_status()
        out: dict[str, Any] = resp.json()
        return out


def _parse(payload: dict[str, Any], choices: Mapping[str, str]) -> Decision:
    answer = payload["answers"]["q"]
    choice = answer["choice"]
    if choice not in choices:
        raise ValueError(f"Backend returned unknown choice {choice!r}")
    return Decision(
        choice=choice,
        confidence=float(answer["confidence"]),
        probabilities=answer.get("probabilities"),
    )
