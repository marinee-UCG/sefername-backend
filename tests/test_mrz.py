import pytest
from app.services.mrz import compute_check_digit,char_value,parse_td3

ICAO_LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
ICAO_LINE2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"




def test_check_digit_birth_date():

    assert compute_check_digit("740812") == 2


def test_check_digit_passport_number():

    assert compute_check_digit("L898902C3") == 6


def test_check_digit_expiry_date():

    assert compute_check_digit("120415") == 9


def test_char_value_rejects_lowercase():
    with pytest.raises(ValueError):
        char_value("a")

def test_parse_td3_icao_example():
   result = parse_td3(ICAO_LINE1,ICAO_LINE2)
   expected = {
        "surname": "ERIKSSON",
        "given_names": "ANNA MARIA",
        "document_number": "L898902C3",
        "birth_date": "1974-08-12",
        "expiry_date": "2012-04-15",
        "all_checks_passed": True,
   }
   
   for field,value in expected.items():
       assert result[field]== value,field