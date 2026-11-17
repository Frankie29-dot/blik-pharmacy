import re

_SEPARATORS = re.compile(r"[\s\-().]")
_NATIONAL_MOBILE = re.compile(r"[789][0-9]{9}")  # e.g. 903 123 4567 (070x, 080x, 081x, 090x, 091x)

INVALID_PHONE_MESSAGE = (
    "Enter a valid Nigerian mobile number, e.g. 0903 123 4567 or +234 903 123 4567"
)


def normalize_ng_phone(raw: str) -> str:
    """Return a Nigerian mobile number in +234XXXXXXXXXX form, or raise ValueError.

    Accepts: 09031234567, 0903 123 4567, +2349031234567, 2349031234567,
    002349031234567 and the common typo +234 (0) 903 123 4567.
    """
    value = _SEPARATORS.sub("", raw.strip())

    if value.startswith("+234"):
        national = value[4:]
    elif value.startswith("00234"):
        national = value[5:]
    elif value.startswith("234"):
        national = value[3:]
    elif value.startswith("0"):
        national = value[1:]
    else:
        raise ValueError(INVALID_PHONE_MESSAGE)

    # "+234 (0) 903 ..." leaves a stray 0 after the country code.
    if national.startswith("0"):
        national = national[1:]

    if not _NATIONAL_MOBILE.fullmatch(national):
        raise ValueError(INVALID_PHONE_MESSAGE)

    return f"+234{national}"
