"""
Scheduled posts Celery task + full tasks.py update.
"""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


# ─── Scheduled Posts ───────────────────────────────────────────────────────────
@shared_task(name='posts.publish_scheduled')
def publish_scheduled_posts():
    """
    Publish posts whose publish_at <= now and status == 'scheduled'.
    Run every minute via Celery Beat.
    """
    from posts.models import Post
    now = timezone.now()
    due = Post.objects.filter(status='scheduled', publish_at__lte=now)
    count = due.count()
    due.update(status='published')

    if count:
        logger.info(f'Published {count} scheduled posts')
        # Notify authors
        for post in Post.objects.filter(
            status='published', publish_at__lte=now, publish_at__gte=now - timezone.timedelta(seconds=70)
        ):
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=post.author,
                    type='system',
                    message=f'📅 Your scheduled post has been published!',
                    data={'post_id': post.id}
                )
            except Exception:
                pass
    return {'published': count}


# ─── Stories cleanup ───────────────────────────────────────────────────────────
@shared_task(name='stories.cleanup_expired')
def cleanup_expired_stories():
    from stories.models import Story
    cutoff = timezone.now()
    deleted, _ = Story.objects.filter(expires_at__lt=cutoff).delete()
    logger.info(f'Cleaned up {deleted} expired stories')
    return {'deleted': deleted}


# ─── Email notifications ───────────────────────────────────────────────────────
@shared_task(name='users.send_missed_message_email', bind=True, max_retries=3)
def send_missed_message_email(self, user_id, sender_username, room_name, message_preview):
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from django.conf import settings
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        if user.is_online:
            return
        send_mail(
            subject=f'New message from {sender_username} on MindConnect',
            message=f'You have a new message in {room_name}:\n\n"{message_preview}"\n\nOpen MindConnect to reply.',
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mindconnect.app'),
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(name='users.send_notification_email')
def send_notification_email(user_id, subject, body):
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from django.conf import settings
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        send_mail(subject=subject, message=body,
                  from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mindconnect.app'),
                  recipient_list=[user.email], fail_silently=True)
    except Exception as e:
        logger.error(f'Notification email error: {e}')


@shared_task(name='users.send_weekly_digest')
def send_weekly_digest():
    from django.contrib.auth import get_user_model
    from notifications.models import Notification
    User = get_user_model()
    for user in User.objects.filter(is_active=True).exclude(email=''):
        unread = Notification.objects.filter(user=user, is_read=False).count()
        if unread == 0:
            continue
        send_notification_email.delay(
            user_id=user.id,
            subject='Your MindConnect Weekly Digest',
            body=f'Hi {user.username}!\n\nYou have {unread} unread notification{"s" if unread != 1 else ""}.'
        )


# ─── WebPush ──────────────────────────────────────────────────────────────────
@shared_task(name='users.send_push_notification')
def send_push_notification(user_id, title, body, url='/'):
    """Send Web Push notification to all active subscriptions for a user."""
    try:
        from users.models import WebPushSubscription
        from django.conf import settings
        from pywebpush import webpush, WebPushException
        import json

        subs = WebPushSubscription.objects.filter(user_id=user_id, is_active=True)
        if not subs.exists():
            return

        vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
        vapid_email = getattr(settings, 'VAPID_CLAIMS_EMAIL', 'mailto:admin@mindconnect.app')

        if not vapid_private:
            logger.warning('VAPID_PRIVATE_KEY not set — push notifications disabled')
            return

        payload = json.dumps({'title': title, 'body': body, 'url': url})

        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}
                    },
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={'sub': vapid_email},
                )
            except WebPushException as e:
                if '410' in str(e) or '404' in str(e):
                    sub.is_active = False
                    sub.save()
                logger.warning(f'Push failed for {sub.endpoint[:40]}: {e}')
    except Exception as e:
        logger.error(f'Push notification task error: {e}')


# ─── Feed cache ───────────────────────────────────────────────────────────────
@shared_task(name='posts.invalidate_feed_cache')
def invalidate_feed_cache(user_id):
    cache.delete(f'feed:{user_id}:page:1')


# ─── Mentions ─────────────────────────────────────────────────────────────────
@shared_task(name='posts.process_mentions')
def process_mentions(post_id):
    import re
    from posts.models import Post
    from notifications.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        post = Post.objects.select_related('author').get(id=post_id)
        mentions = re.findall(r'@(\w+)', post.content)
        for username in set(mentions):
            try:
                mentioned = User.objects.get(username=username)
                if mentioned == post.author:
                    continue
                Notification.objects.get_or_create(
                    user=mentioned, type='mention',
                    data={'post_id': post_id},
                    defaults={'message': f'{post.author.username} mentioned you in a post'}
                )
                # Also send push
                send_push_notification.delay(
                    mentioned.id,
                    f'{post.author.username} mentioned you',
                    post.content[:100],
                    f'/posts/{post_id}'
                )
            except User.DoesNotExist:
                pass
    except Exception as e:
        logger.warning(f'process_mentions error: {e}')


# ─── Link preview ─────────────────────────────────────────────────────────────
@shared_task(name='posts.fetch_link_preview')
def fetch_link_preview(post_id):
    import re
    from posts.models import Post
    try:
        post = Post.objects.get(id=post_id)
        if post.link_preview:
            return
        urls = re.findall(r'https?://[^\s]+', post.content)
        if not urls:
            return
        from posts.link_preview import _extract_og
        import urllib.request
        url = urls[0]
        req = urllib.request.Request(url, headers={'User-Agent': 'MindConnect/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read(50000).decode('utf-8', errors='ignore')
        preview = _extract_og(html, url)
        Post.objects.filter(id=post_id).update(link_preview=preview)
    except Exception as e:
        logger.warning(f'Link preview fetch failed for post {post_id}: {e}')


# ─── Post Analytics snapshot ──────────────────────────────────────────────────
@shared_task(name='posts.snapshot_analytics')
def snapshot_analytics():
    """Daily task: snapshot post analytics for all posts published in last 30 days."""
    from posts.models import Post, PostAnalytics, PostLike, PostComment, PostSave
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    cutoff = today - timedelta(days=30)
    posts = Post.objects.filter(created_at__date__gte=cutoff, status='published')

    for post in posts:
        PostAnalytics.objects.update_or_create(
            post=post, date=today,
            defaults={
                'views': post.views_count,
                'impressions': post.impressions_count,
                'likes': post.likes_count,
                'comments': post.comments_count,
                'shares': post.shares_count,
                'saves': post.saves.count(),
            }
        )
    logger.info(f'Snapshotted analytics for {posts.count()} posts')
    return {'posts': posts.count()}


# ─── Suspicious login alert ───────────────────────────────────────────────────
@shared_task(name='users.check_suspicious_login')
def check_suspicious_login(login_history_id):
    """Check if a new login is from an unusual location and alert the user."""
    try:
        from users.models import UserLoginHistory
        login = UserLoginHistory.objects.select_related('user').get(id=login_history_id)
        user = login.user

        # Check if we've seen this IP before
        known_ips = set(
            UserLoginHistory.objects.filter(user=user, is_suspicious=False)
            .exclude(id=login_history_id)
            .values_list('ip_address', flat=True)
        )

        if known_ips and login.ip_address not in known_ips:
            login.is_suspicious = True
            login.save(update_fields=['is_suspicious'])
            send_notification_email.delay(
                user.id,
                'New login from unfamiliar location — MindConnect',
                f'We noticed a new login to your account:\n\n'
                f'Location: {login.city or "Unknown"}, {login.country or "Unknown"}\n'
                f'Device: {login.device_type} ({login.browser_family})\n'
                f'IP: {login.ip_address}\n\n'
                f'If this was you, you can ignore this email.\n'
                f'If not, please change your password immediately.'
            )
    except Exception as e:
        logger.warning(f'Suspicious login check error: {e}')
