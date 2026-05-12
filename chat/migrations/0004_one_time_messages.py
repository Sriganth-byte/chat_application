from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_messagereaction_pinnedmessage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='one_time',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='one_time_read_by',
            field=models.ManyToManyField(blank=True, related_name='one_time_messages', to=settings.AUTH_USER_MODEL),
        ),
    ]
