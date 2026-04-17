import pytest

from app.parse import parse_clauses


def test_parse_returns_tokens_with_pos_and_lemma():
    [clause] = parse_clauses("The dogs ran home.", language="en")
    texts = [t.text for t in clause.tokens]
    assert "dogs" in texts
    ran = next(t for t in clause.tokens if t.text == "ran")
    assert ran.lemma == "run"
    assert ran.pos == "VERB"


def test_parse_splits_sentences_into_clauses():
    clauses = parse_clauses("I run. You walk.", language="en")
    assert len(clauses) == 2
    assert any(t.text == "run" for t in clauses[0].tokens)
    assert any(t.text == "walk" for t in clauses[1].tokens)


def test_parse_marks_stop_words():
    [clause] = parse_clauses("The cat is here.", language="en")
    stops = [t.text for t in clause.tokens if t.is_stop]
    assert "The" in stops or "the" in stops
    assert "is" in stops
