#!/usr/bin/env python

import os
import sys
import re
import json

from datetime import datetime
from typing import Any, Dict, List, Optional

import click
import httpx
from fastapi import Response
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from server_resources import (
    ResourceType,
    create_resource,
    SessionMetadata,
    TableOfContents,
    AgendaItem,
    SpeakerList,
    Speech,
    AttachmentList,
    FullProtocol,
)

load_dotenv()

mcp = FastMCP("Bundetag-Plenarprotokolle")

# Globaler Cache für das letzte Protokoll
cached_protocol = None


async def query_api(url: str, query_params) -> dict[str, Any] | None:
    headers = {
        "Accept": "application/json",
        "Authorization": f"ApiKey {os.getenv('BUNDESTAG_API_KEY')}",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=headers, timeout=30.0, params=query_params
            )
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
        "f.zuordnung": "BT",
    }

    results = await query_api(url, params)

    xml_url = None
    if results:
        if "documents" in results:
            print(
                f"Total documents found: {len(results['documents'])}.", file=sys.stderr
            )
            for doc in results["documents"]:
                if "xml_url" not in doc["fundstelle"]:
                    print(
                        f"Couldn't find 'xml_url'. Trying next document.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Using protocol from {doc['fundstelle']['datum']}",
                        file=sys.stderr,
                    )
                    xml_url = doc["fundstelle"]["xml_url"]
                    break

    return xml_url


@mcp.tool()
async def get_last_bundestagsplenarprotokoll() -> str:
    """Get the protocol of the last German parliament session.
    Das Protokoll der letzten Plenarsitzung des Deutschen Bundestags.
    """
    global cached_protocol

    if not cached_protocol:
        xml_url = await get_last_protocol_xml_url()
        cached_protocol = await query_api(xml_url, {"format": "xml"})

    return cached_protocol


async def get_protocol_xml() -> bytes:
    """Hilfsfunktion, um das Protokoll als bytes zu erhalten."""
    global cached_protocol

    if not cached_protocol:
        await get_last_bundestagsprotocol()

    return cached_protocol


@mcp.resource("plenarprotokoll://metadata")
async def protocol_metadata() -> str:
    """Metadaten der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.METADATA, protocol_xml)

    return dict(
        uri="plenarprotokoll://metadata",
        name="Metadaten der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://toc")
async def protocol_toc() -> str:
    """Inhaltsverzeichnis der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.TOC, protocol_xml)

    return dict(
        uri="plenarprotokoll://toc",
        name="Inhaltsverzeichnis der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://speaker-list")
async def protocol_speaker_list() -> str:
    """Liste aller Redner der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.SPEAKER_LIST, protocol_xml)

    return dict(
        uri="plenarprotokoll://speaker-list",
        name="Rednerliste der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://agenda-items")
async def protocol_agenda_items() -> str:
    """Tagesordnungspunkte der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.AGENDA_ITEM, protocol_xml)

    return dict(
        uri="plenarprotokoll://agenda-items",
        name="Tagesordnungspunkte der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://speeches")
async def protocol_speeches() -> str:
    """Alle Reden der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.SPEECH, protocol_xml)

    return dict(
        uri="plenarprotokoll://speeches",
        name="Alle Reden der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://attachments")
async def protocol_attachments() -> str:
    """Anlagen der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.ATTACHMENT_LIST, protocol_xml)

    return dict(
        uri="plenarprotokoll://attachments",
        name="Anlagen der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://full")
async def protocol_full() -> str:
    """Vollständiges Protokoll der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.FULL_PROTOCOL, protocol_xml)

    return str(
        uri="plenarprotokoll://full",
        name="Vollständiges Protokoll der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


# Dynamische Ressourcen über URI-Templates


@mcp.resource("plenarprotokoll://speech/{speech_id}")
async def plenarprotokoll_speech_by_id(speech_id: str) -> str:
    """Eine bestimmte Rede aus der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()
    resource = create_resource(ResourceType.SPEECH, protocol_xml, speech_id=speech_id)

    return dict(
        uri=f"plenarprotokoll://speech/{speech_id}",
        name=f"Rede mit ID {speech_id} aus der letzten Bundestagssitzung",
        text=resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://speaker/{speaker_id}")
async def plenarprotokoll_speaker_speeches(speaker_id: str) -> str:
    """Alle Reden eines bestimmten Redners aus der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()

    # Erst alle Reden holen
    speech_resource = create_resource(ResourceType.SPEECH, protocol_xml)
    speeches = speech_resource.speeches

    # Reden nach Redner filtern
    filtered_speeches = [
        speech
        for speech in speeches
        if speech.get("redner", {}).get("id") == speaker_id
    ]

    # Neues Resource-Objekt erstellen
    filtered_resource = Speech(protocol_xml)
    filtered_resource.speeches = filtered_speeches

    return dict(
        uri=f"plenarprotokoll://speaker/{speaker_id}",
        name=f"Reden des Redners mit ID {speaker_id} aus der letzten Bundestagssitzung",
        text=filtered_resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://fraction/{fraction_name}")
async def plenarprotokoll_fraction_speeches(fraction_name: str) -> str:
    """Alle Reden einer bestimmten Fraktion aus der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()

    # Erst alle Reden holen
    speech_resource = create_resource(ResourceType.SPEECH, protocol_xml)
    speeches = speech_resource.speeches

    # Nach Fraktion filtern
    filtered_speeches = [
        speech
        for speech in speeches
        if speech.get("redner", {}).get("fraktion") == fraction_name
    ]

    # Neues Resource-Objekt erstellen
    filtered_resource = Speech(protocol_xml)
    filtered_resource.speeches = filtered_speeches

    return dict(
        uri=f"plenarprotokoll://fraction/{fraction_name}",
        name=f"Reden der Fraktion {fraction_name} aus der letzten Bundestagssitzung",
        text=filtered_resource.to_json(),
        mimeType="application/json",
    )


@mcp.resource("plenarprotokoll://search/{keyword}")
async def plenarprotokoll_search(keyword: str) -> str:
    """Suche nach einem Stichwort in allen Reden der letzten Bundestagssitzung."""
    protocol_xml = await get_protocol_xml()

    # Erst alle Reden holen
    speech_resource = create_resource(ResourceType.SPEECH, protocol_xml)
    speeches = speech_resource.speeches

    # Nach Keyword suchen
    keyword_lower = keyword.lower()
    search_results = []

    for speech in speeches:
        content = speech.get("inhalt", "").lower()
        if keyword_lower in content:
            # Kontext um das Keyword herum extrahieren
            matches = []
            for match in re.finditer(re.escape(keyword_lower), content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                matches.append(f"...{context}...")

            result = {
                "id": speech.get("id"),
                "redner": speech.get("redner", {}),
                "matches": matches,
                "match_count": len(matches),
            }
            search_results.append(result)

    return dict(
        uri=f"plenarprotokoll://search/{keyword}",
        name=f"Suche nach '{keyword}' in der letzten Bundestagssitzung",
        text=json.dumps(
            {"suchergebnisse": search_results}, ensure_ascii=False, indent=2
        ),
        mimeType="application/json",
    )


@click.command(help="MCP Server für Deutscher Bundestag Plenarprotokolle")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport-Modus für den MCP-Server: 'stdio' (Standard) oder 'sse'",
    show_default=True,
)
def main(transport):
    print(f"Starting MCP server with transport mode: {transport}", file=sys.stderr)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
