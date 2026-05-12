"""
Database optimization migration file.
Adds indexes, partitioning support, and full-text search.
"""

from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex, BrinIndex
from django.contrib.postgres.search import SearchVectorField


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_messagereaction_pinnedmessage'),
        ('users', '0003_add_avatar_url_field'),
    ]

    operations = [
        # Add full-text search capabilities
        migrations.RunSQL(
            sql="""
            ALTER TABLE chat_message 
            ADD COLUMN IF NOT EXISTS search_vector tsvector 
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(content, '')), 'A')
            ) STORED;
            """,
            reverse_sql="""
            ALTER TABLE chat_message DROP COLUMN IF EXISTS search_vector;
            """
        ),
        
        # Create GIN index for full-text search
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS chat_message_search_idx 
            ON chat_message USING GIN (search_vector);
            """,
            reverse_sql="DROP INDEX IF EXISTS chat_message_search_idx;"
        ),

        # Add composite indexes for common queries
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS chat_message_room_created_idx 
            ON chat_message (room_id, created_at DESC);
            
            CREATE INDEX IF NOT EXISTS chat_message_sender_room_idx 
            ON chat_message (sender_id, room_id, created_at DESC);
            
            CREATE INDEX IF NOT EXISTS chat_message_seen_idx 
            ON chat_message (room_id, is_seen, created_at);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS chat_message_room_created_idx;
            DROP INDEX IF EXISTS chat_message_sender_room_idx;
            DROP INDEX IF EXISTS chat_message_seen_idx;
            """
        ),

        # Add indexes for notifications
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS notifications_user_read_idx 
            ON notifications_notification (user_id, is_read, created_at DESC);
            
            CREATE INDEX IF NOT EXISTS notifications_type_idx 
            ON notifications_notification (type, created_at DESC);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS notifications_user_read_idx;
            DROP INDEX IF EXISTS notifications_type_idx;
            """
        ),

        # Add BRIN index for time-series data (older messages)
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS chat_message_brin_created 
            ON chat_message USING BRIN (created_at) 
            WITH (pages_per_range = 32);
            """,
            reverse_sql="DROP INDEX IF EXISTS chat_message_brin_created;"
        ),

        # Add partial index for unread messages
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS chat_unread_messages_idx 
            ON chat_message (room_id, created_at DESC) 
            WHERE is_seen = FALSE;
            """,
            reverse_sql="DROP INDEX IF EXISTS chat_unread_messages_idx;"
        ),
    ]