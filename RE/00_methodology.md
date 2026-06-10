# True Love 95 Reverse Engineering Notes - Methodology

Date: 2026-06-10

## Target

- IDB: `T_LOVE95 WINDOWED.EXE.i64`
- Input binary: `T_LOVE95 WINDOWED.EXE`
- Processor: 32-bit x86
- Image base: `0x400000`
- Entry point: `0x415C52`
- MD5: `357f85aad0ccef77d47a42f753419190`
- SHA-256: `754ae179e80bddc20e6d21088ec0c26c3e77f345090fee2ae420790e82099355`

The binary is an MFC/Win32 game executable. The application-specific logic is layered on top of VC/MFC runtime startup, CWinApp/CFrameWnd plumbing, WinMM audio, GDI palette/DIB rendering, archive loaders, and a scenario bytecode VM.

## Process Used

1. Started with the IDA MCP binary survey to avoid relying on stale names or comments.
2. Triaged imports, strings, globals, vtables, message maps, and highly referenced functions.
3. Followed cross-references from configuration strings, media error strings, and subsystem globals.
4. Decompilation was inspected first. Disassembly was used where Hex-Rays hid or simplified important control flow, especially in the install/CD check.
5. Used two read-only subagents to independently inspect:
   - Audio, archive, scenario, and rendering subsystems.
   - MFC startup, window/message-map behavior, renderer message handlers, and input.
6. Applied names, local type declarations, function prototypes, and comments in the IDB only after the behavior was observed in decompilation/disassembly.
7. Forced Hex-Rays cache refresh for representative functions and spot-checked the updated output.

## Number Handling

Number-base conversions were not performed manually. Values with both hexadecimal and decimal forms were taken from MCP tool output, especially `int_convert`, `analyze_batch`, `get_int`, or IDA-rendered metadata. Where a value is only written in one base, it is the observed form from IDA/tool output.

## Accuracy Notes

- Old names and comments were not treated as authoritative.
- The install/CD check at `0x401650` is documented from raw disassembly because the decompiler elides the unreachable fallback path.
- The scenario dispatcher has many handlers. High-confidence handler names were applied where behavior was directly inspected. Remaining handler addresses are mapped, but not all were semantically named.
- Some MFC message-map targets are labels inside larger IDA function regions rather than separate functions. Those addresses received line comments instead of forced function boundaries.

## Main Components Identified

- `TLApp`: global CWinApp-derived object at `0x430970`.
- `TLMainFrame`: main CFrameWnd-derived game frame, global pointer at `0x430AF4`.
- `TLArchive`: fixed-token archive/index loader used by scenario, graphics, MIDI, and WAV resources.
- `TLScenarioState`: bytecode VM and save/end-state owner.
- `TLBgmMci`: MIDI/BGM playback through temp `ADL.MID` and MCI.
- `TLPcmWaveOut`: PCM/WAV playback through `waveOut`.
- `TLRenderer`: 640x400 8-bit child renderer with palette/DIB surfaces.
- Cursor manager/library paths: MRS image conversion into Win32 cursor AND/XOR masks.

