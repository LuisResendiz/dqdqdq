import httpx

from fuzzschema import JevBackend, resolve_country


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
