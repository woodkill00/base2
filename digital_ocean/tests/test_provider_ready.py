from __future__ import annotations

from types import SimpleNamespace

import pytest
from azure.core.exceptions import ServiceRequestError, ServiceResponseError

from digital_ocean.scripts.python.provider_ready import (
    ProviderReadyError,
    wait_for_active_public_ipv4,
)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def client_with(sequence):
    values = iter(sequence)

    def get(_droplet_id):
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return {"droplet": value}

    return SimpleNamespace(droplets=SimpleNamespace(get=get))


def address(droplet):
    return droplet.get("address")


@pytest.mark.parametrize(
    ("timeout_sec", "interval_sec"),
    ((0, 1), (1, 0)),
)
def test_rejects_invalid_polling_bounds(timeout_sec, interval_sec):
    clock = Clock()
    with pytest.raises(ProviderReadyError, match="bounds_invalid"):
        wait_for_active_public_ipv4(
            client_with([]),
            7,
            timeout_sec=timeout_sec,
            interval_sec=interval_sec,
            address_reader=address,
            clock=clock,
            sleeper=clock.sleep,
        )


def test_non_object_provider_response_is_bounded_and_sanitized():
    clock = Clock()
    with pytest.raises(ProviderReadyError, match="transport_or_contract"):
        wait_for_active_public_ipv4(
            client_with(["not-an-object"] * 2),
            7,
            timeout_sec=1,
            interval_sec=1,
            address_reader=address,
            clock=clock,
            sleeper=clock.sleep,
        )


def test_waits_for_active_and_address_under_one_deadline():
    clock = Clock()
    result = wait_for_active_public_ipv4(
        client_with(
            [
                {"status": "new", "address": None},
                {"status": "active", "address": None},
                {"status": "active", "address": "192.0.2.10"},
            ]
        ),
        7,
        timeout_sec=10,
        interval_sec=2,
        address_reader=address,
        clock=clock,
        sleeper=clock.sleep,
    )
    assert result[0] == "192.0.2.10"
    assert clock.now == 4


def test_perpetual_new_is_bounded():
    clock = Clock()
    values = [{"status": "new", "address": None}] * 4
    with pytest.raises(ProviderReadyError, match="provider_ready_timeout"):
        wait_for_active_public_ipv4(
            client_with(values),
            7,
            timeout_sec=3,
            interval_sec=1,
            address_reader=address,
            clock=clock,
            sleeper=clock.sleep,
        )
    assert clock.now == 3


@pytest.mark.parametrize("state", ("off", "archive", "error", "failed", "deleted"))
def test_terminal_provider_states_fail_immediately(state):
    clock = Clock()
    with pytest.raises(ProviderReadyError, match=f"terminal_state:{state}"):
        wait_for_active_public_ipv4(
            client_with([{"status": state, "address": None}]),
            7,
            timeout_sec=10,
            address_reader=address,
            clock=clock,
            sleeper=clock.sleep,
        )
    assert clock.now == 0


@pytest.mark.parametrize(
    "error_type",
    (OSError, ServiceRequestError, ServiceResponseError),
)
def test_transport_failure_sequence_is_bounded_and_sanitized(error_type):
    clock = Clock()
    secret = "provider-secret-must-not-escape"
    with pytest.raises(ProviderReadyError, match="transport_or_contract") as error:
        wait_for_active_public_ipv4(
            client_with([error_type(secret)] * 4),
            7,
            timeout_sec=3,
            interval_sec=1,
            address_reader=address,
            clock=clock,
            sleeper=clock.sleep,
        )
    assert secret not in str(error.value)
