"""Create a staff account.

Usage (from the project root, with the virtualenv active):

    python -m scripts.create_staff --email you@blikpharmacy.example --role pharmacist

The password is typed at a hidden prompt, so it never lands in your shell history.
Run it again to add more staff.
"""
import argparse
import getpass
import re
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Staff, StaffRole
from app.security import hash_password

MIN_PASSWORD_LENGTH = 10
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Blik Pharmacy staff account.")
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--role", choices=[r.value for r in StaffRole], default=StaffRole.pharmacist.value
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        sys.exit("That does not look like a valid email address.")

    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match.")

    with SessionLocal() as db:
        if db.scalar(select(Staff).where(Staff.email == email)) is not None:
            sys.exit(f"A staff account for {email} already exists.")
        db.add(Staff(email=email, password_hash=hash_password(password), role=StaffRole(args.role)))
        db.commit()

    print(f"Created {args.role} account for {email}.")


if __name__ == "__main__":
    main()
