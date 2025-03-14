#!/usr/bin/env python

import asyncio
import sys
import xml.dom.minidom
from server import get_last_bundestagsprotocol


async def main():
    print("Hole das neueste Bundestagsprotokoll...", file=sys.stderr)
    xml_content = await get_last_bundestagsprotocol()

    if xml_content:
        # Formatieren des XMLs für bessere Lesbarkeit (nur die ersten 1000 Zeichen)
        try:
            dom = xml.dom.minidom.parseString(xml_content)
            pretty_xml = dom.toprettyxml()
            print("\nStruktur des XML-Dokuments (Auszug):", file=sys.stderr)
            print(pretty_xml[:1000] + "...", file=sys.stderr)

            # Einfache Analyse der XML-Struktur
            print("\nAnalyse der XML-Struktur:", file=sys.stderr)
            document = dom.documentElement
            print(f"Root-Element: {document.tagName}", file=sys.stderr)

            # Kindknoten des Root-Elements auflisten
            print("Hauptelemente:", file=sys.stderr)
            for child in document.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    print(f"  - {child.tagName}", file=sys.stderr)

            # Vollständiges XML in eine Datei schreiben für weitere Analyse
            with open("latest_protocol.xml", "w", encoding="utf-8") as f:
                f.write(pretty_xml)
            print(
                "\nVollständiges XML wurde in 'latest_protocol.xml' gespeichert.",
                file=sys.stderr,
            )

        except Exception as e:
            print(f"Fehler bei der XML-Verarbeitung: {e}", file=sys.stderr)
            # Rohes XML speichern, wenn die Verarbeitung fehlschlägt
            with open("latest_protocol_raw.xml", "wb") as f:
                f.write(xml_content)
            print(
                "Rohes XML wurde in 'latest_protocol_raw.xml' gespeichert.",
                file=sys.stderr,
            )
    else:
        print("Konnte kein Bundestagsprotokoll abrufen.", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
