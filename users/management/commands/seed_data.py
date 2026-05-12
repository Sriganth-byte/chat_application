"""
Management command: python manage.py seed_data

Seeds realistic demo data for testing all MindConnect features:
- 15 users with profiles
- Friendships + follows
- Posts with hashtags, mentions, polls, media
- Scheduled posts
- Comments, likes, saves
- Stories + highlights
- Notifications
- Feature flags
- Chat rooms + messages
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

USERNAMES = [
    'alice_j', 'bob_dev', 'carol_art', 'dave_photo', 'eve_writer',
    'frank_ml', 'grace_ux', 'heidi_yoga', 'ivan_chef', 'judy_travel',
    'kai_music', 'lena_code', 'mike_fitness', 'nina_reads', 'oscar_gamer',
]

BIOS = [
    'Building cool things on the internet 🚀', 'Photography & adventure seeker 📸',
    'Coffee-powered developer ☕', 'Spreading good vibes and good code 🌟',
    'Nature lover | Writer | Dreamer ✨', 'Machine learning enthusiast 🤖',
    'UX designer making the world more usable 🎨', 'Yoga & mindfulness coach 🧘',
    'Home chef sharing daily recipes 🍳', 'Traveling the world one city at a time 🌍',
    'Music producer | Beat maker 🎵', 'Full-stack developer & open source contributor 💻',
    'Fitness trainer | Nutrition nerd 💪', 'Bookworm & coffee snob 📚',
    'Gamer & streamer | Level 99 🎮',
]

HASHTAGS_POOL = [
    'mindconnect', 'coding', 'webdev', 'python', 'javascript', 'react',
    'design', 'ux', 'photography', 'travel', 'food', 'fitness', 'music',
    'books', 'gaming', 'ai', 'machinelearning', 'startup', 'innovation',
    'wellness', 'yoga', 'nature', 'coffee', 'motivation', 'technology',
]

POST_TEMPLATES = [
    ("Just deployed a new feature to production 🎉 Zero downtime deploys are *chef's kiss* #{tag1} #{tag2}", []),
    ("Morning run done ✅ 5km in 24 minutes. The dedication to health is real! #{tag1} #{tag2}", []),
    ("Reading '{book}' and my mind is blown 🤯 Highly recommend to anyone interested in #{tag1}", []),
    ("Tried a new recipe today — {food} from scratch! Turned out amazing 😍 #{tag1} #{tag2}", []),
    ("Hot take: {opinion} #{tag1} #{tag2} What do you think?", []),
    ("Day {n} of learning {skill}. Progress is slow but steady 🐢 #{tag1}", []),
    ("Sometimes the best code is the code you don't write 🧠 #{tag1} #{tag2}", []),
    ("Exploring {city} today. The architecture here is incredible 🏛️ #{tag1} #{tag2}", []),
    ("New personal record at the gym today 💪 Hard work pays off! #{tag1} #{tag2}", []),
    ("Coffee shop coding session: productive or just vibes? ☕ #{tag1}", []),
    ("Finished migrating our entire database to PostgreSQL. Lessons learned:\n1. Always test migrations\n2. Backups save lives\n3. Document everything #{tag1} #{tag2}", []),
    ("The gap between a junior and senior developer isn't just technical skill — it's pattern recognition, communication, and knowing when NOT to code. #{tag1} #{tag2}", []),
    ("UI tip: White space is not empty space. It's breathing room for your content. Use it generously! #{tag1} #{tag2}", []),
    ("Just discovered that {feature} in {tech} and I've been doing it the hard way for 2 years 😭 #{tag1}", []),
    ("Community question: What's your favorite productivity hack? Drop it below! 👇 #{tag1}", []),
]

BOOKS = ['Atomic Habits', 'The Pragmatic Programmer', 'Deep Work', 'Clean Code', 'Dune', 'The Lean Startup']
FOODS = ['pasta carbonara', 'sourdough bread', 'sushi', 'Thai curry', 'chocolate lava cake', 'shakshuka']
OPINIONS = [
    'tabs > spaces', 'dark mode is superior', 'TypeScript is worth the overhead',
    'documentation should come before code', 'monorepos are underrated',
]
SKILLS = ['Rust', 'Go', 'Kubernetes', 'GraphQL', 'system design', 'machine learning']
CITIES = ['Tokyo', 'Amsterdam', 'Lisbon', 'Melbourne', 'Barcelona', 'Kyoto', 'Cape Town']
TECHS = ['Python 3.12', 'React 19', 'Django 5', 'Vite', 'Next.js 14']
FEATURES = ['walrus operator', 'match statements', 'async generators', 'structural pattern matching']

COMMENTS = [
    "This is exactly what I needed to hear today! 🙌",
    "Great point! Have you tried combining this with {related}?",
    "Totally agree! I had the same experience last month.",
    "Thanks for sharing! Can you elaborate more on the implementation?",
    "Love this perspective 💯",
    "Bookmarked for later reading 📌",
    "This community is amazing — always learning something new here",
    "Incredible work! Keep it up 🔥",
    "I've been thinking about this too! Let's collaborate!",
    "The real MVP right here 👏",
]


def rand_hashtags(n=2):
    return random.sample(HASHTAGS_POOL, n)


def make_post_content():
    tpl = random.choice(POST_TEMPLATES)[0]
    tags = rand_hashtags(2)
    return tpl.format(
        tag1=tags[0], tag2=tags[1] if len(tags) > 1 else tags[0],
        book=random.choice(BOOKS), food=random.choice(FOODS),
        opinion=random.choice(OPINIONS), n=random.randint(1, 30),
        skill=random.choice(SKILLS), city=random.choice(CITIES),
        tech=random.choice(TECHS), feature=random.choice(FEATURES),
        related=random.choice(HASHTAGS_POOL),
    )


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data for testing'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing seed data first')
        parser.add_argument('--users', type=int, default=15, help='Number of demo users')

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== MindConnect Seed Data Generator ===\n'))

        if options['clear']:
            self.stdout.write('🧹 Clearing existing demo data...')
            User.objects.filter(username__in=USERNAMES).delete()

        # ── 1. Create users ──────────────────────────────────────────
        self.stdout.write('👤 Creating users...')
        users = []
        for i, username in enumerate(USERNAMES[:options['users']]):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@demo.mindconnect.app',
                    'first_name': username.split('_')[0].title(),
                    'last_name': 'Demo',
                    'bio': BIOS[i],
                    'is_verified': random.random() > 0.7,
                    'email_verified': True,
                }
            )
            if created:
                user.set_password('Demo@123!')
                user.save()
                if user.is_verified:
                    user.verified_at = timezone.now() - timedelta(days=random.randint(1, 90))
                    user.save(update_fields=['verified_at'])
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(users)} users created'))

        # ── 2. Create admin superuser ────────────────────────────────
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@mindconnect.com',
                'is_staff': True,
                'is_superuser': True,
                'email_verified': True,
                'is_verified': True,
            }
        )
        if not admin.has_usable_password():
            admin.set_password('Admin@123!')
            admin.save()
        self.stdout.write(self.style.SUCCESS('  ✓ Admin user ready (admin / Admin@123!)'))

        # ── 3. Social graph ──────────────────────────────────────────
        self.stdout.write('👥 Building social graph...')
        from social.models import Friendship, Follow, FriendRequest, UserProfile

        # Create user profiles
        for user in users:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': user.first_name,
                    'bio': user.bio,
                    'location': random.choice(['San Francisco', 'London', 'Berlin', 'Tokyo', 'Sydney', 'New York']),
                    'website': f'https://{user.username}.dev',
                    'theme': random.choice(['dark', 'light']),
                }
            )

        # Create friendships (each user friends with 3-6 others)
        friendship_count = 0
        for user in users:
            potential_friends = [u for u in users if u != user]
            friends_to_add = random.sample(potential_friends, min(4, len(potential_friends)))
            for friend in friends_to_add:
                u1, u2 = (user, friend) if user.id < friend.id else (friend, user)
                _, created = Friendship.objects.get_or_create(user1=u1, user2=u2)
                if created:
                    friendship_count += 1

        # Create follows
        follow_count = 0
        for user in users:
            to_follow = random.sample([u for u in users if u != user], min(6, len(users) - 1))
            for target in to_follow:
                _, created = Follow.objects.get_or_create(follower=user, following=target)
                if created:
                    follow_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {friendship_count} friendships, {follow_count} follows'))

        # ── 4. Create posts ──────────────────────────────────────────
        self.stdout.write('📝 Creating posts...')
        from posts.models import Post, PostLike, PostComment, PostSave, Poll, PollOption, SavedCollection
        import re

        posts = []
        for user in users:
            num_posts = random.randint(5, 12)
            for j in range(num_posts):
                content = make_post_content()
                hashtags = re.findall(r'#(\w+)', content)
                days_ago = random.randint(0, 90)
                post = Post(
                    author=user,
                    content=content,
                    visibility=random.choice(['public', 'public', 'public', 'friends']),
                    status='published',
                    hashtags=hashtags,
                    likes_count=0,
                    comments_count=0,
                    views_count=random.randint(10, 500),
                )
                posts.append(post)

        Post.objects.bulk_create(posts, batch_size=50)
        # Fetch created posts with IDs
        all_posts = list(Post.objects.filter(author__in=users).order_by('-created_at'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(all_posts)} posts created'))

        # ── 5. Add scheduled posts ────────────────────────────────────
        for user in random.sample(users, 3):
            Post.objects.create(
                author=user,
                content=f"📅 Excited to share something with everyone soon! #{random.choice(HASHTAGS_POOL)} #scheduled",
                visibility='public',
                status='scheduled',
                publish_at=timezone.now() + timedelta(hours=random.randint(1, 48)),
                hashtags=['scheduled', random.choice(HASHTAGS_POOL)],
            )
        self.stdout.write(self.style.SUCCESS('  ✓ 3 scheduled posts created'))

        # ── 6. Add a poll post ────────────────────────────────────────
        for user in random.sample(users, 3):
            poll_post = Post.objects.create(
                author=user,
                content=f"Quick poll for the community! 🗳️ #mindconnect",
                visibility='public',
                status='published',
                hashtags=['mindconnect'],
            )
            poll = Poll.objects.create(
                post=poll_post,
                question=random.choice([
                    'What programming language should I learn next?',
                    'Best time to post on social media?',
                    'Tabs or spaces?',
                    'Dark mode or light mode?',
                    'Coffee or Tea for coding sessions?',
                ]),
            )
            options_text = random.choice([
                ['Python', 'Rust', 'Go', 'TypeScript'],
                ['Morning', 'Afternoon', 'Evening', 'Late night'],
                ['Tabs', 'Spaces', 'Both are fine', 'Fight me'],
                ['Dark 🌙', 'Light ☀️', 'System default', 'Depends on mood'],
                ['Coffee ☕', 'Tea 🍵', 'Energy drinks ⚡', 'Just water'],
            ])
            for i, opt in enumerate(options_text):
                PollOption.objects.create(poll=poll, text=opt, order=i)
        self.stdout.write(self.style.SUCCESS('  ✓ 3 poll posts created'))

        # ── 7. Likes + comments ───────────────────────────────────────
        self.stdout.write('❤️  Adding likes and comments...')
        like_count = 0
        comment_count = 0
        sample_posts = random.sample(all_posts, min(len(all_posts), 60))

        for post in sample_posts:
            likers = random.sample(users, random.randint(0, min(8, len(users))))
            for liker in likers:
                if liker != post.author:
                    PostLike.objects.get_or_create(post=post, user=liker)
                    like_count += 1

            commenters = random.sample(users, random.randint(0, 3))
            for commenter in commenters:
                PostComment.objects.create(
                    post=post,
                    author=commenter,
                    content=random.choice(COMMENTS).replace('{related}', random.choice(HASHTAGS_POOL)),
                )
                comment_count += 1

        # Update denormalized counts
        for post in all_posts:
            Post.objects.filter(id=post.id).update(
                likes_count=post.likes.count(),
                comments_count=post.comments.count(),
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {like_count} likes, {comment_count} comments'))

        # ── 8. Saved collections + saves ─────────────────────────────
        self.stdout.write('🔖 Creating saved collections...')
        collection_names = ['Inspiration', 'Code Tips', 'Travel Goals', 'Recipes', 'For Later']
        for user in random.sample(users, 6):
            for cname in random.sample(collection_names, 2):
                SavedCollection.objects.get_or_create(
                    owner=user, name=cname,
                    defaults={'emoji': random.choice(['⭐', '📌', '🔖', '💡', '🌟']), 'is_private': True}
                )
            # Save some posts
            to_save = random.sample(all_posts, min(5, len(all_posts)))
            from posts.models import PostSave
            for p in to_save:
                PostSave.objects.get_or_create(post=p, user=user)
        self.stdout.write(self.style.SUCCESS('  ✓ Saved collections created'))

        # ── 9. Stories + Highlights ───────────────────────────────────
        self.stdout.write('📖 Creating stories and highlights...')
        from stories.models import Story, StoryHighlight

        stories_created = 0
        for user in users:
            for _ in range(random.randint(1, 3)):
                story = Story.objects.create(
                    author=user,
                    media_type='text',
                    text_content=random.choice([
                        'Living my best life ✨', 'Code. Coffee. Repeat ☕',
                        'Good vibes only 🌈', 'Building something amazing 🚀',
                        'Be yourself 💫', 'Today was a great day 🌟',
                    ]),
                    bg_color=random.choice(['#6c63ff', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#8b5cf6']),
                    text_color='#ffffff',
                    expires_at=timezone.now() + timedelta(hours=random.randint(1, 24)),
                )
                stories_created += 1

            # Create a highlight for some users
            if random.random() > 0.5:
                user_stories = Story.objects.filter(author=user)
                if user_stories.exists():
                    h = StoryHighlight.objects.create(
                        owner=user,
                        title=random.choice(['Highlights', 'Best of', 'My Journey', 'Daily Life', 'Work']),
                    )
                    h.stories.set(user_stories)
                    h.cover_story = user_stories.first()
                    h.save()

        self.stdout.write(self.style.SUCCESS(f'  ✓ {stories_created} stories, highlights created'))

        # ── 10. Notifications ─────────────────────────────────────────
        self.stdout.write('🔔 Creating notifications...')
        from notifications.models import Notification
        notif_types = ['post_like', 'post_comment', 'new_follower', 'friend_request', 'system']
        notif_msgs = {
            'post_like': 'liked your post',
            'post_comment': 'commented on your post',
            'new_follower': 'started following you',
            'friend_request': 'sent you a friend request',
            'system': 'Welcome to MindConnect! 🎉 Start by completing your profile.',
        }
        for user in users:
            for _ in range(random.randint(3, 8)):
                ntype = random.choice(notif_types)
                actor = random.choice([u for u in users if u != user])
                Notification.objects.create(
                    user=user,
                    type=ntype,
                    message=f'{actor.username} {notif_msgs[ntype]}',
                    is_read=random.random() > 0.4,
                    data={'user_id': actor.id},
                )
        self.stdout.write(self.style.SUCCESS('  ✓ Notifications created'))

        # ── 11. Feature flags ─────────────────────────────────────────
        self.stdout.write('🚩 Creating feature flags...')
        from users.models import FeatureFlag
        flags = [
            ('ai_hashtag_suggestions', 'AI-powered hashtag suggestions in PostComposer', True, 100),
            ('scheduled_posts', 'Allow users to schedule posts for future publishing', True, 100),
            ('story_highlights', 'Story highlights on user profiles', True, 100),
            ('post_analytics', 'Analytics dashboard for post creators', True, 50),
            ('voice_messages', 'Voice message recording in chat', False, 0),
            ('ai_moderation', 'AI content moderation (toxicity filter)', False, 0),
            ('push_notifications', 'Browser push notifications', True, 100),
            ('saved_collections', 'Organize saved posts into named folders', True, 100),
            ('verified_badges', 'Show verification badges on profiles', True, 100),
        ]
        for name, desc, enabled, pct in flags:
            FeatureFlag.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'is_enabled': enabled, 'rollout_percentage': pct}
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(flags)} feature flags created'))

        # ── 12. Chat rooms + messages ─────────────────────────────────
        self.stdout.write('💬 Creating chat rooms and messages...')
        try:
            from chat.models import Room, Message
            # Public rooms
            room_names = ['General 💬', 'Tech Talk 💻', 'Creative Corner 🎨', 'Off Topic 🎲', 'Introductions 👋']
            for rname in room_names:
                room, created = Room.objects.get_or_create(
                    name=rname,
                    defaults={'room_type': 'group', 'created_by': admin}
                )
                # Add some messages
                if created:
                    sample_users = random.sample(users, min(5, len(users)))
                    for user in sample_users:
                        for _ in range(random.randint(1, 4)):
                            Message.objects.create(
                                room=room,
                                sender=user,
                                content=random.choice([
                                    'Hey everyone! 👋',
                                    f'Just finished working on something cool with #{random.choice(HASHTAGS_POOL)}',
                                    'Who else is up late coding? 🌙',
                                    'Anyone have recommendations for learning resources?',
                                    'Great community here! Love the vibes 🙌',
                                ]),
                            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ {len(room_names)} chat rooms with messages'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Chat seeding skipped: {e}'))

        # ── 13. Post analytics snapshots ──────────────────────────────
        self.stdout.write('📊 Creating analytics snapshots...')
        from posts.models import PostAnalytics
        from datetime import date
        sample_for_analytics = random.sample(all_posts, min(20, len(all_posts)))
        analytics_count = 0
        for post in sample_for_analytics:
            for days_ago in range(0, 14):
                d = date.today() - timedelta(days=days_ago)
                views = random.randint(5, 200)
                PostAnalytics.objects.get_or_create(
                    post=post, date=d,
                    defaults={
                        'views': views,
                        'impressions': views * random.randint(2, 5),
                        'likes': random.randint(0, 20),
                        'comments': random.randint(0, 8),
                        'shares': random.randint(0, 5),
                        'saves': random.randint(0, 3),
                        'reach': random.randint(views // 2, views),
                    }
                )
                analytics_count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {analytics_count} analytics data points'))

        # ── Summary ───────────────────────────────────────────────────
        self.stdout.write('\n' + '═' * 55)
        self.stdout.write(self.style.SUCCESS('✅ Seed data complete!\n'))
        self.stdout.write(f'  👤 Users:        {User.objects.count()} total')
        self.stdout.write(f'  📝 Posts:        {Post.objects.count()} total')
        self.stdout.write(f'  💬 Demo logins:  username@demo.mindconnect.app / Demo@123!')
        self.stdout.write(f'  🔑 Admin:        admin / Admin@123!')
        self.stdout.write(f'  🌐 App:          http://localhost:3000')
        self.stdout.write(f'  🛡️  Admin panel:  http://localhost:8000/admin/')
        self.stdout.write(f'  📊 API Docs:     http://localhost:8000/api/docs/')
        self.stdout.write('═' * 55 + '\n')
