"""Strict synthetic confirmation endpoint diagnostics; never pixel acceptance."""

import hashlib
import json
import math
import re
import struct
import zlib

from scripts.python import workspace_ownership

NAME = re.compile(r"workspace-confirm-(submit-review|publish|delete|restore)-capture\.json")
BUDGET = 16384
STATES = {"submit-review", "publish", "delete", "restore"}
PROJECTS = {"chromium-compact", "chromium-desktop", "chromium-large-text"}
ERRORS = {
    "settlement-failed",
    "pre-sample-failed",
    "capture-missing",
    "post-sample-failed",
    "capture-state-invalid",
    "ownership-revoked",
}


def registered(suite, relative):
    return (
        suite == "workspace"
        and len(relative.parts) == 2
        and NAME.fullmatch(relative.name)
        and workspace_ownership.scenario_for_case(relative.parts[0]) == "confirmations"
        and workspace_ownership.project_for_case(relative.parts[0]) in PROJECTS
    )


def png_dimensions(raw):
    """Decode bounded noninterlaced 8-bit RGB(A) scanlines and verify every CRC.

    All five filter types are total byte transforms; validating each filter tag
    and the complete decompressed row length establishes decodability without
    re-encoding or modifying the retained PNG.
    """

    def need(ok):
        if not ok:
            raise ValueError("invalid confirmation PNG")

    need(raw[:8] == b"\x89PNG\r\n\x1a\n")
    pos, chunks, data, size = 8, [], bytearray(), None
    ended = False
    while pos < len(raw):
        need(pos + 12 <= len(raw))
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        kind = raw[pos + 4 : pos + 8]
        need(length <= 32 * 1024 * 1024 and pos + 12 + length <= len(raw))
        payload = raw[pos + 8 : pos + 8 + length]
        need(
            zlib.crc32(kind + payload) & 0xFFFFFFFF
            == struct.unpack(">I", raw[pos + 8 + length : pos + 12 + length])[0]
        )
        if not chunks:
            need(kind == b"IHDR" and length == 13)
            w, h, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            need(0 < w <= 16384 and 0 < h <= 16384 and w * h <= 16 * 1024 * 1024)
            need(depth == 8 and color in (2, 6) and compression == filtering == interlace == 0)
            size = (w, h, 3 if color == 2 else 4)
        elif kind == b"IHDR":
            need(False)
        elif kind == b"IDAT":
            need(b"IDAT" not in chunks or chunks[-1] == b"IDAT")
            data.extend(payload)
        elif kind == b"IEND":
            need(length == 0 and b"IDAT" in chunks and pos + 12 == len(raw))
            ended = True
        else:
            need(kind[0] & 32 and kind != b"acTL")
        chunks.append(kind)
        pos += 12 + length
    need(ended and size is not None)
    w, h, channels = size
    row = w * channels + 1
    decoder = zlib.decompressobj()
    try:
        decoded = decoder.decompress(bytes(data), row * h + 1)
    except zlib.error as error:
        raise ValueError("invalid confirmation PNG") from error
    need(
        len(decoded) == row * h
        and decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail
    )
    need(all(decoded[i] <= 4 for i in range(0, len(decoded), row)))
    return [w, h]


def consistent(s):
    return (
        (not s["sticky"] or (s["header"] is not None and s["header"][2] > 0 and s["header"][3] > 0))
        and s["scale"] > 0
        and s["visualScale"] == 1
        and 0 < s["viewport"][2] <= 4
        and s["layout"][0] > 0
        and s["layout"][1] >= s["layout"][0]
        and s["max"] == max(0, s["layout"][1] - s["layout"][0])
        and not s["overscroll"]
        and 0 <= s["offset"] <= s["max"]
        and (
            (s["port"] is None and s["scale"] == 1 and s["layout"][0] == s["viewport"][1])
            if s["target"] == "document"
            else (
                s["port"] is not None
                and s["layout"][2] > 0
                and s["scale"] == s["port"][3] / s["layout"][2]
            )
        )
    )


def visible(s):
    if not consistent(s):
        return False
    if s["panel"] is None or s["route"] != "workspace" or s["dialogs"] != 1:
        return False
    x, y, w, h = s["panel"]
    vx, vy, vw, vh = s["visual"]
    p = s["port"] or [0, 0, *s["viewport"][:2]]
    top = max(0, vy, p[1], s["header"][1] + s["header"][3] if s["sticky"] and s["header"] else 0)
    return (
        w > 0
        and h > 0
        and x >= max(0, vx, p[0])
        and x + w <= min(s["viewport"][0], vx + vw, p[0] + p[2])
        and y >= top
        and y + h <= min(s["viewport"][1], vy + vh, p[1] + p[3])
    )


def validate(raw, path, provenance):
    def require(ok):
        if not ok:
            raise ValueError("invalid confirmation capture receipt")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    def number(v):
        return type(v) in (int, float) and math.isfinite(v) and abs(v) <= 10000000

    def rect(v):
        return (
            type(v) is list
            and len(v) == 4
            and all(number(n) for n in v)
            and v[2] >= 0
            and v[3] >= 0
        )

    def sample(s):
        require(
            type(s) is dict
            and set(s)
            == {
                "state",
                "route",
                "target",
                "focus",
                "viewport",
                "visual",
                "panel",
                "port",
                "header",
                "sticky",
                "offset",
                "max",
                "scale",
                "dialogs",
                "layout",
                "visualScale",
                "overscroll",
            }
        )
        require(type(s["state"]) is str and s["state"] in STATES | {"other"})
        require(s["route"] in ("workspace", "other") and s["target"] in ("document", "scrollport"))
        require(
            s["focus"] in ("dismiss", "confirm", "panel", "outside") and type(s["sticky"]) is bool
        )
        require(
            type(s["viewport"]) is list
            and len(s["viewport"]) == 3
            and all(number(v) and v > 0 for v in s["viewport"])
        )
        require(rect(s["visual"]) and s["visual"][2] > 0 and s["visual"][3] > 0)
        for k in ("panel", "port", "header"):
            require(s[k] is None or rect(s[k]))
        require((s["target"] == "scrollport") == (s["port"] is not None))
        require(
            all(number(s[k]) for k in ("offset", "max", "scale"))
            and s["max"] >= 0
            and s["scale"] > 0
        )
        require(
            type(s["layout"]) is list
            and len(s["layout"]) == 3
            and all(type(n) is int and 0 <= n <= 10000000 for n in s["layout"])
        )
        require(number(s["visualScale"]) and s["visualScale"] > 0 and type(s["overscroll"]) is bool)
        require(s["overscroll"] == (s["offset"] < 0 or s["offset"] > s["max"]))
        require(type(s["dialogs"]) is int and 0 <= s["dialogs"] <= 100)

    require(len(raw) <= BUDGET)
    try:
        d = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise ValueError("invalid confirmation capture receipt") from error
    require(
        type(d) is dict
        and set(d)
        == {
            "schemaVersion",
            "scope",
            "sourceCommit",
            "sourceTree",
            "runId",
            "attempt",
            "project",
            "state",
            "settlement",
            "pre",
            "post",
            "image",
            "errors",
            "complete",
        }
    )
    require(
        type(d["schemaVersion"]) is int
        and d["schemaVersion"] == 2
        and d["scope"] == "synthetic-confirmation-capture"
    )
    match = NAME.fullmatch(path.name)
    require(match is not None and d["state"] == match[1])
    require(
        type(d["project"]) is str
        and d["project"] in PROJECTS
        and path.parent.name == workspace_ownership.CASES["confirmations"] + "-" + d["project"]
    )
    for key in ("sourceCommit", "sourceTree", "runId", "attempt"):
        require(type(d[key]) is str and d[key] == str(provenance[key]))
        require(
            re.fullmatch("[a-f0-9]{40}" if key.startswith("source") else "[0-9]{1,20}", d[key])
            is not None
        )
    require(type(d["complete"]) is bool and type(d["errors"]) is list and len(d["errors"]) <= 6)
    require(
        all(type(e) is str and e in ERRORS for e in d["errors"])
        and len(set(d["errors"])) == len(d["errors"])
    )
    for key in ("pre", "post"):
        if d[key] is not None:
            sample(d[key])
    settlement = d["settlement"]
    if settlement is not None:
        require(type(settlement) is dict and set(settlement) == {"probes", "elapsed"})
        require(type(settlement["probes"]) is int and 2 <= settlement["probes"] <= 32)
        require(number(settlement["elapsed"]) and 0 <= settlement["elapsed"] <= 1000)
    image = d["image"]
    if image is not None:
        require(type(image) is dict and set(image) == {"file", "bytes", "sha256", "dimensions"})
        require(image["file"] == f"workspace-confirm-{d['state']}-attempt.png")
        require(type(image["bytes"]) is int and 0 < image["bytes"] <= 32 * 1024 * 1024)
        require(
            type(image["sha256"]) is str
            and re.fullmatch("[a-f0-9]{64}", image["sha256"]) is not None
        )
        p = path.parent / image["file"]
        require(not p.is_symlink() and p.is_file() and p.stat().st_size == image["bytes"])
        content = p.read_bytes()
        require(hashlib.sha256(content).hexdigest() == image["sha256"])
        require(
            type(image["dimensions"]) is list
            and len(image["dimensions"]) == 2
            and all(type(n) is int and n > 0 for n in image["dimensions"])
        )
        require(png_dimensions(content) == image["dimensions"])
    else:
        require("capture-missing" in d["errors"])
    complete = (
        not d["errors"]
        and settlement is not None
        and image is not None
        and d["pre"] is not None
        and d["post"] is not None
        and d["pre"] == d["post"]
        and image["dimensions"]
        == [math.floor(v * d["pre"]["viewport"][2] + 0.5) for v in d["pre"]["viewport"][:2]]
        and visible(d["pre"])
        and visible(d["post"])
        and d["pre"]["focus"] == "dismiss"
        and d["pre"]["state"] == d["state"]
    )
    require(d["complete"] == complete)
    require(d["complete"] or bool(d["errors"]))
    return d
