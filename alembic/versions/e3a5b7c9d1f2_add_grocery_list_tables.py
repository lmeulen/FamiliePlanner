"""add grocery list tables

Revision ID: e3a5b7c9d1f2
Revises: d4f9c1a2b7e3
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3a5b7c9d1f2"
down_revision: Union[str, Sequence[str], None] = "d4f9c1a2b7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create grocery_categories table
    op.create_table(
        "grocery_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=10), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#9EA7C4"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_grocery_categories_id"), "grocery_categories", ["id"], unique=False)

    # Create grocery_items table
    op.create_table(
        "grocery_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.String(length=50), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("checked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["grocery_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_grocery_items_category_id"), "grocery_items", ["category_id"], unique=False)
    op.create_index(op.f("ix_grocery_items_checked"), "grocery_items", ["checked"], unique=False)
    op.create_index(op.f("ix_grocery_items_id"), "grocery_items", ["id"], unique=False)
    op.create_index(op.f("ix_grocery_items_product_name"), "grocery_items", ["product_name"], unique=False)

    # Create grocery_product_learning table
    op.create_table(
        "grocery_product_learning",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_used", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["category_id"], ["grocery_categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_name"),
    )
    op.create_index(op.f("ix_grocery_product_learning_id"), "grocery_product_learning", ["id"], unique=False)
    op.create_index(
        op.f("ix_grocery_product_learning_product_name"), "grocery_product_learning", ["product_name"], unique=True
    )

    # Seed default categories
    op.execute(
        """
        INSERT INTO grocery_categories (name, icon, sort_order, color) VALUES
        ('Groente & Fruit', '🥬', 10, '#4CAF50'),
        ('Brood & Bakkerij', '🍞', 20, '#FF9800'),
        ('Zuivel', '🥛', 30, '#2196F3'),
        ('Vlees & Vis', '🥩', 40, '#F44336'),
        ('Kaas & Vleeswaren', '🧀', 50, '#FFC107'),
        ('Conserven & Sauzen', '🥫', 60, '#795548'),
        ('Pasta & Rijst', '🍝', 70, '#FFEB3B'),
        ('Koek & Snoep', '🍪', 80, '#E91E63'),
        ('Diepvries', '🧊', 90, '#00BCD4'),
        ('Non-food', '🧴', 100, '#9E9E9E'),
        ('Overig', '❓', 110, '#9EA7C4')
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_grocery_product_learning_product_name"), table_name="grocery_product_learning")
    op.drop_index(op.f("ix_grocery_product_learning_id"), table_name="grocery_product_learning")
    op.drop_table("grocery_product_learning")

    op.drop_index(op.f("ix_grocery_items_product_name"), table_name="grocery_items")
    op.drop_index(op.f("ix_grocery_items_id"), table_name="grocery_items")
    op.drop_index(op.f("ix_grocery_items_checked"), table_name="grocery_items")
    op.drop_index(op.f("ix_grocery_items_category_id"), table_name="grocery_items")
    op.drop_table("grocery_items")

    op.drop_index(op.f("ix_grocery_categories_id"), table_name="grocery_categories")
    op.drop_table("grocery_categories")
