import pytest

from engine.game import _amount


def test_valid_amount_returns_float():
    assert _amount({"amount": "250.5"}) == 250.5
    assert isinstance(_amount({"amount": 1000}), float)


@pytest.mark.parametrize("amount", [0, -5, "-0.01"])
def test_non_positive_amount_raises(amount):
    with pytest.raises(ValueError):
        _amount({"amount": amount})


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), "inf", "nan"])
def test_non_finite_amount_raises(amount):
    with pytest.raises(ValueError):
        _amount({"amount": amount})
