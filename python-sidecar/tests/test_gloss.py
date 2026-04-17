import json
from pathlib import Path

import pytest

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


def test_pronoun_normalization():
    assert "I" in gloss_of("I see the dog.")
    assert "YOU" in gloss_of("Your book is here.")


def test_sov_reorder():
    # "I drink water" -> I WATER DRINK
    assert gloss_of("I drink water.") == ["I", "WATER", "DRINK"]


def test_time_hoist():
    # "I go to school tomorrow" -> TOMORROW I SCHOOL GO
    out = gloss_of("I go to school tomorrow.")
    assert out[0] == "TOMORROW"


def test_negation_move():
    out = gloss_of("I do not go.")
    assert out.index("GO") < out.index("NOT")


def test_wh_to_end():
    out = gloss_of("Where are you going?")
    assert out[-1] == "WHERE"


def test_plural_marking():
    out = gloss_of("The dogs run.")
    assert any(tok == "DOG+" for tok in out)


def test_possessive_juxtaposition():
    out = gloss_of("My book is here.")
    assert out[0] == "I"
    assert "BOOK" in out


FIXTURES = Path(__file__).parent / "fixtures" / "en_isl_pairs.json"


@pytest.mark.parametrize("pair", json.loads(FIXTURES.read_text()))
def test_gold_pair(pair):
    got = gloss_of(pair["en"])
    assert got == pair["isl"], f"{pair['en']!r}: got {got}, want {pair['isl']}"
