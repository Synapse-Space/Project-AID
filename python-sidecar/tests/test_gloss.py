from app.gloss import to_gloss
from app.parse import parse_clauses


def gloss_of(text: str) -> list[str]:
    clause = parse_clauses(text, "en")[0]
    return [g.gloss for g in to_gloss(clause)]


def test_drops_articles_and_aux():
    assert gloss_of("The cat is here.") == ["CAT", "HERE"]


def test_lemmatizes_verbs():
    out = gloss_of("I am running.")
    assert "RUN" in out
    assert "running" not in [o.lower() for o in out]
