#!/usr/bin/env python

import os
import sys
import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

import httpx
from dotenv import load_dotenv

load_dotenv()


class BundestagResource:
    """Basisklasse für Ressourcen aus Bundestagsprotokollen."""

    def __init__(self, xml_data: bytes):
        self.root = ET.fromstring(xml_data)
        self.ns = {"bt": ""}  # Falls in Zukunft Namespaces verwendet werden
        self._parse_metadata()

    def _parse_metadata(self):
        """Extrahiert Metadaten aus dem Protokoll."""
        self.wahlperiode = self.root.get("wahlperiode")
        self.sitzung_nr = self.root.get("sitzung-nr")
        self.sitzung_datum = self.root.get("sitzung-datum")
        self.sitzung_ort = self.root.get("sitzung-ort")
        self.sitzung_start = self.root.get("sitzung-start-uhrzeit")
        self.sitzung_ende = self.root.get("sitzung-ende-uhrzeit")

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        return {
            "wahlperiode": self.wahlperiode,
            "sitzung_nr": self.sitzung_nr,
            "sitzung_datum": self.sitzung_datum,
            "sitzung_ort": self.sitzung_ort,
            "sitzung_start": self.sitzung_start,
            "sitzung_ende": self.sitzung_ende,
        }

    def to_json(self) -> str:
        """Konvertiert die Ressource in einen JSON-String."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class SessionMetadata(BundestagResource):
    """Ressource für die Metadaten einer Plenarsitzung."""

    def _parse_metadata(self):
        """Erweitert Metadaten mit zusätzlichen Informationen."""
        super()._parse_metadata()

        # Hier könnten weitere Metadaten extrahiert werden
        self.herausgeber = self.root.get("herausgeber")
        self.issn = self.root.get("issn")
        self.sitzung_naechste_datum = self.root.get("sitzung-naechste-datum")
        self.start_seitennr = self.root.get("start-seitennr")

    def to_dict(self) -> Dict[str, Any]:
        """Erweitert Dictionary mit zusätzlichen Metadaten."""
        data = super().to_dict()
        data.update(
            {
                "herausgeber": self.herausgeber,
                "issn": self.issn,
                "sitzung_naechste_datum": self.sitzung_naechste_datum,
                "start_seitennr": self.start_seitennr,
            }
        )
        return data


class AgendaItem(BundestagResource):
    """Ressource für Tagesordnungspunkte einer Plenarsitzung."""

    def __init__(self, xml_data: bytes):
        super().__init__(xml_data)
        self.agenda_items = self._extract_agenda_items()

    def _extract_agenda_items(self) -> List[Dict[str, Any]]:
        """Extrahiert alle Tagesordnungspunkte aus dem Protokoll."""
        items = []

        # Finde alle Tagesordnungspunkte im XML
        tagesordnungspunkte = self.root.findall(".//tagesordnungspunkt")

        for top in tagesordnungspunkte:
            top_id = top.get("top-id")
            titel_elem = top.find(".//p[@klasse='T_fett']")

            # Extrahiere den Text des Tagesordnungspunkts
            titel = ""
            if titel_elem is not None and titel_elem.text:
                titel = titel_elem.text.strip()

            # Finde alle untergeordneten Textelemente
            description = []
            for p in top.findall(".//p"):
                if p.text and p != titel_elem:
                    description.append(p.text.strip())

            items.append(
                {
                    "id": top_id,
                    "titel": titel,
                    "beschreibung": "\n".join(description) if description else "",
                }
            )

        return items

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        data = super().to_dict()
        data["tagesordnungspunkte"] = self.agenda_items
        return data


class SpeakerList(BundestagResource):
    """Ressource für die Rednerliste einer Plenarsitzung."""

    def __init__(self, xml_data: bytes):
        super().__init__(xml_data)
        self.speakers = self._extract_speakers()

    def _extract_speakers(self) -> List[Dict[str, Any]]:
        """Extrahiert alle Redner aus dem Protokoll."""
        speakers = []

        # Finde alle Redner im XML
        redner_elems = self.root.findall(".//redner")

        for redner in redner_elems:
            redner_id = redner.get("id")

            # Verhindere Duplikate durch eindeutige IDs
            if any(s["id"] == redner_id for s in speakers):
                continue

            name_elem = redner.find("./name")
            if name_elem is None:
                continue

            vorname = name_elem.find("./vorname")
            nachname = name_elem.find("./nachname")
            titel = name_elem.find("./titel")
            fraktion = name_elem.find("./fraktion")
            rolle = name_elem.find("./rolle/rolle_lang")

            speaker_info = {
                "id": redner_id,
                "vorname": vorname.text if vorname is not None and vorname.text else "",
                "nachname": (
                    nachname.text if nachname is not None and nachname.text else ""
                ),
                "titel": titel.text if titel is not None and titel.text else "",
                "fraktion": (
                    fraktion.text if fraktion is not None and fraktion.text else ""
                ),
                "rolle": rolle.text if rolle is not None and rolle.text else "",
            }

            speakers.append(speaker_info)

        return speakers

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        data = super().to_dict()
        data["redner"] = self.speakers
        return data


class Speech(BundestagResource):
    """Ressource für einzelne Reden einer Plenarsitzung."""

    def __init__(self, xml_data: bytes, speech_id: Optional[str] = None):
        super().__init__(xml_data)
        self.speeches = self._extract_speeches(speech_id)

    def _extract_speeches(
        self, specific_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extrahiert alle Reden oder eine bestimmte Rede aus dem Protokoll."""
        speeches = []

        # Finde alle Reden im XML
        rede_elems = self.root.findall(".//rede")

        for rede in rede_elems:
            rede_id = rede.get("id")

            # Wenn eine bestimmte ID angefordert wurde, filtere entsprechend
            if specific_id and rede_id != specific_id:
                continue

            redner_elem = rede.find("./p[@klasse='redner']/redner")
            redner_info = {}

            if redner_elem is not None:
                name_elem = redner_elem.find("./name")
                if name_elem is not None:
                    vorname = name_elem.find("./vorname")
                    nachname = name_elem.find("./nachname")
                    titel = name_elem.find("./titel")
                    fraktion = name_elem.find("./fraktion")
                    rolle = name_elem.find("./rolle/rolle_lang")

                    redner_info = {
                        "id": redner_elem.get("id"),
                        "vorname": (
                            vorname.text if vorname is not None and vorname.text else ""
                        ),
                        "nachname": (
                            nachname.text
                            if nachname is not None and nachname.text
                            else ""
                        ),
                        "titel": titel.text if titel is not None and titel.text else "",
                        "fraktion": (
                            fraktion.text
                            if fraktion is not None and fraktion.text
                            else ""
                        ),
                        "rolle": rolle.text if rolle is not None and rolle.text else "",
                    }

            # Extrahiere den Redetext
            speech_content = []
            for p in rede.findall(".//p"):
                if p.get("klasse") != "redner" and p.text:
                    speech_content.append(p.text.strip())

            # Extrahiere Kommentare und Zwischenrufe
            kommentare = []
            for k in rede.findall(".//kommentar"):
                if k.text:
                    kommentare.append(k.text.strip())

            speeches.append(
                {
                    "id": rede_id,
                    "redner": redner_info,
                    "inhalt": "\n".join(speech_content),
                    "kommentare": kommentare,
                }
            )

            # Wenn eine bestimmte ID angefordert wurde und gefunden ist, breche ab
            if specific_id and rede_id == specific_id:
                break

        return speeches

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        data = super().to_dict()
        if len(self.speeches) == 1:
            data["rede"] = self.speeches[0]
        else:
            data["reden"] = self.speeches
        return data


class AttachmentList(BundestagResource):
    """Ressource für Anlagen zu einer Plenarsitzung."""

    def __init__(self, xml_data: bytes):
        super().__init__(xml_data)
        self.attachments = self._extract_attachments()

    def _extract_attachments(self) -> List[Dict[str, Any]]:
        """Extrahiert alle Anlagen aus dem Protokoll."""
        attachments = []

        # Finde alle Anlagen im XML
        anlagen_blocks = self.root.findall(".//ivz-block")

        for block in anlagen_blocks:
            titel_elem = block.find("./ivz-block-titel")
            if titel_elem is None or titel_elem.text is None:
                continue

            if not titel_elem.text.startswith("Anlage"):
                continue

            # Extrahiere Einträge in der Anlage
            eintraege = []
            for eintrag in block.findall("./ivz-eintrag"):
                inhalt_elem = eintrag.find("./ivz-eintrag-inhalt")
                if inhalt_elem is not None and inhalt_elem.text:
                    eintraege.append(inhalt_elem.text.strip())

            attachments.append(
                {
                    "titel": titel_elem.text.strip(),
                    "eintraege": eintraege,
                }
            )

        return attachments

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        data = super().to_dict()
        data["anlagen"] = self.attachments
        return data


class TableOfContents(BundestagResource):
    """Ressource für das Inhaltsverzeichnis einer Plenarsitzung."""

    def __init__(self, xml_data: bytes):
        super().__init__(xml_data)
        self.toc = self._extract_toc()

    def _extract_toc(self) -> Dict[str, Any]:
        """Extrahiert das Inhaltsverzeichnis aus dem Protokoll."""
        toc = {"titel": "", "eintraege": []}

        # Finde das Inhaltsverzeichnis im XML
        inhaltsverzeichnis = self.root.find(".//inhaltsverzeichnis")
        if inhaltsverzeichnis is None:
            return toc

        titel_elem = inhaltsverzeichnis.find("./ivz-titel")
        if titel_elem is not None and titel_elem.text:
            toc["titel"] = titel_elem.text.strip()

        # Extrahiere Einträge
        for eintrag in inhaltsverzeichnis.findall("./ivz-eintrag"):
            inhalt_elem = eintrag.find("./ivz-eintrag-inhalt")
            if inhalt_elem is not None and inhalt_elem.text:
                toc["eintraege"].append(
                    {
                        "inhalt": inhalt_elem.text.strip(),
                        "seite": self._extract_page_reference(eintrag),
                    }
                )

        # Extrahiere Blöcke (Tagesordnungspunkte)
        blocks = []
        for block in inhaltsverzeichnis.findall("./ivz-block"):
            titel_elem = block.find("./ivz-block-titel")
            block_data = {"titel": "", "eintraege": []}

            if titel_elem is not None and titel_elem.text:
                block_data["titel"] = titel_elem.text.strip()

            for eintrag in block.findall("./ivz-eintrag"):
                inhalt_elem = eintrag.find("./ivz-eintrag-inhalt")
                if inhalt_elem is not None and inhalt_elem.text:
                    block_data["eintraege"].append(
                        {
                            "inhalt": inhalt_elem.text.strip(),
                            "seite": self._extract_page_reference(eintrag),
                        }
                    )

            blocks.append(block_data)

        toc["bloecke"] = blocks

        return toc

    def _extract_page_reference(self, eintrag_elem) -> str:
        """Extrahiert die Seitenreferenz aus einem Inhaltsverzeichniseintrag."""
        page_ref = ""
        a_elem = eintrag_elem.find(".//a")

        if a_elem is not None:
            seite_elem = a_elem.find("./seite")
            seitenbereich_elem = a_elem.find("./seitenbereich")

            if seite_elem is not None and seite_elem.text:
                page_ref = seite_elem.text.strip()

            if seitenbereich_elem is not None and seitenbereich_elem.text:
                page_ref += seitenbereich_elem.text.strip()

        return page_ref

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Ressource in ein Dictionary."""
        data = super().to_dict()
        data.update(self.toc)
        return data


class FullProtocol(BundestagResource):
    """Ressource für das vollständige Plenarprotokoll."""

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das vollständige Protokoll in ein Dictionary."""
        data = super().to_dict()

        # Füge zusätzliche Metadaten hinzu
        metadata = SessionMetadata(ET.tostring(self.root)).to_dict()
        data.update({k: v for k, v in metadata.items() if k not in data})

        # Extrahiere Inhaltsverzeichnis
        toc = TableOfContents(ET.tostring(self.root)).to_dict()
        data["inhaltsverzeichnis"] = {
            "titel": toc.get("titel", ""),
            "eintraege": toc.get("eintraege", []),
            "bloecke": toc.get("bloecke", []),
        }

        # Extrahiere Tagesordnungspunkte
        agenda = AgendaItem(ET.tostring(self.root)).to_dict()
        data["tagesordnungspunkte"] = agenda.get("tagesordnungspunkte", [])

        # Extrahiere Redner
        speakers = SpeakerList(ET.tostring(self.root)).to_dict()
        data["redner"] = speakers.get("redner", [])

        # Extrahiere Anlagen
        attachments = AttachmentList(ET.tostring(self.root)).to_dict()
        data["anlagen"] = attachments.get("anlagen", [])

        return data


class ResourceType(Enum):
    """Enum für die verschiedenen Ressourcentypen."""

    METADATA = "metadata"
    AGENDA_ITEM = "agendaitem"
    SPEAKER_LIST = "speakerlist"
    SPEECH = "speech"
    ATTACHMENT_LIST = "attachmentlist"
    TOC = "toc"
    FULL_PROTOCOL = "fullprotocol"


def create_resource(
    resource_type: ResourceType, xml_data: bytes, **kwargs
) -> BundestagResource:
    """Factory-Methode zur Erstellung von Ressourcen."""
    if resource_type == ResourceType.METADATA:
        return SessionMetadata(xml_data)
    elif resource_type == ResourceType.AGENDA_ITEM:
        return AgendaItem(xml_data)
    elif resource_type == ResourceType.SPEAKER_LIST:
        return SpeakerList(xml_data)
    elif resource_type == ResourceType.SPEECH:
        return Speech(xml_data, kwargs.get("speech_id"))
    elif resource_type == ResourceType.ATTACHMENT_LIST:
        return AttachmentList(xml_data)
    elif resource_type == ResourceType.TOC:
        return TableOfContents(xml_data)
    elif resource_type == ResourceType.FULL_PROTOCOL:
        return FullProtocol(xml_data)
    else:
        raise ValueError(f"Unbekannter Ressourcentyp: {resource_type}")
