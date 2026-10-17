"""
NearSpot Code Generator
=======================
Code formats by role:
  NSC-<NN>-<AA>-<RRRR>  customers  (15 chars)
  NSB-<NN>-<AA>-<RRRR>  vendors and workers  (15 chars)
  NS-<NN>-<AA>-<RRRR>   admins and legacy codes  (13 chars)

  NN   — 2-char name tag  (initials of each word, e.g. "Sneha Fashion" → SF)
  AA   — 2-char area tag  (first 2 alpha chars of area/city; XX when unknown)
  RRRR — 4-char random suffix (uppercase letters + digits)

New users receive role-prefixed codes (NSC/NSB).
Existing NS- codes are never modified by this function.

Examples:
  customer / "Arjun Kumar" / "Kurnool"    → NSC-AK-KU-4X2B
  vendor   / "Sneha Fashion" / "Hyderabad" → NSB-SF-HY-9K3M
  customer / "Priya" / ""                 → NSC-PR-XX-7R1Q
"""
import re
import secrets
import string

_CHARS = string.ascii_uppercase + string.digits


def _name_tag(name: str) -> str:
    """
    2-char abbreviation from a name.
    Multi-word → first letter of each of the first two words.
    Single word → first two characters.
    """
    name = name.strip().upper()
    if not name:
        return 'XX'
    words = name.split()
    if len(words) >= 2:
        tag = words[0][0] + words[1][0]
    else:
        tag = name[:2].ljust(2, 'X')
    return tag[:2]


def _area_tag(area: str) -> str:
    """
    2-char abbreviation from an area / city / address string.
    Strips non-alpha characters and takes the first two letters.
    """
    clean = re.sub(r'[^A-Za-z]', '', area).upper()
    if not clean:
        return 'XX'
    return clean[:2].ljust(2, 'X')


def _random_suffix(k: int = 6) -> str:
    return ''.join(secrets.choice(_CHARS) for _ in range(k))


def make_ns_code(name: str = '', area: str = '', role: str = '') -> str:
    """
    Generate a NearSpot-standard unique code.

    Args:
        name: Display name of the user or store (e.g. "Sneha Fashion").
        area: Area / city / locality (e.g. "Kukatpally").
        role: UserRole string — 'customer' → NSC prefix, 'vendor' → NSB prefix.

    Returns:
        A code like "NSC-AK-KU-4X2B" (15 chars) or "NS-AK-KU-4X2B" (13 chars).
    """
    nn = _name_tag(name)
    aa = _area_tag(area)
    rr = _random_suffix(4)
    if role == 'vendor':
        return f'NSB-{nn}-{aa}-{rr}'
    if role == 'customer':
        return f'NSC-{nn}-{aa}-{rr}'
    return f'NS-{nn}-{aa}-{rr}'
