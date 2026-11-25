import pytest

from engine.mirror import _log_balance


@pytest.mark.parametrize("a, b, neutral, span, expected", [
    (0, 0, 1, 1, 0.0),          # rien des deux côtés
    (5, 0, 1, 1, -1.0),         # seul a existe
    (0, 5, 1, 1, 1.0),          # seul b existe
    (3, 3, 1, 1, 0.0),
    (1, 10, 10, 1, 0.0),        # b = neutral × a
    (1, 10 ** 0.5, 1, 1, 0.5),
    (1, 10, 1, 2, 0.5),
    (1, 10, 1, 1, 1.0),
    (10, 1, 1, 1, -1.0),
    (1, 1000, 1, 1, 1.0),       # écrêté
    (1000, 1, 1, 1, -1.0),      # écrêté
])
def test_log_balance(a, b, neutral, span, expected):
    assert _log_balance(a, b, neutral, span) == pytest.approx(expected)
