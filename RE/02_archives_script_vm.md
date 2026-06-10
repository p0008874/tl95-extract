# Archives, Scenario VM, and Save State

## Archive Layer

The generic archive object is now named `TLArchive`. The main archive functions are:

- `0x404A90` `TLArchive_OpenAndLoadIndex`
- `0x404D70` `TLArchive_OpenEntryByName`
- `0x405130` `TLArchive_CloseCurrentEntry`
- `0x4051E0` `TLArchive_GetCurrentEntrySize`

`TLArchive_OpenAndLoadIndex` builds a path from `baseDir`, archive name, and extension, opens the archive file, reads the directory/index, and keeps the directory in global movable memory.

`TLArchive_OpenEntryByName` searches fixed-size name tokens, computes the entry size from this entry offset and the next entry offset, and opens the relevant stream region. If an archive entry is missing, it can fall back to opening a loose file path. Missing resource failures use formatted UI error strings.

The observed index entry shape was modeled as:

```c
typedef struct TLArchiveEntry {
  char name[12];
  unsigned int offset;
} TLArchiveEntry;
```

## Resource Archive Usage

Observed resource groups:

- Scenario scripts: `DATE.DAT`, `DATG.DAT`, or `DATF.DAT`
- MIDI/BGM: `MIDI.MID` archive path
- PCM/effects and voice: WAV archives under data/voice directories
- Images: `MRS.MRS`

`0x408B80` `TLSoundArchives_ctor` opens the effect WAV archive and the voice WAV archive. `0x408CA0` `TLSoundArchives_OpenWavByName` resolves a script PCM token into the selected archive and returns the stream plus size.

## Scenario State

`0x408ED0` is now `TLScenarioState_ctor`.

Observed responsibilities:

- Allocates a 64KB script buffer with `GlobalAlloc`.
- Chooses the scenario archive based on language/config state.
- Initializes VM execution flags and state fields.
- Loads persistent `END.` state from `SaveDir`.
- Records media availability flags based on startup probes.

`0x4093C0` `TLScenarioState_IsReadyForNextOpcode` gates execution. It handles the special state that loads the start scenario and waits for all five cursor banks to finish pending activity before allowing the dispatcher to execute another opcode.

## Script Loading

`0x409C00` is now `TLScenarioState_LoadScriptByName`.

Observed behavior:

- Opens a named script entry from the active scenario archive.
- Reads the script into the 64KB buffer.
- Sets error/stop state on read failure.
- Handles a header/magic-controlled decode or scramble path before execution starts.

The detailed transformation inside the decode path was not fully renamed. The presence of header/magic checks and byte manipulation was verified from decompilation and constants, but the exact format should be treated as future work.

## Token and Jump Helpers

`0x409D40` `TLScenario_ReadToken8` reads up to 8 bytes from the current script operand stream. It stops on NUL, carriage return, or space and zero-terminates the output. Media handlers and branch handlers use this for resource names.

`0x409D90` `TLScenario_JumpToSegment` uses the script header/table to set the VM PC to a segment offset.

## Bytecode Dispatcher

`0x409430` is now `TLScenarioState_DispatchNextOpcode`.

Instruction format observed:

- If `currentOpcode` is idle, read one opcode byte from `pc`.
- Read operand length.
- If the high bit of the length byte is set, decode an extended two-byte length.
- Store the operand pointer for the handler.
- Dispatch through a large jump table.
- If the handler returns success and has not set a special opcode state, advance `pc` by the operand length and return to idle opcode state.

The idle loop calls the dispatcher repeatedly, but caps dispatches at 50 operations per idle cycle.

## Opcode Map

The following map was extracted from the dispatcher jump table. Names are only applied where behavior was inspected directly; otherwise the table records target addresses.

| Opcode | Target | Notes |
| --- | --- | --- |
| `0x10` | `0x40A020` | `TLScriptOp_10_BeginBlockAtCurrentPc` |
| `0x12` | `0x40A050` | handler mapped |
| `0x13` | `0x40A130` | handler mapped |
| `0x14` | `0x40A160` | `TLScriptOp_14_SetBranchResumePointer` |
| `0x15` | `0x40A1B0` | handler mapped |
| `0x16` | `0x40A340` | handler mapped |
| `0x17` | `0x40A3C0` | handler mapped |
| `0x18` | `0x40A430` | handler mapped |
| `0x19` | `0x40A4E0` | handler mapped |
| `0x1A` | `0x40A580` | handler mapped |
| `0x1B` | `0x40A600` | handler mapped |
| `0x20` | `0x40A6A0` | handler mapped |
| `0x21` | `0x40A6A0` | same target as `0x20` |
| `0x22` | `0x40A6A0` | same target as `0x20` |
| `0x23` | `0x40A6B0` | `TLScriptOp_23_SaveScenarioSlot` |
| `0x24` | `0x40A980` | `TLScriptOp_24_LoadScenarioSlot` |
| `0x28` | `0x40AC90` | `TLScriptOp_28_JumpToScriptSegment` |
| `0x29` | `0x40ACD0` | handler mapped |
| `0x2A` | `0x40AD30` | `TLScriptOp_2A_RandomBranch` |
| `0x2B` | `0x40ADF0` | handler mapped |
| `0x30` | `0x40AE40` | handler mapped |
| `0x31` | `0x40AE70` | handler mapped |
| `0x32` | `0x40AEE0` | handler mapped |
| `0x33` | `0x40AF40` | handler mapped |
| `0x34` | `0x40AFF0` | handler mapped |
| `0x35` | `0x40B040` | handler mapped |
| `0x36` | `0x40B070` | handler mapped |
| `0x38` | `0x40B970` | handler mapped |
| `0x39` | `0x40B9C0` | handler mapped |
| `0x3A` | `0x40B9F0` | handler mapped |
| `0x3B` | `0x40BCA0` | handler mapped |
| `0x3C` | `0x40BD10` | handler mapped |
| `0x40` | `0x40BEF0` | handler mapped |
| `0x41` | `0x40BF70` | handler mapped |
| `0x42` | `0x40BFF0` | handler mapped |
| `0x43` | `0x40C0A0` | handler mapped |
| `0x44` | `0x40C170` | handler mapped |
| `0x45` | `0x40C250` | handler mapped |
| `0x48` | `0x40C2D0` | handler mapped |
| `0x49` | `0x40C310` | handler mapped |
| `0x4A` | `0x40C370` | handler mapped |
| `0x4B` | `0x40C420` | handler mapped |
| `0x4C` | `0x40C4A0` | handler mapped |
| `0x4D` | `0x40C530` | handler mapped |
| `0x50` | `0x40C590` | handler mapped |
| `0x51` | `0x40C610` | handler mapped |
| `0x52` | `0x40C670` | handler mapped |
| `0x53` | `0x40C6D0` | handler mapped |
| `0x54` | `0x40C780` | handler mapped |
| `0x60` | `0x40C810` | wait/check BGM state path |
| `0x61` | `0x40C830` | `TLScriptOp_61_LoadAndPlayBgm` |
| `0x62` | `0x40C930` | `TLScriptOp_62_ReplayCurrentBgm` |
| `0x63` | `0x40C990` | handler mapped |
| `0x64` | `0x40C9C0` | `TLScriptOp_64_LoadAndMaybePlayPcm` |
| `0x65` | `0x40CC30` | `TLScriptOp_65_PlayCachedPcmSlot` |
| `0x66` | `0x40CCF0` | `TLScriptOp_66_PreparePcmByName` |
| `0x67` | `0x40CDF0` | `TLScriptOp_67_StartPreparedPcm` |
| `0x70` | `0x40CF10` | handler mapped |
| `0x71` | `0x40CF70` | handler mapped |
| `0x72` | `0x40D060` | handler mapped |
| `0x73` | `0x40D0A0` | handler mapped |
| `0x75` | `0x40D110` | handler mapped |
| `0x76` | `0x40D1B0` | handler mapped |
| `0x80` | `0x40D1F0` | handler mapped |
| `0x81` | `0x40D240` | handler mapped |
| `0x82` | `0x40D290` | handler mapped |
| `0x83` | `0x40D380` | handler mapped |
| `0x84` | `0x40D3C0` | handler mapped |
| `0x85` | `0x40D410` | handler mapped |
| `0x86` | `0x40D490` | handler mapped |
| `0x87` | `0x40D540` | handler mapped |
| `0x88` | `0x40D590` | handler mapped |
| `0x89` | `0x40D5E0` | handler mapped |
| `0x8A` | `0x40D620` | handler mapped |
| `0x90` | `0x40D630` | handler mapped |
| `0x91` | `0x40D820` | handler mapped |
| `0x92` | `0x40D850` | handler mapped |
| `0x94` | `0x40D8E0` | handler mapped |
| `0x95` | `0x40D960` | handler mapped |
| `0x97` | `0x40DAC0` | handler mapped |
| `0x98` | `0x40DB00` | handler mapped |
| `0x99` | `0x40DC60` | handler mapped |
| `0x9A` | `0x40DE30` | handler mapped |
| `0x9B` | `0x40DED0` | handler mapped |
| `0x9D` | `0x40DF80` | handler mapped |
| `0xA0` | `0x40E010` | handler mapped |
| `0xA2` | `0x40E040` | handler mapped |
| `0xA3` | `0x40E110` | handler mapped |
| `0xA4` | `0x40E190` | handler mapped |
| `0xA5` | `0x40E1E0` | handler mapped |
| `0xA6` | `0x40E2D0` | handler mapped |
| `0xA7` | `0x40E330` | handler mapped |
| `0xA8` | `0x40E460` | `TLScriptOp_A8_LoadMouseCursorData` |
| `0xA9` | `0x40E4F0` | handler mapped |
| `0xAA` | `0x40E5B0` | handler mapped |
| `0xAB` | `0x40E6C0` | cursor positioning path observed |
| `0xAC` | `0x40E770` | handler mapped |
| `0xAD` | `0x40E7B0` | handler mapped |
| `0xAE` | `0x40E8B0` | handler mapped |
| `0xFF` | dispatcher return/default | stop/end style path |

Unlisted opcode values fall into the dispatcher's default path at `0x40996A`.

## Save and End State

`0x409E00` `TLScenario_LoadEndStateFile` and `0x409F70` `TLScenario_SaveEndStateFile` operate on `END.` under `SaveDir`. This appears to persist completion/progress flags separate from numbered scenario saves.

`0x40A6B0` `TLScriptOp_23_SaveScenarioSlot` and `0x40A980` `TLScriptOp_24_LoadScenarioSlot` handle numbered `SAVE.` records. The slot id is decoded from script bytes, then the handler opens/seeks the matching save record and writes or restores VM/cursor/scenario state.

## VM-Related Globals

- `g_shutdownRequested` at `0x430AF8`: set when the idle loop should stop dispatching and close the app.
- `g_scriptOpsThisTick` at `0x430AFC`: per-idle-cycle opcode counter, capped at 50.
- `g_startScenarioCString`: configured startup script name.
- `g_languageId`: selects language/archive variant.

