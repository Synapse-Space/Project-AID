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


# More rule implementations land in Task 13.

RULES: dict[str, Callable[[list[ParsedToken], dict], list[ParsedToken]]] = {
    "drop_pos": _drop_pos,
    "drop_lemma": _drop_lemma,
    "lemmatize_verb": _lemmatize_verb,
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
