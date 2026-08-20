import os

import pytest

from aiofase import security


def test_generate_keypair_creates_key_files(tmp_path):
    public_file, secret_file = security.generate_keypair('svc', str(tmp_path))

    assert public_file == str(tmp_path / 'svc.key')
    assert secret_file == str(tmp_path / 'svc.key_secret')
    assert os.path.exists(public_file)
    assert os.path.exists(secret_file)


def test_generate_keypair_creates_missing_directory(tmp_path):
    out_dir = tmp_path / 'nested' / 'keys'
    assert not out_dir.exists()

    security.generate_keypair('svc', str(out_dir))

    assert out_dir.is_dir()


def test_load_keypair_from_secret_file_returns_both_keys(tmp_path):
    _, secret_file = security.generate_keypair('svc', str(tmp_path))

    public_key, secret_key = security.load_keypair(secret_file)

    assert public_key is not None
    assert secret_key is not None


def test_load_keypair_from_public_file_has_no_secret(tmp_path):
    public_file, _ = security.generate_keypair('svc', str(tmp_path))

    public_key, secret_key = security.load_keypair(public_file)

    assert public_key is not None
    assert secret_key is None


def test_cli_generates_keys_and_prints_paths(tmp_path, capsys):
    out_dir = tmp_path / 'keys'

    security.main(['--name', 'broker', '--out', str(out_dir)])

    captured = capsys.readouterr()
    assert str(out_dir / 'broker.key') in captured.out
    assert str(out_dir / 'broker.key_secret') in captured.out
    assert (out_dir / 'broker.key').exists()
    assert (out_dir / 'broker.key_secret').exists()


def test_cli_short_flags(tmp_path, capsys):
    out_dir = tmp_path / 'keys'

    security.main(['-n', 'client', '-o', str(out_dir)])

    assert (out_dir / 'client.key').exists()
    assert (out_dir / 'client.key_secret').exists()


def test_cli_defaults_out_dir_to_keys(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)

    security.main(['--name', 'default_out'])

    assert (tmp_path / 'keys' / 'default_out.key').exists()


def test_cli_requires_name_argument():
    with pytest.raises(SystemExit):
        security.main(['--out', '/tmp/whatever'])
