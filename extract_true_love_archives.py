#!/usr/bin/env python3
"""Extract TRUE LOVE 95 archive files.

Archive format observed in T_LOVE95 WINDOWED.EXE:
  u16le index_size
  repeated index_size / 16 records:
    char name[12]      # NUL padded, usually includes extension
    u32le offset       # absolute offset in archive file
  data blobs follow at the listed offsets; each size is next_offset - offset,
  with the final entry ending at EOF.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ARCHIVES = ("DATB", "DATE", "DATG", "DATR", "EFF", "MIDI", "MRS")
INDEX_HEADER_SIZE = 2
ENTRY_SIZE = 16
NAME_SIZE = 12


@dataclass(frozen=True)
class Entry:
    index: int
    name: str
    offset: int
    size: int
    output_name: str


def parse_index(data: bytes, archive_name: str) -> list[Entry]:
    if len(data) < INDEX_HEADER_SIZE:
        raise ValueError(f"{archive_name}: file is too small to contain an index")

    index_size = int.from_bytes(data[:INDEX_HEADER_SIZE], "little")
    index_start = INDEX_HEADER_SIZE
    index_end = index_start + index_size

    if index_size == 0 or index_size % ENTRY_SIZE != 0:
        raise ValueError(f"{archive_name}: invalid index size {index_size}")
    if index_end > len(data):
        raise ValueError(
            f"{archive_name}: index ends past EOF ({index_end} > {len(data)})"
        )

    raw_entries: list[tuple[str, int]] = []
    record_count = index_size // ENTRY_SIZE
    for idx, pos in enumerate(range(index_start, index_end, ENTRY_SIZE)):
        raw_name = data[pos : pos + NAME_SIZE]
        raw_offset = data[pos + NAME_SIZE : pos + ENTRY_SIZE]
        name = raw_name.split(b"\0", 1)[0].decode("cp932", errors="replace")
        offset = int.from_bytes(raw_offset, "little")
        if not name and idx != record_count - 1:
            raise ValueError(f"{archive_name}: empty name at index {idx}")
        raw_entries.append((name, offset))

    has_eof_sentinel = raw_entries[-1][0] == ""
    if has_eof_sentinel and raw_entries[-1][1] != len(data):
        raise ValueError(
            f"{archive_name}: EOF sentinel offset {raw_entries[-1][1]} "
            f"does not match file size {len(data)}"
        )

    offsets = [offset for _, offset in raw_entries]
    if offsets[0] != index_end:
        raise ValueError(
            f"{archive_name}: first data offset {offsets[0]} does not match "
            f"index end {index_end}"
        )
    if offsets != sorted(offsets):
        raise ValueError(f"{archive_name}: entry offsets are not sorted")
    if offsets[-1] > len(data):
        raise ValueError(f"{archive_name}: last offset is past EOF")

    content_entries = raw_entries[:-1] if has_eof_sentinel else raw_entries
    content_end_offsets = offsets[1:] if has_eof_sentinel else offsets[1:] + [len(data)]

    seen: dict[str, int] = {}
    entries: list[Entry] = []
    for idx, ((name, offset), end_offset) in enumerate(
        zip(content_entries, content_end_offsets)
    ):
        if end_offset < offset:
            raise ValueError(f"{archive_name}: negative size for {name}")

        count = seen.get(name, 0)
        seen[name] = count + 1
        output_name = name if count == 0 else f"{Path(name).stem}_{count}{Path(name).suffix}"

        entries.append(
            Entry(
                index=idx,
                name=name,
                offset=offset,
                size=end_offset - offset,
                output_name=safe_output_name(output_name),
            )
        )

    return entries


def safe_output_name(name: str) -> str:
    name = name.replace("\\", "_").replace("/", "_").replace(":", "_")
    name = name.replace("*", "_").replace("?", "_").replace('"', "_")
    name = name.replace("<", "_").replace(">", "_").replace("|", "_")
    return name.strip() or "unnamed.bin"


def extract_archive(path: Path, output_root: Path) -> list[Entry]:
    data = path.read_bytes()
    entries = parse_index(data, path.name)
    archive_output = output_root / path.name
    archive_output.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        output_path = archive_output / entry.output_name
        output_path.write_bytes(data[entry.offset : entry.offset + entry.size])

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract TRUE LOVE 95 archives.")
    parser.add_argument(
        "archives",
        nargs="*",
        default=list(DEFAULT_ARCHIVES),
        help="Archive files to extract. Defaults to the known game archives.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="EXTRACTED",
        help="Output directory. Default: EXTRACTED",
    )
    parser.add_argument(
        "--manifest",
        default="manifest.tsv",
        help="Manifest filename under the output directory. Default: manifest.tsv",
    )
    args = parser.parse_args()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / args.manifest

    rows: list[dict[str, str | int]] = []
    total_entries = 0
    total_bytes = 0

    for archive_arg in args.archives:
        archive_path = Path(archive_arg)
        if not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        entries = extract_archive(archive_path, output_root)
        total_entries += len(entries)
        total_bytes += sum(entry.size for entry in entries)
        print(f"{archive_path.name}: extracted {len(entries)} files")
        for entry in entries:
            rows.append(
                {
                    "archive": archive_path.name,
                    "index": entry.index,
                    "name": entry.name,
                    "output_name": entry.output_name,
                    "offset": entry.offset,
                    "size": entry.size,
                }
            )

    with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(
            manifest_file,
            fieldnames=("archive", "index", "name", "output_name", "offset", "size"),
            dialect="excel-tab",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Total: extracted {total_entries} files, {total_bytes} bytes")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
