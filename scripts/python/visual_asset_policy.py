#!/usr/bin/env python3
"""Enforce safe scalable SVG UI artwork and classified raster exceptions."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

RASTER = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ACTIVE_TAGS = {"script", "foreignObject", "iframe", "object", "embed"}
EXTERNAL = re.compile(r"^(?:https?:|//|data:text/html)", re.IGNORECASE)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def scan_assets(
    root: Path, *, raster_allow: tuple[str, ...] = ("content/", "photos/", "screenshots/")
) -> dict:
    findings = []
    assets = 0
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.casefold()
        if suffix in RASTER:
            assets += 1
            if not any(relative.startswith(prefix) for prefix in raster_allow):
                findings.append({"path": relative, "code": "UNCLASSIFIED_RASTER"})
            continue
        if suffix != ".svg":
            continue
        assets += 1
        try:
            document = ET.parse(path)
        except ET.ParseError:
            findings.append({"path": relative, "code": "SVG_INVALID"})
            continue
        root_element = document.getroot()
        if _local(root_element.tag) != "svg" or not root_element.get("viewBox"):
            findings.append({"path": relative, "code": "SVG_VIEWBOX_REQUIRED"})
        title_present = any(
            _local(element.tag) == "title" and (element.text or "").strip()
            for element in root_element
        )
        if (
            root_element.get("role") == "img"
            and not root_element.get("aria-label")
            and not root_element.get("aria-labelledby")
            and not title_present
        ):
            findings.append({"path": relative, "code": "SVG_ACCESSIBLE_NAME_REQUIRED"})
        for element in root_element.iter():
            if _local(element.tag) in ACTIVE_TAGS:
                findings.append({"path": relative, "code": "SVG_ACTIVE_CONTENT"})
            for name, value in element.attrib.items():
                local_name = _local(name)
                if local_name.casefold().startswith("on"):
                    findings.append({"path": relative, "code": "SVG_EVENT_HANDLER"})
                if local_name in {"href", "src"} and EXTERNAL.match(value.strip()):
                    findings.append({"path": relative, "code": "SVG_EXTERNAL_CONTENT"})
    return {
        "schemaVersion": 1,
        "ok": not findings,
        "assetCount": assets,
        "findings": findings,
        "secretValuesEmitted": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = scan_assets(args.root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
