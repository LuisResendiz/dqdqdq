import httpx

from dqdqdq import JevBackend, resolve_country


def test_jev_request_and_parse() -> None:
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(
            200,
            json={"answers": {"q": {"type": "choice", "choice": "JP", "confidence": 0.91,
                                     "probabilities": {"JP": 0.91}}}},
        )

    backend = JevBackend(api_key="k", client=httpx.Client(transport=httpx.MockTransport(handler)))
    m = resolve_country("land of the rising sun", backend=backend)
    assert m.alpha_3 == "JPN" and m.confidence == 0.91
    assert seen["auth"] == "Bearer k"
    q = seen["body"]["questions"]["q"]
    assert q["type"] == "choice" and len(q["criteria"]) <= 255


def test_jev_score() -> None:
    import json

    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["q"] = json.loads(req.content)["questions"]["q"]
        return httpx.Response(200, json={"answers": {"q": {
            "type": "score", "score": 3, "confidence": 0.8,
            "probabilities": {"2": 0.2, "3": 0.6, "4": 0.2}}}})

    b = JevBackend(api_key="k", client=httpx.Client(transport=httpx.MockTransport(handler)))
    d = b.score("cv", ["a", "b", "c", "d", "e"], "fit?")
    assert seen["q"]["type"] == "score" and seen["q"]["criteria"] == ["a", "b", "c", "d", "e"]
    assert d.score == 3 and abs(d.expected - 3.0) < 1e-9 and d.confidence == 0.8
