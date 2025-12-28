import os


def test_production_password_hasher_is_not_reduced_iteration():
    # Ensure production settings can be imported without enabling staging/prod fail-fast.
    os.environ.setdefault("ENV", "development")

    from django.contrib.auth.hashers import PBKDF2PasswordHasher

    from project.password_hashers import PBKDF2TunablePasswordHasher
    from project.settings import production as prod

    assert prod.PASSWORD_HASHERS == [
        "project.password_hashers.PBKDF2TunablePasswordHasher",
    ]

    # Enforce that production hashing is at least Django's default PBKDF2 iterations.
    assert PBKDF2TunablePasswordHasher.iterations >= PBKDF2PasswordHasher.iterations
