"""A real MCP client to Alpaca's MCP server, started WITHOUT the trading toolset.

This is the boundary that matters. The practitioner researches through these
tools; it cannot place an order because the tools to do so are never loaded into
its session. That is a property of the process, not a line in a prompt, and it
survives any instruction the model is given or given by others.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from saadhak.config import settings

# Research only. "trading" is deliberately absent: no place_*_order, no
# close_position, no cancel_order reaches the model's tool list. "account" is
# absent too, because it carries update_account_config, which can change margin
# and shorting settings. The engine feeds account context into the prompt from
# its own REST call instead, so nothing the model can reach mutates anything.
RESEARCH_TOOLSETS = "options-data,stock-data,news,assets"

FORBIDDEN = ("place_", "cancel_", "close_", "replace_", "exercise_", "update_")


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: str
    error: str | None = None


def server_params() -> StdioServerParameters:
    s = settings()
    env = {
        **os.environ,
        "ALPACA_API_KEY": s.apca_api_key_id,
        "ALPACA_SECRET_KEY": s.apca_api_secret_key,
        "ALPACA_PAPER_TRADE": "true",
        "ALPACA_TOOLSETS": RESEARCH_TOOLSETS,
    }
    return StdioServerParameters(command="uvx", args=["alpaca-mcp-server"], env=env)


@asynccontextmanager
async def session():
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            yield s


async def list_tools() -> list[str]:
    async with session() as s:
        return [t.name for t in (await s.list_tools()).tools]


async def call(name: str, arguments: dict | None = None) -> ToolCall:
    async with session() as s:
        return await _call_on(s, name, arguments or {})


async def _call_on(s: ClientSession, name: str, arguments: dict) -> ToolCall:
    if any(name.startswith(p) for p in FORBIDDEN):
        return ToolCall(name, arguments, "", "refused: not a research tool")
    try:
        r = await s.call_tool(name, arguments)
        text = "\n".join(getattr(c, "text", "") for c in r.content)[:4000]
        return ToolCall(name, arguments, text)
    except Exception as e:
        return ToolCall(name, arguments, "", str(e))


async def research(calls: list[tuple[str, dict]]) -> list[ToolCall]:
    """Run several research calls inside one server session."""
    async with session() as s:
        return [await _call_on(s, name, args) for name, args in calls]


def verify_no_trading_tools() -> dict[str, Any]:
    """Proof, not a promise: enumerate what the model can actually reach."""
    names = asyncio.run(list_tools())
    dangerous = [n for n in names if any(n.startswith(p) for p in FORBIDDEN)]
    return {"toolsets": RESEARCH_TOOLSETS, "tool_count": len(names),
            "trading_tools_exposed": dangerous, "safe": not dangerous,
            "tools": sorted(names)}
