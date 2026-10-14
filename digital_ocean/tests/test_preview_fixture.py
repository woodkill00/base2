import pytest

from digital_ocean.scripts.python.preview_fixture import fixture_identity, main


@pytest.mark.parametrize("revision", ["", "-r1", "-r99"])
def test_shared_fixture_identity(revision):
    assert (
        fixture_identity("base2-full-20261014-010203", revision)
        == "base2-full-20261014-010203" + revision
    )


@pytest.mark.parametrize("revision", ["-r0", "-r100", "../x", "\n-r1", "-r01", "-r1/secret"])
def test_hostile_revision_rejected(revision):
    with pytest.raises(ValueError):
        fixture_identity("base2-full-20261014-010203", revision)


def test_invalid_run_and_cli(capsys):
    with pytest.raises(ValueError):
        fixture_identity("../run")
    assert main(["--run-id", "base2-full-20261014-010203", "--revision=-r1"]) == 0
    assert capsys.readouterr().out.strip() == "base2-full-20261014-010203-r1"
