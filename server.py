import os
import sys
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Bundetag")

async def query_api(url: str, query_params) -> dict[str, Any] | None:
    headers = {
        "Accept": "application/json",
        "Authorization": f"ApiKey {os.getenv('BUNDESTAG_API_KEY')}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0, params=query_params)
            response.raise_for_status()
            if query_params["format"] == "json":
                return response.json()
            else: 
                return response.content
        except Exception:
            return None
        

async def get_last_protocol_xml_url():
    url = "https://search.dip.bundestag.de/api/v1/plenarprotokoll"
    params = {
        "f.datum.start": "2025-01-01",
        "f.datum.end": datetime.now().strftime("%Y-%m-%d"),
        "format": "json",
        "f.zuordnung": "BT"
    }
    
    results = await query_api(url, params)
    
    xml_url = None
    if results:
        if "documents" in results:
            print(f"\nTotal documents found: {len(results['documents'])}. Trying last.", file=sys.stderr)
            last = results['documents'][0]
            #pdf = last["fundstelle"]["pdf_url"]
            xml_url = last["fundstelle"]["xml_url"]
            
    return xml_url

#
# MCP Tool Definition
#

@mcp.tool()
async def get_last_bundestagsprotocol() -> str:
    """Get the protocol of the last German parliament session.
    Das Protokoll der letzten Plenarsitzung des Deutschen Bundestags.
    """
    
    xml_url = await get_last_protocol_xml_url()
    last_protocol_xml = await query_api(xml_url, {"format": "xml"})

    return last_protocol_xml

if __name__ == "__main__":
    print("Starting Bundestag-MCP", file=sys.stderr)
    mcp.run(transport='stdio')