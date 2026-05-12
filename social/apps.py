from django.apps import AppConfig

class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social'

    def ready(self):
        # Create UserProfile on user creation via signal
        from django.db.models.signals import post_save
        from django.contrib.auth import get_user_model

        def create_profile(sender, instance, created, **kwargs):
            if created:
                from social.models import UserProfile
                UserProfile.objects.get_or_create(user=instance)

        User = get_user_model()
        post_save.connect(create_profile, sender=User)
