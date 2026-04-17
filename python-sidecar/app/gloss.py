"""Rule engine: parsed English clause -> ISL gloss token list."""

from pathlib import Path
from typing import Callable

import yaml

from app.models import GlossToken, ParsedClause, ParsedToken

RulesPath = Path(__file__).parent / "rules.yaml"


def _load_rules() -> list[dict]:
    return yaml.safe_load(RulesPath.read_text())["rules"]


# ---- Rule implementations ----

def _drop_pos(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.pos not in params["pos"]]


def _drop_lemma(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.lemma.lower() not in params["lemmas"]]


def _lemmatize_verb(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos in ("VERB",):
            out.append(t.model_copy(update={"text": t.lemma}))
        else:
            out.append(t)
    return out


PRONOUN_MAP = {
    "i": "I", "me": "I", "my": "I", "mine": "I",
    "you": "YOU", "your": "YOU", "yours": "YOU",
    "he": "HE-SHE", "she": "HE-SHE", "him": "HE-SHE", "her": "HE-SHE",
    "his": "HE-SHE", "hers": "HE-SHE",
    "we": "WE", "us": "WE", "our": "WE", "ours": "WE",
    "they": "THEY", "them": "THEY", "their": "THEY",
    "it": "IT",
}


def _normalize_pronoun(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos == "PRON":
            mapped = PRONOUN_MAP.get(t.text.lower())
            if mapped:
                out.append(t.model_copy(update={"text": mapped}))
                continue
        out.append(t)
    return out


def _reorder_sov(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    """If a clause has S V O (dep tags nsubj / dobj / ROOT verb), move O before V."""
    verb_idx = next((i for i, t in enumerate(tokens) if t.pos == "VERB"), None)
    if verb_idx is None:
        return tokens
    obj_idx = next(
        (i for i, t in enumerate(tokens) if t.dep in ("dobj", "obj", "attr") and i > verb_idx),
        None,
    )
    if obj_idx is None:
        return tokens
    reordered = tokens.copy()
    obj = reordered.pop(obj_idx)
    reordered.insert(verb_idx, obj)
    return reordered


def _hoist_time_first(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    time_lemmas = set(params["time_lemmas"])
    time_idx = next(
        (i for i, t in enumerate(tokens) if t.lemma.lower() in time_lemmas),
        None,
    )
    if time_idx is None or time_idx == 0:
        return tokens
    out = tokens.copy()
    t = out.pop(time_idx)
    return [t] + out


def _move_negation(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    neg_idx = next((i for i, t in enumerate(tokens) if t.dep == "neg" or t.text.lower() == "not"), None)
    if neg_idx is None:
        return tokens
    verb_idx = next((i for i, t in enumerate(tokens) if t.pos == "VERB"), None)
    if verb_idx is None or neg_idx > verb_idx:
        return tokens
    out = tokens.copy()
    neg = out.pop(neg_idx)
    if neg_idx < verb_idx:
        verb_idx -= 1
    out.insert(verb_idx + 1, neg)
    return out


def _wh_to_end(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    wh = set(params["wh_lemmas"])
    idx = next((i for i, t in enumerate(tokens) if t.lemma.lower() in wh), None)
    if idx is None or idx == len(tokens) - 1:
        return tokens
    out = tokens.copy()
    t = out.pop(idx)
    out.append(t)
    return out


def _plural_repetition(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    out: list[ParsedToken] = []
    for t in tokens:
        if t.pos == "NOUN" and t.text.lower() != t.lemma.lower() and t.text.lower().endswith("s"):
            out.append(t.model_copy(update={"text": f"{t.lemma}+"}))
        else:
            out.append(t)
    return out


def _possessive_drop(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    return [t for t in tokens if t.dep != "poss" or t.text.lower() in ("i", "you", "we", "he", "she", "they")]


def _number_pass_through(tokens: list[ParsedToken], params: dict) -> list[ParsedToken]:
    # Placeholder: keep numerals as-is (ISL number signs exist in wordmap).
    return tokens


RULES: dict[str, Callable[[list[ParsedToken], dict], list[ParsedToken]]] = {
    "drop_pos": _drop_pos,
    "drop_lemma": _drop_lemma,
    "lemmatize_verb": _lemmatize_verb,
    "normalize_pronoun": _normalize_pronoun,
    "reorder_sov": _reorder_sov,
    "hoist_time_first": _hoist_time_first,
    "move_negation_after_verb": _move_negation,
    "wh_to_end": _wh_to_end,
    "plural_repetition": _plural_repetition,
    "possessive_drop": _possessive_drop,
    "number_pass_through": _number_pass_through,
}


def _apply_rules(tokens: list[ParsedToken]) -> list[ParsedToken]:
    for rule in _load_rules():
        impl = RULES.get(rule["kind"])
        if impl is None:
            continue  # filled in by later tasks
        tokens = impl(tokens, rule)
    return tokens


def to_gloss(clause: ParsedClause) -> list[GlossToken]:
    processed = _apply_rules(list(clause.tokens))
    return [
        GlossToken(gloss=t.text.upper(), kind="sign", source_text=t.text)
        for t in processed
    ]
