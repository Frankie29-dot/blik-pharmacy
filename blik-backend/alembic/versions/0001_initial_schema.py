"""initial schema: customers, refill_requests, staff

Revision ID: 0001
Revises:
Create Date: 2026-11-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", "date_of_birth", name="uq_customers_phone_dob"),
    )

    op.create_table(
        "refill_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("prescription_number", sa.String(length=40), nullable=False),
        sa.Column(
            "method",
            sa.Enum("pickup", "delivery", name="refill_method", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "new", "preparing", "ready", "collected",
                name="refill_status", native_enum=False, create_constraint=True,
            ),
            server_default="new",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refill_requests_customer_id", "refill_requests", ["customer_id"])
    op.create_index("ix_refill_requests_status", "refill_requests", ["status"])

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("pharmacist", "assistant", name="staff_role", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_staff_email"),
    )


def downgrade() -> None:
    op.drop_table("staff")
    op.drop_index("ix_refill_requests_status", table_name="refill_requests")
    op.drop_index("ix_refill_requests_customer_id", table_name="refill_requests")
    op.drop_table("refill_requests")
    op.drop_table("customers")
