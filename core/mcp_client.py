import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["-m", "mcp_server.crm_server"],
)

async def _call_tool(tool_name: str, arguments: dict):
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            raw_text = result.content[0].text
            return json.loads(raw_text)

def get_stalled_deals(days_since_contact: int = 14) -> list[dict]:
    return asyncio.run(_call_tool("get_stalled_deals", {"days_since_contact": days_since_contact}))

def get_deal_history(deal_id: int) -> list[dict]:
    return asyncio.run(_call_tool("get_deal_history", {"deal_id": deal_id}))

def log_action(deal_id: int, agent_name: str, action: str, detail: str = "") -> str:
    return asyncio.run(_call_tool("log_action", {
        "deal_id": deal_id, "agent_name": agent_name, "action": action, "detail": detail
    }))

def request_approval(deal_id: int, proposed_action: str) -> int:
    return asyncio.run(_call_tool("request_approval", {
        "deal_id": deal_id, "proposed_action": proposed_action
    }))
