import os

import django


def ensure_superuser() -> bool:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.environ.get("DJANGO_SETTINGS_MODULE", "project.settings.production"),
    )
    django.setup()

    from django.contrib.auth import get_user_model

    username = os.getenv("DJANGO_SUPERUSER_NAME") or os.getenv("DJANGO_SUPERUSER_USERNAME")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

    if not (username and email and password):
        return False

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return True

    User.objects.create_superuser(username=username, email=email, password=password)
    return True


if __name__ == "__main__":
    try:
        created = ensure_superuser()
        print(f"ensure_superuser: {created}")
    except Exception as e:
        # Avoid crashing the container if creation fails (e.g., race during deploy)
        print(f"ensure_superuser error: {e}")