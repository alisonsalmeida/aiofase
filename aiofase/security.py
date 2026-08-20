from argparse import ArgumentParser
from typing import Optional, Tuple

import os
import zmq.auth


def generate_keypair(name: str, directory: str) -> Tuple[str, str]:
    """Generate a CURVE keypair for `name` inside `directory`.

    Returns (public_key_file, secret_key_file). The secret file contains both
    keys and must never be shared or committed to version control.
    """
    os.makedirs(directory, exist_ok=True)
    return zmq.auth.create_certificates(directory, name)


def load_keypair(cert_file: str) -> Tuple[bytes, Optional[bytes]]:
    """Load a CURVE keypair from a `.key` or `.key_secret` file.

    Returns (public_key, secret_key). `secret_key` is None when `cert_file`
    is a public-only `.key` file.
    """
    return zmq.auth.load_certificate(cert_file)


def main(argv=None):
    parser = ArgumentParser(description='Generate a CURVE keypair for aiofase')
    parser.add_argument('-n', '--name', action='store', dest='name', required=True)
    parser.add_argument('-o', '--out', action='store', dest='out', default='./keys')

    args = parser.parse_args(argv)

    public_file, secret_file = generate_keypair(args.name, args.out)
    print(f'public key file: {public_file}')
    print(f'secret key file: {secret_file} (keep this private, never commit it)')


if __name__ == '__main__':
    main()
