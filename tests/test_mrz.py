import pytest
from app.services.mrz import compute_check_digit,char_value



def test_check_digit_birth_date():

    assert compute_check_digit("740812") == 2


def test_check_digit_passport_number():

    assert compute_check_digit("L898902C3") == 6


def test_check_digit_expiry_date():

    assert compute_check_digit("120415") == 9


def test_char_value_rejects_lowercase():
    with pytest.raises(ValueError):
        char_value("a")
