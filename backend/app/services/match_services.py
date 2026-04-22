import re
from typing import Dict, Any, List

def _norm(s: str) -> str:
    return (s or "").lower()

def _contains_phrase(text: str, phrase: str) -> bool:
    return _norm(phrase) in _norm(text)

def _near(text: str, a: str, b: str, window: int = 3) -> bool:
    # very simple NEAR: token distance
    t = re.findall(r"\w+", _norm(text))
    a_tokens = re.findall(r"\w+", _norm(a))
    b_tokens = re.findall(r"\w+", _norm(b))
    if not a_tokens or not b_tokens:
        return False
    a0, b0 = a_tokens[0], b_tokens[0]
    pos_a = [i for i,w in enumerate(t) if w == a0]
    pos_b = [i for i,w in enumerate(t) if w == b0]
    for i in pos_a:
        for j in pos_b:
            if abs(i-j) <= window:
                return True
    return False

def compute_matches(title: str, body: str, terms: List[dict], rules: List[dict]) -> Dict[str, Any]:
    text = (title or "") + "\n" + (body or "")
    matched_terms = []
    score = 0.0

    for t in terms:
        term = t["term"]
        aliases = (t.get("aliases") or {}).get("aliases", [])
        priority = int(t.get("priority", 3))
        candidates = [term] + list(aliases)

        hit = False
        for c in candidates:
            if _contains_phrase(text, c):
                hit = True
                break

        if hit:
            matched_terms.append(term)
            # peso por prioridade + bônus título
            base = 10 + (priority * 5)
            if _contains_phrase(title or "", term):
                base *= 1.8
            score += base

    matched_rules = []
    severity = None

    def set_sev(s):
        nonlocal severity
        rank = {"low":1,"med":2,"high":3,"critical":4}
        if severity is None or rank.get(s,0) > rank.get(severity,0):
            severity = s

    for r in rules:
        if not r.get("enabled", True):
            continue
        dsl = r.get("query_dsl") or {}
        ok = eval_dsl(text, dsl)
        if ok:
            matched_rules.append(r["name"])
            set_sev(r.get("severity","med"))
            # regra puxa score mínimo
            if r.get("severity") == "critical":
                score = max(score, 90)
            elif r.get("severity") == "high":
                score = max(score, 70)
            elif r.get("severity") == "med":
                score = max(score, 40)
            else:
                score = max(score, 20)

    if severity is None:
        # infer severidade pelo score
        if score >= 80: severity = "high"
        elif score >= 55: severity = "med"
        elif score >= 25: severity = "low"
        else: severity = "low"

    return {
        "matched_terms": matched_terms,
        "matched_rules": matched_rules,
        "score": float(score),
        "severity": severity,
        "reasons": {"terms": matched_terms, "rules": matched_rules}
    }

def eval_dsl(text: str, dsl: Dict[str, Any]) -> bool:
    # DSL simples:
    # {"and":[...]} | {"or":[...]} | {"not":{...}} | {"phrase":"..."} | {"near":{"a":"...","b":"...","w":3}}
    if not dsl:
        return False
    if "and" in dsl:
        return all(eval_dsl(text, x) for x in dsl["and"])
    if "or" in dsl:
        return any(eval_dsl(text, x) for x in dsl["or"])
    if "not" in dsl:
        return not eval_dsl(text, dsl["not"])
    if "phrase" in dsl:
        return _contains_phrase(text, dsl["phrase"])
    if "near" in dsl:
        n = dsl["near"]
        return _near(text, n.get("a",""), n.get("b",""), int(n.get("w",3)))
    return False