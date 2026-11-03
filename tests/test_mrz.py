from app.services.mrz import compute_check_digit


def test_check_digit_birth_date():
    assert compute_check_digit("740812") == 3