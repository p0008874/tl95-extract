# MRS Image Conversion

Date: 2026-06-10

## Converter

Converter script:

`tools/convert_mrs_to_png.py`

Run from the game directory for PNG:

```powershell
python tools\convert_mrs_to_png.py EXTRACTED\MRS -o CONVERTED\MRS_PNG
```

Run from the game directory for BMP:

```powershell
python tools\convert_mrs_to_png.py EXTRACTED\MRS -o CONVERTED\MRS_BMP --format bmp
```

The script writes PNG output to:

`CONVERTED\MRS_PNG\<name>.png`

It writes BMP output to:

`CONVERTED\MRS_BMP\<name>.bmp`

It also writes a manifest in each output directory:

`manifest.tsv`

The manifest records input path, output path, width, height, origin fields, and mode byte.

## Results

The conversion runs produced:

- 299 opaque RGB PNG files from the 299 extracted `.MRS` payloads.
- 299 opaque RGB BMP files from the same extracted `.MRS` payloads.

Sample verification:

- `AC010A.png`: 456x64
- `OTAKU.png`: 640x400
- `TRUMP2.png`: 640x400
- `CMK.png`: 32x32

All 299 generated PNGs were opened and verified with Pillow. Representative PNG files were checked as `RGB` with no alpha band and no PNG transparency metadata. `TRUMP2.png` was visually sampled and the palette/order is coherent.

All 299 generated BMPs were opened and verified with Pillow. Representative BMP files were checked as `RGB`, and `TRUMP2.bmp` starts with the `BM` BMP signature.

## Format Summary

The standalone converter is based on `TLMrsArchive_DecodeImageToDib` at `0x413FD0`.

Observed MRS image payload:

```c
struct MrsHeader {
  uint8_t signature_or_kind[4];  // high byte is mode; observed mode is 0
  int16_t width;
  int16_t height;
  int16_t origin_x;
  int16_t origin_y;
  uint8_t palette[256][3];       // file triple order is B, R, G
  uint8_t compressed_pixels[];
};
```

The game decodes into an 8-bit indexed, top-down DIB.

## Palette Mapping

The renderer does not install all 256 palette entries directly. It updates logical palette entries 1 through 247 and preserves system entries outside that range.

The converter's default `--palette-mode game` follows the renderer mapping:

- File palette color 0 becomes game palette index 247.
- File palette colors 1 through 246 become game palette indices 1 through 246.
- Palette index 0 is black.
- Palette entries 248 through 255 use the final file/system-color triples.

The script defaults to opaque RGB output:

```powershell
python tools\convert_mrs_to_png.py EXTRACTED\MRS -o CONVERTED\MRS_PNG --output-mode rgb
```

It also supports indexed palette output:

```powershell
python tools\convert_mrs_to_png.py EXTRACTED\MRS -o CONVERTED\MRS_PNG_INDEXED --output-mode indexed
```

Use `--transparent-index 0` only with `--output-mode indexed` if a transparent-background sprite export is desired. The current generated output in `CONVERTED\MRS_PNG` is opaque RGB with no transparency.

## Compression Summary

The pixel stream uses one-byte control commands:

- `00xxxxxx`: literal byte run. A zero length byte means the next byte extends the length.
- `01xxxxxx`: repeat the previous decoded pixel. A zero length byte means the next byte extends the length; the effective repeat count includes the game decoder's extra increment.
- `1xxxxxxx`: back-reference copy from previously decoded output. Low bits encode distance and high bits encode length, with an extended length byte when needed.

Some files, for example `OTAKU.MRS`, reach the exact expected DIB pixel count before a strict row-counter loop would finish. The standalone converter therefore stops at `width * height` decoded pixels, which matches the valid PNG image size.
