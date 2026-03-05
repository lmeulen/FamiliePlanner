"""Shared database helpers used across routers."""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def set_junction_members(
    db: AsyncSession,
    junction_table,
    key_col: str,
    key_val: int,
    member_ids: list[int],
) -> None:
    """Replace all member associations for a junction table row."""
    try:
        await db.execute(junction_table.delete().where(junction_table.c[key_col] == key_val))
        if member_ids:
            await db.execute(
                junction_table.insert(),
                [{key_col: key_val, "member_id": mid} for mid in member_ids],
            )
        logger.debug(
            "set_junction_members table={} {}={} member_ids={}",
            junction_table.name, key_col, key_val, member_ids,
        )
    except Exception as exc:
        logger.error(
            "set_junction_members FAILED table={} {}={} member_ids={} error={}",
            junction_table.name, key_col, key_val, member_ids, exc,
        )
        raise
