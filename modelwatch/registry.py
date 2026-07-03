import yaml


def _norm(s: str) -> str:
    return s.strip().lower()


class Registry:
    def __init__(self, models: list[dict]):
        self.models = models
        # lookup[(source_id, normalized_alias)] -> canonical id; source_id "*" = any source
        self._lookup: dict[tuple[str, str], str] = {}
        for m in models:
            for source_id, names in (m.get("aliases") or {}).items():
                for n in names:
                    self._lookup[(source_id, _norm(n))] = m["id"]
            self._lookup[("*", _norm(m["id"]))] = m["id"]
            self._lookup[("*", _norm(m["name"]))] = m["id"]

    def canonical_id(self, source_id: str, raw_name: str) -> str | None:
        key = _norm(raw_name)
        return self._lookup.get((source_id, key)) or self._lookup.get(("*", key))


def load_registry(path: str) -> Registry:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return Registry(doc["models"])
