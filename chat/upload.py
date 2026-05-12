import os
import uuid
import mimetypes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


# Allowed MIME types mapped to their category
ALLOWED_MIME_TYPES = {
    # Images
    'image/jpeg': 'image',
    'image/png': 'image',
    'image/webp': 'image',
    'image/gif': 'image',
    # Documents
    'application/pdf': 'file',
    'application/msword': 'file',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'file',
    'text/plain': 'file',
    # Audio
    'audio/mpeg': 'audio',
    'audio/wav': 'audio',
    'audio/x-wav': 'audio',
    'audio/webm': 'audio',
    'audio/ogg': 'audio',
    # Video
    'video/mp4': 'video',
    'video/quicktime': 'video',
    'video/webm': 'video',
}

MAX_FILE_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 104857600)  # 100MB default


def _upload_to_supabase(file_bytes, storage_path, mime_type):
    """Try Supabase upload. Returns public URL or raises Exception."""
    from supabase import create_client
    url = getattr(settings, 'SUPABASE_URL', '')
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', '')
    bucket = getattr(settings, 'SUPABASE_BUCKET', 'media-files')

    # If keys look like placeholders, skip immediately
    if not url or not key or key.startswith('eyJ...') or len(key) < 50:
        raise ValueError('Supabase not configured')

    client = create_client(url, key)
    client.storage.from_(bucket).upload(
        path=storage_path,
        file=file_bytes,
        file_options={'content-type': mime_type, 'upsert': 'true'}
    )
    return client.storage.from_(bucket).get_public_url(storage_path)


def _upload_to_local(file_bytes, storage_path, mime_type, request):
    """Fallback: save file to Django MEDIA_ROOT and return a root-relative URL.

    We intentionally return a relative path (e.g. /media/uploads/...)
    rather than an absolute URL (http://127.0.0.1:8000/...) because:
    - The Vite dev-server proxies /media/* → Django :8000
    - Devices on the LAN access Vite at https://<LAN-IP>:3000
    - An absolute 127.0.0.1 URL only works on the server machine itself.
    A relative URL is resolved against whatever host the browser is using,
    so it works identically on the server machine and any LAN device.
    """
    import os
    from django.conf import settings

    uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    prefix = 'uploads/'
    relative = storage_path[len(prefix):] if storage_path.startswith(prefix) else storage_path
    local_path = os.path.join('uploads', relative)
    saved_path = default_storage.save(local_path, ContentFile(file_bytes))
    # Return a root-relative URL — resolved by whichever host the client uses.
    return settings.MEDIA_URL + saved_path.replace('\\', '/')



class FileUploadView(APIView):
    """
    POST /api/chat/upload/
    Accepts a multipart file, validates it, uploads to Supabase Storage
    (with local disk fallback for development), and returns the public URL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # ── Size check ────────────────────────────────────────────────────────
        if file.size > MAX_FILE_SIZE:
            mb = MAX_FILE_SIZE // (1024 * 1024)
            return Response(
                {'error': f'File exceeds maximum size of {mb}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── MIME type detection ───────────────────────────────────────────────
        # Priority 1: trust the browser's Content-Type header (accurate for
        # MediaRecorder blobs — e.g. audio/webm, not video/webm).
        mime_type = getattr(file, 'content_type', None)

        # Priority 2: guess from filename extension (can misclassify .webm as video)
        if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
            guessed, _ = mimetypes.guess_type(file.name)
            if guessed and guessed in ALLOWED_MIME_TYPES:
                mime_type = guessed

        # Priority 3: magic-byte sniffing as last resort
        if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
            try:
                import magic
                header = file.read(2048)
                file.seek(0)
                mime_type = magic.from_buffer(header, mime=True)
            except Exception:
                mime_type = 'application/octet-stream'

        if mime_type not in ALLOWED_MIME_TYPES:
            return Response(
                {'error': f'File type "{mime_type}" is not supported'},
                status=status.HTTP_400_BAD_REQUEST
            )

        message_type = ALLOWED_MIME_TYPES[mime_type]

        # ── Build unique storage path ─────────────────────────────────────────
        ext = os.path.splitext(file.name)[1].lower() or '.bin'
        storage_path = f'uploads/{request.user.id}/{uuid.uuid4().hex}{ext}'
        file_bytes = file.read()

        # ── Try Supabase first, fallback to local disk ────────────────────────
        public_url = None
        storage_backend = 'local'

        try:
            public_url = _upload_to_supabase(file_bytes, storage_path, mime_type)
            storage_backend = 'supabase'
        except Exception as supabase_err:
            # Supabase not available — use local storage
            try:
                public_url = _upload_to_local(file_bytes, storage_path, mime_type, request)
                storage_backend = 'local'
            except Exception as local_err:
                return Response(
                    {'error': f'Upload failed: {local_err}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response({
            'file_url': public_url,
            'file_name': file.name,
            'file_size': file.size,
            'message_type': message_type,
            'mime_type': mime_type,
            'storage': storage_backend,
        }, status=status.HTTP_201_CREATED)
