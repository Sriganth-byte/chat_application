# MindConnect - Real-Time Chat Application

A production-ready real-time chat application built with Django, Django REST Framework, Django Channels, Redis, and Supabase PostgreSQL.

## Features

### Core Features
- **JWT Authentication** - Secure token-based authentication with refresh rotation
- **Real-Time Messaging** - WebSocket-based instant messaging via Django Channels
- **User Presence** - Online/offline status with multi-device session tracking
- **File Uploads** - Support for images, documents, audio, and video (Supabase Storage)
- **Search** - Full-text search across users, messages, and groups
- **Notifications** - Real-time and email notifications for messages, mentions, and invites

### Message Types
- Text messages
- Images (JPG, PNG, WEBP)
- Documents (PDF, DOCX, TXT)
- Audio (MP3, WAV)
- Video (MP4, MOV)

### Security
- Rate limiting (login: 5/min, register: 3/hour)
- CORS protection
- CSRF protection
- File validation (size, type, MIME)
- Password hashing (Django built-in)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Django 6.0.5 |
| APIs | Django REST Framework 3.17.1 |
| WebSockets | Django Channels 4.3.2 |
| Database | Supabase PostgreSQL 15 |
| Cache & Broker | Redis 7 |
| Authentication | JWT (SimpleJWT) |
| Storage | Supabase Storage |
| Task Queue | Celery (for async tasks) |
| Frontend | React (recommended) |
| Styling | Tailwind CSS / Material UI |

## Project Structure

```
MindConnect/
├── backend/
│   ├── settings.py          # Django configuration
│   ├── urls.py              # URL routing
│   ├── asgi.py              # ASGI for Channels
│   └── wsgi.py              # WSGI for deployment
├── users/                   # User authentication & profiles
│   ├── models.py           # Custom User model
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # REST endpoints
│   ├── consumers.py        # WebSocket handlers
│   ├── admin.py            # Admin panel config
│   └── urls.py             # URL patterns
├── chat/                   # Messaging core
│   ├── models.py           # Room, Message
│   ├── serializers.py      # Message/Room serializers
│   ├── views.py            # REST API views
│   ├── consumers.py        # Chat WebSocket consumer
│   ├── routing.py          # WebSocket routes
│   └── urls.py             # API endpoints
├── notifications/          # Notification system
│   ├── models.py           # Notification model
│   ├── serializers.py      # Notification serializer
│   ├── views.py            # Notification API
│   ├── consumers.py        # Real-time notifications
│   └── urls.py             # Notification routes
├── core/                   # Shared utilities
│   ├── permissions.py      # Custom permissions
│   ├── pagination.py       # Pagination classes
│   └── mixins.py           # Reusable view mixins
├── static/                 # Static files
├── media/                  # Media uploads
├── templates/              # HTML templates
├── logs/                   # Application logs
├── .env                    # Environment variables (create from .env.example)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (or Supabase account)
- Redis server
- Node.js 18+ (for frontend)

### 1. Clone Repository
```bash
git clone <repository-url>
cd MindConnect
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
# - Supabase database URL
# - Supabase storage keys
# - JWT secret key
# - Redis URL
```

### 5. Setup Database

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (https://www.postgresql.org/download/)
createdb mindconnect
```

**Option B: Supabase Cloud**
1. Create account at https://supabase.com
2. Create new project
3. Get connection string from Settings → Database
4. Update `.env` with `DATABASE_URL`

### 6. Install & Start Redis
```bash
# Using Docker
docker run --name mindconnect-redis -p 6379:6379 -d redis:7-alpine

# Or install locally (https://redis.io/download)
```

### 7. Run Migrations
```bash
python manage.py makemigrations users chat notifications
python manage.py migrate
```

### 8. Create Superuser
```bash
python manage.py createsuperuser
```

### 9. Collect Static Files (Production)
```bash
python manage.py collectstatic
```

### 10. Run Development Server
```bash
# Terminal 1: Django (with Channels)
python manage.py runserver

# Terminal 2: Celery worker (for async tasks)
celery -A backend worker -l info

# Terminal 3: Celery beat (scheduled tasks)
celery -A backend beat -l info
```

**Note**: For WebSocket support, use Daphne or Uvicorn:
```bash
pip install daphne
daphne backend.asgi:application --port 8000
```

## API Documentation

### Authentication Endpoints

#### Register User
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password123",
  "password2": "secure_password123",
  "bio": "Hello world!"
}
```
**Response**: `201 Created`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "avatar": null,
  "bio": "Hello world!",
  "is_online": false,
  "last_seen": null,
  "date_joined": "2026-05-09T10:00:00Z"
}
```

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "secure_password123"
}
```
**Response**: `200 OK`
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Get Profile
```http
GET /api/auth/profile/
Authorization: Bearer <access_token>
```
**Response**: `200 OK`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "avatar_url": null,
  "bio": "Hello world!",
  "is_online": true,
  "last_seen": "2026-05-09T10:30:00Z",
  "date_joined": "2026-05-09T10:00:00Z"
}
```

### Chat Endpoints

#### List Rooms
```http
GET /api/chat/rooms/
Authorization: Bearer <access_token>
```
**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "John & Jane",
    "type": "dm",
    "avatar": null,
    "description": "",
    "created_at": "2026-05-09T10:00:00Z",
    "members": [...],
    "last_message": {...},
    "unread_count": 2
  }
]
```

#### Create Room
```http
POST /api/chat/rooms/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Project Team",
  "type": "group",
  "description": "Team coordination",
  "members": [2, 3, 4]  # User IDs
}
```

#### List Messages
```http
GET /api/chat/rooms/1/messages/
Authorization: Bearer <access_token>
```
**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "room": 1,
    "sender": {
      "id": 1,
      "username": "john_doe"
    },
    "message_type": "text",
    "content": "Hello team!",
    "file_url": null,
    "is_seen": true,
    "edited": false,
    "created_at": "2026-05-09T10:05:00Z",
    "reply_to_data": null
  }
]
```

#### Send Message
```http
POST /api/chat/rooms/1/send/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Hey everyone, how's the project going?",
  "message_type": "text"
}
```

### Notification Endpoints

#### List Notifications
```http
GET /api/notifications/
Authorization: Bearer <access_token>
```
**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "type": "message",
    "message": "Jane: Hi there!",
    "data": {"room_id": 1},
    "is_read": false,
    "created_at": "2026-05-09T10:35:00Z"
  }
]
```

#### Mark as Read
```http
POST /api/notifications/1/mark-read/
Authorization: Bearer <access_token>
```

## WebSocket Events

Connect to WebSocket endpoints:

### Chat WebSocket
```
ws://localhost:8000/ws/chat/{room_id}/
```

**Client → Server:**
```json
{"type": "message", "content": "Hello!"}
{"type": "typing_start"}
{"type": "typing_stop"}
{"type": "message_seen", "message_ids": [1,2,3]}
```

**Server → Client:**
```json
{
  "event": "new_message",
  "data": { /* Message object */ }
}
{
  "event": "typing_start",
  "data": { "user_id": "1", "username": "john" }
}
{
  "event": "typing_stop",
  "data": { "user_id": "1" }
}
{
  "event": "message_seen",
  "data": { "user_id": "2", "message_ids": [1,2] }
}
{
  "event": "chat_history",
  "messages": [ /* Array of recent messages */ ]
}
```

### Notifications WebSocket
```
ws://localhost:8000/ws/notifications/
```

**Server → Client:**
```json
{
  "event": "notification",
  "data": {
    "type": "message",
    "message": "Jane: Hi!",
    "data": { "room_id": 1 },
    "is_read": false,
    "created_at": "2026-05-09T10:35:00Z"
  }
}
```

## Deployment

### Using Docker

1. Build image:
```bash
docker build -t mindconnect-backend .
```

2. Run with docker-compose:
```bash
docker-compose up -d
```

### Manual Deployment (Render / Railway)

1. **Environment Variables** (set in dashboard):
   - `DATABASE_URL` (Supabase connection)
   - `SECRET_KEY` (generate via Django)
   - `DEBUG=False`
   - `REDIS_URL` (Redis cloud service)
   - `SUPABASE_*` keys

2. **Commands**:
```bash
python manage.py collectstatic --noinput
python manage.py migrate

# Use Daphne for ASGI (WebSocket support)
daphne backend.asgi:application --port $PORT --bind 0.0.0.0
```

3. **Add PostgreSQL & Redis add-ons** (if not using Supabase).

### Supabase Setup

1. Create Supabase project
2. Get connection details from **Settings → Database**
3. Enable **Storage** and create bucket `media-files`
4. Get API keys from **Settings → API**
5. Add to `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`

## Monitoring & Logs

### View Logs
```bash
# Django logs
tail -f logs/django.log

# Celery logs
celery -A backend worker -l info

# Redis monitoring
redis-cli monitor
```

### Admin Dashboard
Access at `http://localhost:8000/admin/` for:
- User management (ban, unban)
- Room monitoring
- Message audit
- Analytics

## Testing

```bash
# Run tests
python manage.py test users
python manage.py test chat
python manage.py test notifications

# With coverage
coverage run --source='.' manage.py test
coverage report
```

## Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Django secret key | Yes | - |
| `DEBUG` | Debug mode | No | True |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `REDIS_URL` | Redis connection string | Yes | redis://localhost:6379 |
| `JWT_SECRET` | JWT signing secret | Yes | - |
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_ANON_KEY` | Supabase anon key | Yes | - |
| `SUPABASE_SERVICE_KEY` | Supabase service key | Yes | - |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | No | localhost:3000 |

## Performance Considerations

- **Database Indexes** on frequently queried fields (user_id, room_id, created_at)
- **Redis Caching** for hot data (user presence, room lists)
- **Connection Pooling** (CONN_MAX_AGE=600)
- **Pagination** on all list endpoints (default 20 items)
- **Select Related/Prefetch** to minimize DB queries
- **WebSocket Groups** for efficient broadcasts

## Security

- JWT tokens stored in `HttpOnly` cookies (preferred) or local storage
- Rate limiting on auth endpoints
- Password validation (Django validators)
- File upload validation (size, MIME, extension)
- HTTPS enforced in production
- CSRF protection enabled

## Development Roadmap

### Phase 1 ✅ - Foundation & Configuration
- Environment setup
- Database configuration
- Redis integration
- Custom User model
- Core models (Room, Message, Notification)

### Phase 2 - Real-Time Messaging
- WebSocket consumers
- Typing indicators
- Message delivery receipts
- Presence system

### Phase 3 - Advanced Features
- File uploads (Supabase Storage)
- Search (full-text PostgreSQL)
- Push notifications (Firebase)
- Group management

### Phase 4 - Production
- Docker deployment
- CI/CD setup
- Monitoring (Sentry, Prometheus)
- Load testing

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions, please open an issue on GitHub.

---

**Built with Django, Real-Time with Channels, Powered by Supabase.**
