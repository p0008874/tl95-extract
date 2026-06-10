# Media, Rendering, Cursor, and Input

## BGM Through MCI

The BGM helper is now named `TLBgmMci`.

Important functions:

- `0x406CE0` `TLBgmMci_ctorTempMidiProbe`
- `0x406D80` `TLBgmMci_ProbeDeviceAndLength`
- `0x406E00` `TLBgmMci_CopyArchiveMidiToTempAndOpen`
- `0x406FC0` `TLBgmMci_PlayFromStart`
- `0x407040` `TLBgmMci_PollAndLoopIfEnded`
- `0x407100` `TLBgmMci_CloseDeviceAndDeleteTemp`
- `0x407180` `TLBgmMci_PauseOrResume`
- `0x407260` `TLBgmMci_StopCloseAndClearState`

The helper creates a temp MIDI path ending in `ADL.MID`. Script BGM data is copied from the MIDI archive into that temp file, then MCI opens it using the `ADLMIDI` alias. Playback state stores the last start position so pause/resume and looping can restart without re-reading the archive.

`0x407040` polls MCI status and loops the BGM when the current position reaches the known length. It is called from `TLMainFrame_TickAudioCursorRenderer`.

Script opcodes:

- `0x40C830` `TLScriptOp_61_LoadAndPlayBgm`: reads an 8-byte MIDI token, opens it from the archive, writes it to temp `ADL.MID`, and starts MCI playback.
- `0x40C930` `TLScriptOp_62_ReplayCurrentBgm`: restarts or resumes the existing BGM.
- `0x40C810`: mapped as opcode `0x60`, interacts with the wait/check BGM state used by the frame tick.

## PCM Through waveOut

The PCM helper is now named `TLPcmWaveOut`.

Important functions:

- `0x414780` `TLPcmWaveOut_ctorProbeDevice`
- `0x4147E0` `TLPcmWaveOut_LoadWaveFromStream`
- `0x4148F0` `TLPcmWaveOut_StartPreparedBuffer`
- `0x4149E0` `TLPcmWaveOut_StopAndFreeHeader`
- `0x414A70` `TLPcmWaveOut_CloseAndFreeBuffer`
- `0x414BB0` `TLPcmWaveOut_PauseOrRestart`
- `0x414BE0` `TLPcmWaveOut_CacheCurrentVolume`
- `0x414C80` `TLPcmWaveOut_RestoreCachedVolume`

Observed behavior:

- Constructor probes for output devices and caches volume state.
- Loading stops/free old playback, allocates global movable memory for sample data, reads the stream, derives WAVEFORMAT data, and opens `waveOut`.
- Starting playback allocates and locks a `WAVEHDR`, points it at the sample buffer, prepares it, and writes it.
- Stopping mutes/restores around `waveOutReset`, unprepares the header, and frees header memory.
- Closing frees the sample buffer and closes output.

Script opcodes:

- `0x40C9C0` `TLScriptOp_64_LoadAndMaybePlayPcm`: reads token/control bytes, opens a WAV resource through the sound archive manager, caches it in a scenario slot, and optionally starts playback.
- `0x40CC30` `TLScriptOp_65_PlayCachedPcmSlot`: starts an already cached PCM slot.
- `0x40CCF0` `TLScriptOp_66_PreparePcmByName`: prepares PCM by name and rewinds/retries when previous playback is still active.
- `0x40CDF0` `TLScriptOp_67_StartPreparedPcm`: starts the previously prepared PCM buffer and clears pending name state.
- `0x40CE60` `TLScript_LoadPcmStreamByName`: helper for resolving PCM token to stream/size.
- `0x40CED0` `TLScript_ShowPcmPlaybackError`: shows `Could not play PCM %s.` style error.

## MRS Images and Cursors

Image archive functions:

- `0x413F90` `TLMrsArchive_Open`
- `0x413FD0` `TLMrsArchive_DecodeImageToDib`

The MRS archive is opened from `DataDir` and used by renderer, graphics opcodes, and cursor creation.

Cursor functions:

- `0x407300` `TLCursorLibrary_LoadFramesFromMrs`
- `0x407570` `TLCursorLibrary_TickAnimation`
- `0x407BA0` `TLCursorBank_TickState`
- `0x40E460` `TLScriptOp_A8_LoadMouseCursorData`

`TLCursorLibrary_LoadFramesFromMrs` decodes an MRS image and converts 32x32 image pixels into Windows cursor AND/XOR mask planes before calling `CreateCursor`. Pixel value handling observed:

- One value sets the AND bit.
- Another value sets the XOR bit.
- Replacing an active frame destroys the old handle and updates current cursor state.

`TLScriptOp_A8_LoadMouseCursorData` reads start index, count, and an 8-byte resource token from the script, then loads cursor frames from the MRS path. Its failure string is `Couldn't find mouse data.`

## Renderer

The renderer child object is now named `TLRenderer`.

Important functions:

- `0x40EFB0` `TLRenderer_ctor`
- `0x40F130` `TLRenderer_InitPalettesAndSurfaces`
- `0x40F430` `TLRenderer_RealizePalette`
- `0x40F4A0` `TLRenderer_TickAndRender`
- `0x4105A0` `TLRenderer_InvalidateAndUpdate`
- `0x4134A0` `TLRenderer_OnPaint`
- `0x402D60` `TLGdi_Create8bppDibSection`
- `0x402F50` `TLGdi_BlitDibToDevice`

`TLRenderer_InitPalettesAndSurfaces` creates palettes, registers the child window through MFC, creates a 640x400 render child, and allocates three 8-bit DIB-backed surfaces. `TLRenderer_OnPaint` realizes the palette and blits a full or partial 640x400 DIB to the paint DC, or clears the client area when there is no active surface.

The renderer tick at `0x40F4A0` is large. Observed responsibilities:

- Input-driven state updates.
- Window/render child centering.
- Palette and surface animation.
- Dirty-rectangle management.
- Invalidation and update scheduling.

## Renderer Message Map

Some renderer message targets are labels inside larger IDA regions rather than standalone functions. They were line-commented:

- `0x4136A0`: `WM_MOUSEMOVE`
- `0x413840`: `WM_LBUTTONDOWN`
- `0x413A80`: `WM_LBUTTONUP`
- `0x413960`: `WM_RBUTTONDOWN`
- `0x413AF0`: `WM_RBUTTONUP`

These handlers update renderer/input state from client coordinates and button state.

## Input Helpers

`0x404550` is now `TLInput_MapKeyboardMouseAction`.

It samples:

- `GetAsyncKeyState`
- `GetKeyState`
- `GetCursorPos`
- `ScreenToClient`
- `GetClientRect`
- `PtInRect`

It maps Enter, Space, Esc, and mouse buttons into game action codes. Mouse actions only count when the cursor is inside the client rectangle.

`0x4086E0` is now `TLInput_WaitForLeftButtonRelease`. It waits for left-button release with `GetAsyncKeyState(1)` and handles capture release behavior.

