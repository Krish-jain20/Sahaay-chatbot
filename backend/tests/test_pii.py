import pytest

from app.safety.pii import mask_pii, verhoeff_valid

# 2345 6789 0124 is Verhoeff-valid (computed in test_verhoeff_reference).
VALID_AADHAAR = "234567890124"


def test_verhoeff_reference():
    assert verhoeff_valid("2363")  # textbook example: 236 + check digit 3
    assert not verhoeff_valid("2364")
    assert verhoeff_valid(VALID_AADHAAR)


@pytest.mark.parametrize(
    ("text", "expected", "kinds"),
    [
        (f"my aadhaar is {VALID_AADHAAR}", "my aadhaar is XXXX XXXX 0124", ["aadhaar"]),
        ("aadhaar 2345 6789 0124 hai", "aadhaar XXXX XXXX 0124 hai", ["aadhaar"]),
        ("PAN: ABCPE1234F", "PAN: XXXXXX234F", ["pan"]),
        ("call 9876543210", "call XXXXXX3210", ["phone"]),
        ("call +91 98765 43210", "call XXXXXX3210", ["phone"]),
        ("account no: 123456789012", "account no: XXXXXXXX9012", ["bank_account"]),
        ("मेरा खाता 001234567890 है", "मेरा खाता XXXXXXXX7890 है", ["bank_account"]),
    ],
)
def test_masks(text, expected, kinds):
    masked, findings = mask_pii(text)
    assert masked == expected
    assert [f.kind for f in findings] == kinds


@pytest.mark.parametrize(
    "text",
    [
        "family income is 300000 per year",
        "income ₹3,00,000",
        "born on 1960-01-01",
        "number 234567890123 is not a valid aadhaar",  # fails Verhoeff
        "reference 123456789012",  # starts with 1: never an Aadhaar, no account keyword
        "I scored 87.5 percent",
        "pin code 110001",
        "word ABCDE",
        "ABCXE1234F has a bad 4th letter",
    ],
)
def test_false_positives_untouched(text):
    masked, findings = mask_pii(text)
    assert masked == text
    assert findings == []


def test_never_leaks_full_numbers():
    text = f"aadhaar {VALID_AADHAAR}, phone 9876543210, a/c 5555666677778888, PAN ABCPE1234F"
    masked, findings = mask_pii(text)
    for secret in [VALID_AADHAAR, "9876543210", "5555666677778888", "ABCPE1234F"]:
        assert secret not in masked
    assert len(findings) == 4
