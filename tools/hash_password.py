#!/usr/bin/env python
"""Generate a bcrypt password hash to store in APP_PASSWORD in .env.

Usage:
    python hash_password.py
    python hash_password.py mysecretpassword
"""

import sys


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        import getpass

        password = getpass.getpass("Wachtwoord: ")
        confirm = getpass.getpass("Bevestig wachtwoord: ")
        if password != confirm:
            print("Wachtwoorden komen niet overeen.")
            sys.exit(1)

    from app.config import hash_password

    print(hash_password(password))


if __name__ == "__main__":
    main()
