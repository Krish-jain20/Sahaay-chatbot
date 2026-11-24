"""Where LangGraph keeps conversation state.

With `DATABASE_URL` set (the Supabase Postgres connection string) state survives a restart. Without it
the in-memory saver is used, which is fine for local work and tests. State only ever holds masked text:
`run_turn` masks identity numbers before the message enters the graph, so nothing sensitive is checkpointed.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

log = logging.getLogger("sahaay.checkpoint")


class Checkpointer:
    def __init__(self, saver: Any, pool: Any | None = None) -> None:
        self.saver = saver
        self._pool = pool

    @property
    def persistent(self) -> bool:
        return self._pool is not None

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()


def make_checkpointer(database_url: str) -> Checkpointer:
    if not database_url:
        return Checkpointer(MemorySaver())
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    # autocommit + no prepared statements: required by LangGraph's saver and by Supabase's pooler.
    pool = ConnectionPool(
        conninfo=database_url,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    saver = PostgresSaver(pool)  # type: ignore[arg-type]
    saver.setup()  # creates its own tables on first run
    log.info("conversation state stored in Postgres")
    return Checkpointer(saver, pool)
