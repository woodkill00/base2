import os

from django.contrib.auth.hashers import PBKDF2PasswordHasher

_DEFAULT_PBKDF2_ITERATIONS = int(getattr(PBKDF2PasswordHasher, "iterations", 0) or 0)


class PBKDF2TunablePasswordHasher(PBKDF2PasswordHasher):
    # Enforce a minimum of Django's default iterations.
    # You may increase iterations via DJANGO_PBKDF2_ITERATIONS, but never decrease.
    _env_iterations = int(
        os.environ.get(
            "DJANGO_PBKDF2_ITERATIONS",
            str(_DEFAULT_PBKDF2_ITERATIONS),
        )
        or _DEFAULT_PBKDF2_ITERATIONS
    )
    iterations = max(_DEFAULT_PBKDF2_ITERATIONS, _env_iterations)
