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
            junction_table.name,
            key_col,
            key_val,
            member_ids,
        )
    except Exception as exc:
        logger.error(
            "Failed to update member junction rows; relation update aborted and caller transaction should be reviewed.",
            table=junction_table.name,
            key_column=key_col,
            key_value=key_val,
            member_ids=member_ids,
            error=str(exc),
        )
        raise
