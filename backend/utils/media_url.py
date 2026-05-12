"""
backend/utils/media_url.py
──────────────────────────
Utility for normalising locally-stored media URLs.

Problem
-------
When a file is uploaded locally (Supabase not configured), Django used to call
request.build_absolute_uri() and store/return URLs like:

    http://127.0.0.1:8000/media/uploads/<file>

That URL only resolves on the machine running the Django server.  Any other
device on the LAN gets a connection-refused because 127.0.0.1 refers to
*their own* localhost, not the server.

Solution
--------
The Vite dev server now proxies /media/* → http://127.0.0.1:8000 (see
vite.config.js), so every device on the LAN can load media via the Vite HTTPS
URL it is already using.  We simply need to strip the absolute host prefix from
any URL that points at a local Django instance and return the root-relative path.

External URLs (e.g. Supabase CDN, https://...) are returned unchanged.
"""

import re

# Patterns that identify a locally-hosted Django dev-server URL.
# Covers http and https variants of localhost / 127.0.0.1 / any LAN IP.
_LOCAL_PREFIX_RE = re.compile(
    r'^https?://(127\.0\.0\.1|localhost|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?',
    re.IGNORECASE,
)


def to_relative_url(url: str) -> str:
    """
    Convert a localhost absolute media URL to a root-relative path.

    Examples
    --------
    >>> to_relative_url("http://127.0.0.1:8000/media/uploads/abc.jpg")
    '/media/uploads/abc.jpg'

    >>> to_relative_url("https://cdn.supabase.co/storage/v1/object/public/file.jpg")
    'https://cdn.supabase.co/storage/v1/object/public/file.jpg'  # unchanged

    >>> to_relative_url("/media/uploads/abc.jpg")
    '/media/uploads/abc.jpg'  # already relative — unchanged

    >>> to_relative_url(None)
    None
    """
    if not url or not isinstance(url, str):
        return url
    # Already relative — nothing to do.
    if url.startswith('/'):
        return url
    # Strip the local host prefix, leaving the path (e.g. /media/...).
    stripped = _LOCAL_PREFIX_RE.sub('', url)
    if stripped != url:
        # Make sure the result starts with /
        return stripped if stripped.startswith('/') else '/' + stripped
    # External URL — return as-is.
    return url


def normalise_media_list(urls) -> list:
    """
    Apply to_relative_url() to every item in a list of media URLs.
    Safely handles None / non-list values.
    """
    if not urls or not isinstance(urls, list):
        return urls or []
    return [to_relative_url(u) for u in urls]
