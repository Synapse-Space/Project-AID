"""spaCy-based clause parsing for English. Hindi added in Month 3."""

from functools import lru_cache

import spacy

from app.models import Language, ParsedClause, ParsedToken


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def parse_clauses(text: str, language: Language = "en") -> list[ParsedClause]:
    if language != "en":
        raise NotImplementedError("Hindi parsing lands in Month 3")
    doc = _nlp()(text)
    clauses: list[ParsedClause] = []
    for sent in doc.sents:
        tokens = [
            ParsedToken(
                text=t.text,
                lemma=t.lemma_,
                pos=t.pos_,
                dep=t.dep_,
                head=t.head.i - sent.start,
                is_stop=bool(t.is_stop),
            )
            for t in sent
            if not t.is_punct
        ]
        clauses.append(ParsedClause(tokens=tokens, language="en"))
    return clauses
