import pytest
from celery import Celery

from api.tasks import app as celery_app


pytestmark = [pytest.mark.integration]


def test_celery_add_runs_quickly():
    assert isinstance(celery_app, Celery)
    res = celery_app.send_task("base2.add", args=[2, 3])
    out = res.get(timeout=10)
    assert out == 5
