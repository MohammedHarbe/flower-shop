import re


_DIGIT_TRANSLATION = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)
_EGYPTIAN_MOBILE = re.compile(r"^\+201[0125][0-9]{8}$")


def normalize_egyptian_mobile(value: str) -> str:
    """Normalize supported Egyptian mobile formats to +201xxxxxxxx."""
    if not isinstance(value, str):
        raise ValueError("Enter a valid Egyptian mobile number")
    compact = re.sub(r"[\s().-]", "", value.translate(_DIGIT_TRANSLATION).strip())
    if compact.startswith("0020"):
        compact = "+20" + compact[4:]
    elif compact.startswith("20"):
        compact = "+" + compact
    elif compact.startswith("0"):
        compact = "+20" + compact[1:]
    if not _EGYPTIAN_MOBILE.fullmatch(compact):
        raise ValueError("Enter a valid Egyptian mobile number")
    return compact
