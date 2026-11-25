import pytest

from engine.game import _amortize


@pytest.mark.parametrize("years", [0, 1])
def test_last_year_pays_everything(years):
    pay, rest = _amortize(1000, 0.05, years, 0.02)
    assert pay == pytest.approx(1050.0)
    assert rest == 0.0


def test_annuity_payment():
    pay, rest = _amortize(100_000, 0.05, 20, 0.0)
    assert pay == pytest.approx(8024.26, rel=1e-4)
    assert rest == pytest.approx(105_000 - pay)


def test_inflation_deflates_remaining_balance():
    _, nominal = _amortize(100_000, 0.05, 20, 0.0)
    _, real = _amortize(100_000, 0.05, 20, 0.03)
    assert real == pytest.approx(nominal / 1.03)


def test_tiny_remainder_is_floored():
    assert _amortize(0.5, 0.05, 10, 0.0)[1] == 0.0
