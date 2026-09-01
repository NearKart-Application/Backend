"""
Lightweight User-Agent parser — no external library required.
Covers Android, iOS, Windows, macOS, major browsers.
"""
import re


def parse_ua(ua_string: str) -> dict:
    ua = ua_string or ''

    # ── Device type ──────────────────────────────────────────────────────────
    if 'iPad' in ua:
        device_type = 'tablet'
    elif any(t in ua for t in ['Mobile', 'Android', 'iPhone']):
        device_type = 'mobile'
    else:
        device_type = 'desktop'

    # ── OS + version ─────────────────────────────────────────────────────────
    if 'Android' in ua:
        m = re.search(r'Android\s([\d.]+)', ua)
        os, os_version = 'Android', (m.group(1) if m else '')
    elif 'iPhone OS' in ua or 'CPU OS' in ua:
        m = re.search(r'(?:iPhone OS|CPU OS)\s([\d_]+)', ua)
        os = 'iOS'
        os_version = m.group(1).replace('_', '.') if m else ''
    elif 'iPad' in ua:
        m = re.search(r'CPU OS\s([\d_]+)', ua)
        os = 'iPadOS'
        os_version = m.group(1).replace('_', '.') if m else ''
    elif 'Windows NT' in ua:
        nt_map = {'10.0': '10/11', '6.3': '8.1', '6.2': '8', '6.1': '7'}
        m = re.search(r'Windows NT\s([\d.]+)', ua)
        ver = m.group(1) if m else ''
        os, os_version = 'Windows', nt_map.get(ver, ver)
    elif 'Mac OS X' in ua:
        m = re.search(r'Mac OS X\s([\d_.]+)', ua)
        os = 'macOS'
        os_version = m.group(1).replace('_', '.') if m else ''
    elif 'Linux' in ua:
        os, os_version = 'Linux', ''
    else:
        os, os_version = 'Unknown', ''

    # ── Device model (Android only) ──────────────────────────────────────────
    device_name = ''
    if 'Android' in ua:
        m = re.search(r';\s*([^;)]+?)\s*(?:Build/|MIUI/|\))', ua)
        if m:
            device_name = m.group(1).strip()

    # ── Browser / App ────────────────────────────────────────────────────────
    if 'NearKartApp/' in ua:
        browser = 'NearKart App'
    elif 'Edg/' in ua or 'Edge/' in ua:
        browser = 'Edge'
    elif 'OPR/' in ua or 'Opera' in ua:
        browser = 'Opera'
    elif 'SamsungBrowser' in ua:
        browser = 'Samsung Browser'
    elif 'Chrome/' in ua and 'Chromium' not in ua:
        browser = 'Chrome'
    elif 'Firefox/' in ua:
        browser = 'Firefox'
    elif 'Safari/' in ua and 'Chrome' not in ua:
        browser = 'Safari'
    else:
        browser = 'Unknown'

    return {
        'device_type': device_type,
        'device_name': device_name,
        'os':          os,
        'os_version':  os_version,
        'browser':     browser,
    }


def get_client_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
