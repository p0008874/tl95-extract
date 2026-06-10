# Archive Extraction

Date: 2026-06-10

## Extractor

Extractor script:

`tools/extract_true_love_archives.py`

Run from the game directory:

```powershell
python tools\extract_true_love_archives.py DATB DATE DATG DATR EFF MIDI MRS -o EXTRACTED
```

The script writes files under:

`EXTRACTED\<archive-name>\`

It also writes:

`EXTRACTED\manifest.tsv`

The manifest records archive name, entry index, original entry name, output name, entry offset, and extracted size.

## Archive Format

The archive format used by `DATB`, `DATE`, `DATG`, `DATR`, `EFF`, `MIDI`, and `MRS` is:

```c
struct ArchiveHeader {
  uint16_t index_size;
};

struct ArchiveEntry {
  char name[12];
  uint32_t offset;
};
```

Notes:

- `index_size` is little-endian and counts only directory bytes after the two-byte header.
- Each directory record is 16 bytes.
- `name` is NUL-padded and usually includes the extension.
- `offset` is an absolute file offset from the start of the archive.
- Entry size is calculated from the next entry offset.
- These archives include a final empty-name EOF sentinel record. The extractor uses it to size the final real entry and does not write it as a file.

## Extraction Results

The extraction run produced:

| Archive | Extracted files |
| --- | ---: |
| `DATB` | 118 |
| `DATE` | 118 |
| `DATG` | 118 |
| `DATR` | 118 |
| `EFF` | 16 |
| `MIDI` | 16 |
| `MRS` | 299 |
| Total | 803 |

Total extracted archive-entry bytes reported by the extractor:

`10407437`

The recursive file count under `EXTRACTED` is 804 because it includes the generated `manifest.tsv`.

## Validation Samples

Sample checks after extraction:

- `EXTRACTED\EFF\SE_009.WAV` starts with `RIFF` / `WAVEfmt`, matching a WAV payload.
- `EXTRACTED\MIDI\M014.MID` starts with `MThd`, matching a MIDI payload.
- `EXTRACTED\MRS\AC010A.MRS` starts with the game-specific MRS image payload header observed in the renderer/cursor paths.
- `EXTRACTED\DATB\REMI.DAT` starts with scenario/table payload bytes, consistent with script/archive data rather than a standard container.

