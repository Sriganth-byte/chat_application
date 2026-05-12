"""
Link preview fetcher — /api/posts/link-preview/?url=https://...
Fetches OG metadata server-side (avoids CORS), cached in Redis for 24h.
"""
import re
import hashlib
from urllib.parse import urlparse, urljoin

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache


def _extract_og(html: str, base_url: str) -> dict:
    def meta(prop):
        m = re.search(
            rf'<meta[^>]+(?:property|name)=["\']og:{prop}["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:{prop}["\']',
            html, re.IGNORECASE
        )
        return m.group(1).strip() if m else ''

    def tag(name):
        m = re.search(rf'<{name}[^>]*>([^<]+)</{name}>', html, re.IGNORECASE)
        return m.group(1).strip() if m else ''

    title = meta('title') or tag('title')
    description = meta('description') or (
        re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE) or
        type('', (), {'group': lambda s, n: ''})()
    )
    if hasattr(description, 'group'):
        description = description.group(1)
    else:
        description = ''

    image = meta('image')
    if image and not image.startswith('http'):
        image = urljoin(base_url, image)

    parsed = urlparse(base_url)
    domain = parsed.netloc.replace('www.', '')

    return {
        'title': title[:200] if title else '',
        'description': description[:500] if description else '',
        'image': image or '',
        'domain': domain,
        'url': base_url,
    }


class LinkPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        url = request.query_params.get('url', '').strip()
        if not url or not url.startswith(('http://', 'https://')):
            return Response({'error': 'Invalid URL'}, status=400)

        # Limit URL length
        if len(url) > 2000:
            return Response({'error': 'URL too long'}, status=400)

        cache_key = 'og:' + hashlib.md5(url.encode()).hexdigest()
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'MindConnect/1.0 (Link Preview Bot)',
                    'Accept': 'text/html',
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                content_type = resp.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    return Response({'error': 'Not an HTML page'}, status=400)
                html = resp.read(50000).decode('utf-8', errors='ignore')

            data = _extract_og(html, url)
            cache.set(cache_key, data, timeout=86400)  # 24h
            return Response(data)
        except Exception as e:
            return Response({'error': f'Could not fetch preview: {str(e)}'}, status=400)
