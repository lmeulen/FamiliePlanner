"""initial schema

Revision ID: a8b46995a372
Revises: 
Create Date: 2026-03-04 22:03:46.984571

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a8b46995a372'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables (idempotent) then apply schema fixes to existing DBs."""
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    # ── Create tables that don't exist yet ────────────────────────────────────
    # (skipped on existing installs that already have the tables)

    if 'family_members' not in existing:
        op.create_table(
            'family_members',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('color', sa.String(7), server_default='#4ECDC4'),
            sa.Column('avatar', sa.String(10), server_default='👤'),
        )

    if 'recurrence_series' not in existing:
        op.create_table(
            'recurrence_series',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('location', sa.String(200), server_default=''),
            sa.Column('all_day', sa.Boolean(), server_default='0'),
            sa.Column('member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('color', sa.String(7), server_default='#4ECDC4'),
            sa.Column('recurrence_type', sa.String(50), nullable=False),
            sa.Column('series_start', sa.Date(), nullable=False),
            sa.Column('series_end', sa.Date(), nullable=False),
            sa.Column('start_time_of_day', sa.Time(), nullable=False),
            sa.Column('end_time_of_day', sa.Time(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if 'agenda_events' not in existing:
        op.create_table(
            'agenda_events',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('location', sa.String(200), server_default=''),
            sa.Column('start_time', sa.DateTime(), nullable=False),
            sa.Column('end_time', sa.DateTime(), nullable=False),
            sa.Column('all_day', sa.Boolean(), server_default='0'),
            sa.Column('member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('color', sa.String(7), server_default='#4ECDC4'),
            sa.Column('series_id', sa.Integer(), sa.ForeignKey('recurrence_series.id', ondelete='CASCADE'), nullable=True),
            sa.Column('is_exception', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if 'task_lists' not in existing:
        op.create_table(
            'task_lists',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('color', sa.String(7), server_default='#4ECDC4'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if 'task_recurrence_series' not in existing:
        op.create_table(
            'task_recurrence_series',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('list_id', sa.Integer(), sa.ForeignKey('task_lists.id', ondelete='SET NULL'), nullable=True),
            sa.Column('member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('recurrence_type', sa.String(50), nullable=False),
            sa.Column('series_start', sa.Date(), nullable=False),
            sa.Column('series_end', sa.Date(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if 'tasks' not in existing:
        op.create_table(
            'tasks',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('done', sa.Boolean(), server_default='0'),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('list_id', sa.Integer(), sa.ForeignKey('task_lists.id', ondelete='SET NULL'), nullable=True),
            sa.Column('member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('series_id', sa.Integer(), sa.ForeignKey('task_recurrence_series.id', ondelete='CASCADE'), nullable=True),
            sa.Column('is_exception', sa.Boolean(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if 'meals' not in existing:
        op.create_table(
            'meals',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('date', sa.Date(), nullable=False, index=True),
            sa.Column('meal_type', sa.String(20), server_default='dinner'),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('recipe_url', sa.String(500), server_default=''),
            sa.Column('cook_member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    # ── Schema fixes for existing DBs (batch = safe for SQLite) ──────────────
    # These are no-ops if the tables were just created above with correct types.
    # On existing DBs they fix INTEGER → Boolean columns and add FK constraints.

    if 'agenda_events' in existing:
        with op.batch_alter_table('agenda_events', schema=None) as batch_op:
            batch_op.alter_column('is_exception',
                existing_type=sa.INTEGER(),
                type_=sa.Boolean(),
                existing_nullable=False,
                existing_server_default=sa.text('0'))
            batch_op.create_foreign_key('fk_agenda_events_series_id', 'recurrence_series', ['series_id'], ['id'], ondelete='CASCADE')

    if 'meals' in existing:
        with op.batch_alter_table('meals', schema=None) as batch_op:
            batch_op.create_foreign_key('fk_meals_cook_member_id', 'family_members', ['cook_member_id'], ['id'], ondelete='SET NULL')

    if 'tasks' in existing:
        with op.batch_alter_table('tasks', schema=None) as batch_op:
            batch_op.alter_column('is_exception',
                existing_type=sa.INTEGER(),
                type_=sa.Boolean(),
                existing_nullable=False,
                existing_server_default=sa.text('0'))
            batch_op.create_foreign_key('fk_tasks_series_id', 'task_recurrence_series', ['series_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Revert schema fixes (does not drop tables to avoid data loss)."""
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tasks_series_id', type_='foreignkey')
        batch_op.alter_column('is_exception',
            existing_type=sa.Boolean(),
            type_=sa.INTEGER(),
            existing_nullable=False,
            existing_server_default=sa.text('0'))

    with op.batch_alter_table('meals', schema=None) as batch_op:
        batch_op.drop_constraint('fk_meals_cook_member_id', type_='foreignkey')

    with op.batch_alter_table('agenda_events', schema=None) as batch_op:
        batch_op.drop_constraint('fk_agenda_events_series_id', type_='foreignkey')
        batch_op.alter_column('is_exception',
            existing_type=sa.Boolean(),
            type_=sa.INTEGER(),
            existing_nullable=False,
            existing_server_default=sa.text('0'))

