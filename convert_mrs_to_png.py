#!/usr/bin/env python3
"""Convert TRUE LOVE 95 .MRS image payloads to standard image files.

This implements the decoder observed in T_LOVE95 WINDOWED.EXE at
TLMrsArchive_DecodeImageToDib (0x413FD0). The game decodes MRS files into
8-bit indexed, top-down DIB pixel data.
"""

from __future__ import annotations

import argparse
import csv
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


HEADER_SIZE = 12
PALETTE_SIZE = 256 * 3
PIXEL_STREAM_OFFSET = HEADER_SIZE + PALETTE_SIZE


@dataclass(frozen=True)
class MrsImage:
    width: int
    height: int
    origin_x: int
    origin_y: int
    mode: int
    palette: list[tuple[int, int, int]]
    pixels: bytes


class MrsDecodeError(ValueError):
    pass


def _read_u8(data: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(data):
        raise MrsDecodeError("unexpected EOF in compressed pixel stream")
    return data[pos], pos + 1


def _decode_palette(raw_palette: bytes, palette_mode: str) -> list[tuple[int, int, int]]:
    if len(raw_palette) != PALETTE_SIZE:
        raise MrsDecodeError("palette is not 768 bytes")

    # The game writes MRS triples into PALETTEENTRY fields as:
    #   stream byte 0 -> peBlue
    #   stream byte 1 -> peRed
    #   stream byte 2 -> peGreen
    # so the file triple order is B, R, G.
    raw = []
    for pos in range(0, PALETTE_SIZE, 3):
        blue, red, green = raw_palette[pos : pos + 3]
        raw.append((red, green, blue))

    if palette_mode == "raw":
        return raw

    # The renderer updates logical palette entries 1..247, while preserving
    # Windows/system entries outside that range. The decoder maps file color 0
    # to entry 247, colors 1..246 to entries 1..246, and skips the remaining
    # system-color triples.
    palette = [(0, 0, 0)] * 256
    for index in range(1, 247):
        palette[index] = raw[index]
    palette[247] = raw[0]
    for index in range(248, 256):
        palette[index] = raw[index]
    return palette


def decode_mrs(data: bytes, palette_mode: str = "game") -> MrsImage:
    if len(data) < PIXEL_STREAM_OFFSET:
        raise MrsDecodeError("file is too small for MRS header and palette")

    signature = data[:4]
    mode = signature[3]
    if mode not in (0, 4):
        raise MrsDecodeError(f"unsupported MRS mode byte {mode}")

    width, height, origin_x, origin_y = struct.unpack_from("<hhhh", data, 4)
    if width <= 0 or height <= 0:
        raise MrsDecodeError(f"invalid dimensions {width}x{height}")
    if width % 4 != 0:
        raise MrsDecodeError(f"unsupported non-DWORD-aligned width {width}")

    palette = _decode_palette(data[HEADER_SIZE:PIXEL_STREAM_OFFSET], palette_mode)
    pos = PIXEL_STREAM_OFFSET
    output = bytearray()
    total_pixels = width * height

    # The game's decoder tracks a per-row counter, but real files such as
    # OTAKU.MRS reach the exact expected pixel count before the nominal row loop
    # would finish. For standalone conversion, the stable termination condition
    # is the DIB pixel count.
    while len(output) < total_pixels:
        control, pos = _read_u8(data, pos)
        family = control & 0xC0

        if family == 0x00:
            count = control & 0x3F
            if count == 0:
                extra, pos = _read_u8(data, pos)
                count = extra + 64
            if pos + count > len(data):
                raise MrsDecodeError("literal run exceeds EOF")
            output.extend(data[pos : pos + count])
            pos += count

        elif family == 0x40:
            count = control & 0x3F
            if count == 0:
                extra, pos = _read_u8(data, pos)
                count = extra + 64
            count += 1
            if not output:
                raise MrsDecodeError("repeat run appears before first pixel")
            output.extend(bytes([output[-1]]) * count)

        else:
            distance_low, pos = _read_u8(data, pos)
            distance = ((control & 0x0F) << 8) | distance_low
            source = len(output) - distance - 1
            if source < 0:
                raise MrsDecodeError("back-reference points before output")

            length_code = (control >> 4) & 0x07
            if length_code:
                count = length_code + 2
            else:
                extra, pos = _read_u8(data, pos)
                count = extra + 10

            for _ in range(count):
                output.append(output[source])
                source += 1

        if len(output) > total_pixels:
            del output[total_pixels:]
            break

    if len(output) != total_pixels:
        raise MrsDecodeError(
            f"decoded {len(output)} pixels, expected {total_pixels}"
        )

    return MrsImage(
        width=width,
        height=height,
        origin_x=origin_x,
        origin_y=origin_y,
        mode=mode,
        palette=palette,
        pixels=bytes(output),
    )


def write_image(
    image: MrsImage,
    output_path: Path,
    transparent_index: int | None,
    output_mode: str,
    image_format: str,
) -> None:
    converted = Image.frombytes("P", (image.width, image.height), image.pixels)
    flat_palette: list[int] = []
    for red, green, blue in image.palette:
        flat_palette.extend((red, green, blue))
    converted.putpalette(flat_palette)
    if output_mode == "rgb" or image_format == "bmp":
        converted = converted.convert("RGB")
    elif transparent_index is not None:
        converted.info["transparency"] = transparent_index
    output_path.parent.mkdir(parents=True, exist_ok=True)
    converted.save(output_path, format=image_format.upper())


def iter_inputs(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            candidates = [*sorted(path.glob("*.MRS")), *sorted(path.glob("*.mrs"))]
        elif path.is_file():
            candidates = [path]
        else:
            raise FileNotFoundError(f"MRS input not found: {path}")
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(candidate)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert TRUE LOVE 95 MRS files.")
    parser.add_argument(
        "inputs",
        nargs="*",
        default=["EXTRACTED/MRS"],
        help="MRS files or directories. Default: EXTRACTED/MRS",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="CONVERTED/MRS_PNG",
        help="Output directory. Default: CONVERTED/MRS_PNG",
    )
    parser.add_argument(
        "--palette-mode",
        choices=("game", "raw"),
        default="game",
        help="Palette mapping. 'game' matches the renderer update path; 'raw' uses file order.",
    )
    parser.add_argument(
        "--transparent-index",
        type=int,
        default=None,
        help="Optional PNG transparent palette index for indexed output, commonly 0 for sprites.",
    )
    parser.add_argument(
        "--output-mode",
        choices=("rgb", "indexed"),
        default="rgb",
        help="PNG output mode. Default: rgb, which is fully opaque and has no transparency chunk.",
    )
    parser.add_argument(
        "--format",
        choices=("png", "bmp"),
        default="png",
        help="Output image format. BMP is always written as opaque RGB. Default: png",
    )
    parser.add_argument(
        "--manifest",
        default="manifest.tsv",
        help="Manifest filename under the output directory. Default: manifest.tsv",
    )
    args = parser.parse_args()

    if args.transparent_index is not None and not 0 <= args.transparent_index <= 255:
        raise ValueError("--transparent-index must be between 0 and 255")

    output_root = Path(args.output)
    inputs = iter_inputs(args.inputs)
    rows: list[dict[str, str | int]] = []

    for input_path in inputs:
        image = decode_mrs(input_path.read_bytes(), args.palette_mode)
        relative_name = input_path.with_suffix(f".{args.format}").name
        output_path = output_root / relative_name
        write_image(image, output_path, args.transparent_index, args.output_mode, args.format)
        rows.append(
            {
                "input": str(input_path),
                "output": str(output_path),
                "width": image.width,
                "height": image.height,
                "origin_x": image.origin_x,
                "origin_y": image.origin_y,
                "mode": image.mode,
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / args.manifest
    with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(
            manifest_file,
            fieldnames=("input", "output", "width", "height", "origin_x", "origin_y", "mode"),
            dialect="excel-tab",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Converted {len(rows)} MRS files to {args.format.upper()}")
    print(f"Output: {output_root}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
