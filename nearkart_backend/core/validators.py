"""
NearKart — Shared Validators
"""
import re
from rest_framework.exceptions import ValidationError

# Matches any http/https URL that is NOT a nearkart domain
_EXTERNAL_URL_RE = re.compile(
    r'https?://(?!(?:www\.)?nearkart\.(?:com|app|in))[^\s<>"\']+',
    re.IGNORECASE,
)


def validate_no_external_links(text: str) -> str:
    """
    Rejects any text that contains an external URL.
    Only nearkart:// deep links and nearkart.com/app/in URLs are allowed.
    """
    if _EXTERNAL_URL_RE.search(text):
        raise ValidationError(
            'External links are not allowed. Only NearKart app links are permitted.'
        )
    return text
