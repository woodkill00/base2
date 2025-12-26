import os

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2FastPasswordHasher(PBKDF2PasswordHasher):
    iterations = int(os.environ.get("DJANGO_PBKDF2_ITERATIONS", "260000"))
