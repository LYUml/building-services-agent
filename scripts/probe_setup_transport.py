"""Read-only SDK handshake using the saved project MCP startup profile."""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import tomllib


async def probe(config):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    server = tomllib.loads(config.read_text(encoding='utf-8'))['mcp_servers']['building_services']
    params = StdioServerParameters(command=server['command'], args=server['args'],
        cwd=server['cwd'], env={**os.environ, **server.get('env', {})})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=120)) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            if len(tools) != 45:
                raise ValueError('Expected 45 MCP tools')
            response = await session.call_tool('bsa_reference_catalogue', {'limit': 1})
            if response.isError:
                raise ValueError('Read-only reference catalogue failed: ' + str(response.content))
    return dict(schema='bsa.setup-transport/1', tool_count=len(tools),
                catalogue_call_pass=True, configured_enabled=server.get('enabled', True),
                host_ui_connection_verified=False, native_execution_verified=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    result = asyncio.run(probe(args.config))
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
