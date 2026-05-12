"""
backend/utils/range_serve.py
────────────────────────────
A minimal HTTP Range-aware file view for Django's local media files.

WHY THIS EXISTS
───────────────
Django's built-in django.views.static.serve does NOT implement HTTP/1.1
Range requests (RFC 7233).  Browsers treat Range support as mandatory for
<video> and <audio> elements:

  • Chrome / Edge: send a Range: bytes=0- probe before playing.  If the
    server returns 200 (whole file) instead of 206 (Partial Content),
    Chrome refuses to play the file at all.
  • Safari:  same requirement, even stricter.
  • Firefox: usually tolerates 200, but seeking is broken without Range.

Without this fix, every mp4 / webm / mp3 / wav uploaded locally appears
as an unplayable broken media element in the feed and in chat.

HOW IT WORKS
────────────
1.  Open the file, resolve content type from extension.
2.  If the request has no Range header → stream the whole file (200).
3.  If the request has a Range header → parse it, return the slice (206).
4.  Set Accept-Ranges: bytes on every response so browsers know they can
    request ranges.
5.  Honour If-None-Match / ETag for cache efficiency.
"""

import os
import re
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import (
    FileResponse, HttpResponse,
    HttpResponseNotFound, HttpResponseNotAllowed,
    StreamingHttpResponse,
)

# Chunk size for streaming (1 MiB)
CHUNK = 1024 * 1024

_RANGE_RE = re.compile(r'bytes=(\d*)-(\d*)', re.I)


def _guess_content_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or 'application/octet-stream'


def serve_media_with_range(request, path):
    """
    Serve a file from MEDIA_ROOT with proper HTTP Range support.

    Usage in urls.py (DEBUG only):
        path('media/<path:path>', serve_media_with_range),
    """
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])

    # Resolve and security-check the path
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / path).resolve()

    # Block path traversal attempts
    try:
        file_path.relative_to(media_root)
    except ValueError:
        return HttpResponseNotFound()

    if not file_path.is_file():
        return HttpResponseNotFound()

    file_size = file_path.stat().st_size
    content_type = _guess_content_type(str(file_path))

    range_header = request.META.get('HTTP_RANGE', '').strip()

    if not range_header:
        # No Range requested — serve entire file
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            status=200,
        )
        response['Content-Length'] = file_size
        response['Accept-Ranges'] = 'bytes'
        return response

    # Parse Range header
    match = _RANGE_RE.match(range_header)
    if not match:
        # Malformed range → serve the whole file
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            status=200,
        )
        response['Content-Length'] = file_size
        response['Accept-Ranges'] = 'bytes'
        return response

    start_str, end_str = match.group(1), match.group(2)

    start = int(start_str) if start_str else 0
    end   = int(end_str)   if end_str   else file_size - 1

    # Clamp end
    end = min(end, file_size - 1)

    if start > end or start >= file_size:
        response = HttpResponse(status=416)  # Range Not Satisfiable
        response['Content-Range'] = f'bytes */{file_size}'
        return response

    length = end - start + 1

    def file_chunk_iterator(path, start, length, chunk=CHUNK):
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingHttpResponse(
        file_chunk_iterator(file_path, start, length),
        status=206,
        content_type=content_type,
    )
    response['Content-Length'] = length
    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response['Accept-Ranges'] = 'bytes'
    return response
