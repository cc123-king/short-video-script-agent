"""Local, deterministic material search. No retrieval paths selected by the model."""
import copy
import re

from .domain import ValidationError, digest, read_json


def terms(value):
    value = value.lower()
    result = set(re.findall(r"[a-z0-9]+", value))
    for chunk in re.findall(r"[\u4e00-\u9fff]+", value):
        result.add(chunk)
        result.update(chunk[i:i + 2] for i in range(len(chunk) - 1))
    return result


class Knowledge:
    def __init__(self, catalog, brand, duration):
        self.catalog = read_json(catalog)
        self.brand = read_json(brand)
        self.duration = read_json(duration)
        self.fingerprint = digest({"catalog": self.catalog, "brand": self.brand, "duration": self.duration})
        self.materials = self.catalog["materials"]
        material_ids, fact_ids = set(), set()
        for material in self.materials:
            if material["id"] in material_ids:
                raise ValidationError("资料中存在重复素材 ID")
            material_ids.add(material["id"])
            for fact in material["facts"]:
                if fact["id"] in fact_ids:
                    raise ValidationError("资料中存在重复事实 ID")
                fact_ids.add(fact["id"])
        for key in ("speech_units_per_second", "speech_safety_factor", "subtitle_units_per_second"):
            value = self.duration[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 30:
                raise ValidationError(f"时长配置错误: {key}")

    def search(self, query, product_id):
        query_terms = terms(query)
        ranked = []
        for material in self.materials:
            if material["product_id"] != product_id:
                continue
            searchable = " ".join([material["name"], *material["keywords"], *(f["text"] for f in material["facts"])])
            overlap = query_terms & terms(searchable)
            score = len(overlap)
            if score:
                ranked.append((score, material["id"], material, sorted(overlap)))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [{**copy.deepcopy(item[2]), "search_score": item[0], "matched_terms": item[3]} for item in ranked[:5]]
