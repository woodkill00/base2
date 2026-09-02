import pytest

from api.services.content_workspace_scanner import ScannerError, scan_content


class FakeSocket:
    def __init__(self, reply):
        self.reply = reply
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def sendall(self, value):
        self.sent.append(value)

    def recv(self, _size):
        reply, self.reply = self.reply, b''
        return reply


@pytest.mark.parametrize(
    ('reply', 'expected'),
    [(b'stream: OK\0', 'clean'), (b'stream: Eicar-Signature FOUND\0', 'infected')],
)
def test_clamav_instream_is_bounded_and_closed(reply, expected):
    fake = FakeSocket(reply)
    calls = []

    def connect(address, timeout):
        calls.append((address, timeout))
        return fake

    assert scan_content(b'synthetic', connector=connect) == expected
    assert calls == [(('clamav', 3310), 10.0)]
    assert fake.sent[0] == b'zINSTREAM\0'
    assert fake.sent[-1] == b'\x00\x00\x00\x00'
    assert b''.join(fake.sent[1:-1]).endswith(b'synthetic')


def test_scanner_rejects_untrusted_hosts_bad_replies_empty_and_oversize_content():
    for kwargs in (
        {'content': b'x', 'host': 'attacker.example'},
        {'content': b''},
        {'content': b'x' * (10 * 1024 * 1024 + 1)},
        {'content': b'x', 'connector': lambda *_args, **_kwargs: FakeSocket(b'unknown\0')},
    ):
        with pytest.raises(ScannerError):
            scan_content(**kwargs)


def test_scanner_network_failure_is_actionable_and_never_clean():
    def unavailable(*_args, **_kwargs):
        raise OSError('private detail')

    with pytest.raises(ScannerError, match='content_scanner_unavailable') as caught:
        scan_content(b'x', connector=unavailable)
    assert 'private detail' not in str(caught.value)
