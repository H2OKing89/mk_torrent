#!/usr/bin/env python3
"""
Test Mutagen metadata reader for .m4b (MP4) audiobooks.

Usage:
  python test_mutagen_m4b.py
  python test_mutagen_m4b.py --file "/path/to/book.m4b"

Requires:
  pip install mutagen
"""

import argparse
import base64
import json
import string
from pathlib import Path

import mutagen
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

# Friendly names for common MP4 atoms
FRIENDLY = {
    "©nam": "title",
    "©ART": "artist",
    "aART": "album_artist",
    "©alb": "album",
    "©day": "year_or_date",
    "©gen": "genre",
    "©wrt": "writer",
    "©too": "encoder",
    "©cmt": "comment",
    "desc": "description",
    "ldes": "long_description",
    "cprt": "copyright",
    "trkn": "track_number",
    "disk": "disc_number",
    "cpil": "compilation",
    "pgap": "gapless",
    "stik": "media_type",      # 2 often = Audiobook
    "tmpo": "tempo_bpm",
    "tvsh": "show",
    "tven": "episode_id",
    "tvsn": "season",
    "tves": "episode",
    "----:com.apple.iTunes:ASIN": "asin",
    "----:com.apple.iTunes:publisher": "publisher",
    "----:com.apple.iTunes:Purchase Date": "purchase_date",
    "----:com.apple.iTunes:Encoding Params": "encoding_params",
    "covr": "cover_art",
}

_PRINTABLE = set(bytes(string.printable, "ascii"))

def _is_mostly_text(b: bytes, threshold: float = 0.90) -> bool:
    if not b:
        return True
    printable = sum(ch in _PRINTABLE for ch in b)
    return (printable / len(b)) >= threshold

def _decode_bytes(b: bytes):
    """Return UTF-8/Latin-1 string if readable; otherwise a safe summary."""
    if _is_mostly_text(b):
        for enc in ("utf-8", "latin-1"):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
    # Fallback: summarize to avoid console garbage
    return {
        "bytes": len(b),
        "base64_preview": base64.b64encode(b[:96]).decode("ascii"),  # first 96 bytes
    }

def _decode_value(v):
    """Turn Mutagen values into serializable strings/tuples/summaries."""
    try:
        # Lists of values
        if isinstance(v, list):
            return [_decode_value(x) for x in v]

        # Freeform / bytes-like data (e.g., iTunSMPB / Encoding Params)
        if isinstance(v, (bytes, bytearray)):
            return _decode_bytes(bytes(v))

        if isinstance(v, MP4FreeForm):
            return _decode_bytes(bytes(v))

        # Track/disc numbers may be tuples like (track, total)
        if isinstance(v, tuple) and len(v) == 2 and all(isinstance(n, int) for n in v):
            return {"number": v[0], "total": v[1]}

        # Cover art: summarize, don't dump binary
        if isinstance(v, MP4Cover):
            fmt = "jpeg" if v.imageformat == MP4Cover.FORMAT_JPEG else "png"
            return {"bytes": len(v), "format": fmt}

        # Fall back to primitive / string
        return v
    except Exception:
        return str(v)

def mp4_tags_to_dict(tags):
    """Map raw MP4 atoms to friendly keys and decode values."""
    out = {}
    if not tags:
        return out

    for raw_key in tags.keys():
        friendly = FRIENDLY.get(raw_key, raw_key)
        val = tags.get(raw_key)

        if raw_key in ("trkn", "disk") and isinstance(val, list) and val:
            # Normalize e.g. [(5, 12)] -> {"number":5,"total":12}
            val = _decode_value(val[0])
        else:
            val = _decode_value(val)

        out[friendly] = val
    return out

def main():
    ap = argparse.ArgumentParser(description="Read metadata/tags from an M4B using Mutagen.")
    ap.add_argument(
        "--file",
        default=str(Path(
            
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
        )),
        help="Path to the .m4b file",
    )
    args = ap.parse_args()
    path = Path(args.file)

    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    audio = mutagen.File(str(path))
    if audio is None:
        raise SystemExit("Mutagen could not open this file. Is it a valid MP4/M4B?")

    info = {
        "mutagen_type": type(audio).__name__,
    }
    mime = getattr(audio, "mime", None)
    if mime:
        info["mime"] = mime

    # MP4-specific fields
    if isinstance(audio, MP4):
        ai = getattr(audio, "info", None)
        if ai:
            info["length_seconds"]   = getattr(ai, "length", None)
            info["bitrate"]          = getattr(ai, "bitrate", None)
            info["sample_rate"]      = getattr(ai, "sample_rate", None)
            info["channels"]         = getattr(ai, "channels", None)
            info["bits_per_sample"]  = getattr(ai, "bits_per_sample", None)

        tags = mp4_tags_to_dict(audio.tags)

    else:
        # Other container fallback
        ai = getattr(audio, "info", None)
        if ai:
            info["length_seconds"] = getattr(ai, "length", None)
            info["bitrate"]        = getattr(ai, "bitrate", None)
            info["sample_rate"]    = getattr(ai, "sample_rate", None)
            info["channels"]       = getattr(ai, "channels", None)

        tags = {}
        if getattr(audio, "tags", None):
            for k, v in audio.tags.items():
                # Many non-MP4 tags expose .text; safe-decode either way
                tags[str(k)] = _decode_value(getattr(v, "text", v))

    payload = {
        "path": str(path),
        "container_info": info,
        "tags": tags,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
