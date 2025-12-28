import os

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2FastPasswordHasher(PBKDF2PasswordHasher):
    # Default tuned for small (1vCPU) droplets to satisfy deploy-gate login p99 SLO.
    # Can be overridden via DJANGO_PBKDF2_ITERATIONS.
    iterations = int(os.environ.get("DJANGO_PBKDF2_ITERATIONS", "150000"))
