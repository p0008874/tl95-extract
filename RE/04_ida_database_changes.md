# IDA Database Changes

## Type Work

Local type declarations were added for the main app-specific structures:

- `TLArchiveEntry`
- `TLArchive`
- `TLSoundArchives`
- `TLPcmWaveOut`
- `TLBgmMci`
- `TLScenarioState`
- `TLRenderer`
- `TLMainFrame`
- `TLApp`
- `TLCursorBank` forward declaration

Global config and runtime pointers were typed where observed, including:

- `g_tlApp` as `TLApp`
- `g_mainFrame` as `TLMainFrame *`
- path/title globals as `char *`
- app icon/cursor globals as pointer/handle-like values
- config string pointer table entries as `const char *`

## Key Function Names Applied

Startup and app:

- `TLApp_ctor` at `0x401010`
- `TLApp_InitInstance_CheckInstallAndCreateMainWindow` at `0x401170`
- `TLApp_ReadRegistryConfigAndValidateFiles` at `0x401370`
- `TLApp_CheckInstallIniTitle_BypassedDriveLoop` at `0x401650`
- `TLApp_ProbeDisplayAudioCapabilities` at `0x4017B0`
- `TLApp_OnIdleRunScriptTick` at `0x401A30`

Main frame:

- `TLMainFrame_ctor` at `0x4060D0`
- `TLMainFrame_Create640x480Window` at `0x406200`
- `TLMainFrame_InitGameSubsystems` at `0x4062F0`
- `TLMainFrame_OnActivatePauseResumeAudio` at `0x4067B0`
- `TLMainFrame_OnSizeAdjustPaletteAndDisplay` at `0x406830`
- `TLMainFrame_PreTranslateMessage` at `0x4069E0`
- `TLMainFrame_AdjustShowStateForClientSize` at `0x406A10`
- `TLMainFrame_OnCloseConfirm` at `0x406B10`
- `TLMainFrame_TickAudioCursorRenderer` at `0x406BA0`

Archives and script:

- `TLArchive_OpenAndLoadIndex` at `0x404A90`
- `TLArchive_OpenEntryByName` at `0x404D70`
- `TLArchive_CloseCurrentEntry` at `0x405130`
- `TLArchive_GetCurrentEntrySize` at `0x4051E0`
- `TLSoundArchives_ctor` at `0x408B80`
- `TLSoundArchives_OpenWavByName` at `0x408CA0`
- `TLScenarioState_ctor` at `0x408ED0`
- `TLScenarioState_IsReadyForNextOpcode` at `0x4093C0`
- `TLScenarioState_DispatchNextOpcode` at `0x409430`
- `TLScenarioState_LoadScriptByName` at `0x409C00`
- `TLScenario_ReadToken8` at `0x409D40`
- `TLScenario_JumpToSegment` at `0x409D90`
- `TLScenario_LoadEndStateFile` at `0x409E00`
- `TLScenario_SaveEndStateFile` at `0x409F70`

Media and rendering:

- `TLBgmMci_ctorTempMidiProbe` at `0x406CE0`
- `TLBgmMci_CopyArchiveMidiToTempAndOpen` at `0x406E00`
- `TLBgmMci_PlayFromStart` at `0x406FC0`
- `TLBgmMci_PollAndLoopIfEnded` at `0x407040`
- `TLPcmWaveOut_ctorProbeDevice` at `0x414780`
- `TLPcmWaveOut_LoadWaveFromStream` at `0x4147E0`
- `TLPcmWaveOut_StartPreparedBuffer` at `0x4148F0`
- `TLPcmWaveOut_StopAndFreeHeader` at `0x4149E0`
- `TLCursorLibrary_LoadFramesFromMrs` at `0x407300`
- `TLCursorLibrary_TickAnimation` at `0x407570`
- `TLRenderer_ctor` at `0x40EFB0`
- `TLRenderer_InitPalettesAndSurfaces` at `0x40F130`
- `TLRenderer_TickAndRender` at `0x40F4A0`
- `TLRenderer_OnPaint` at `0x4134A0`
- `TLMrsArchive_Open` at `0x413F90`
- `TLMrsArchive_DecodeImageToDib` at `0x413FD0`

Input:

- `TLInput_MapKeyboardMouseAction` at `0x404550`
- `TLInput_WaitForLeftButtonRelease` at `0x4086E0`

## Comments Added

Detailed comments were added at function starts and key line-level branch points for:

- Startup registry/config validation.
- The patched/bypassed `TRUELOVE.INI` title comparison and unreachable drive loop.
- Main-frame ownership of subsystem objects.
- Idle loop/script VM timing and opcode cap.
- Archive open/member lookup.
- Scenario load/decode and dispatcher format.
- Save/load slot and END. state handling.
- MCI BGM temp-file playback.
- PCM waveOut buffer/header lifecycle.
- MRS cursor conversion and cursor animation.
- Renderer palette/DIB setup and paint path.
- Message-map labels that are not independent IDA functions.

## Verification

After names, types, and comments were applied, Hex-Rays cache was forced to refresh for representative functions:

- `TLApp_InitInstance_CheckInstallAndCreateMainWindow`
- `TLApp_ReadRegistryConfigAndValidateFiles`
- `TLApp_CheckInstallIniTitle_BypassedDriveLoop`
- `TLApp_OnIdleRunScriptTick`
- `TLMainFrame_InitGameSubsystems`
- `TLScenarioState_DispatchNextOpcode`
- `TLScenarioState_LoadScriptByName`
- `TLScriptOp_61_LoadAndPlayBgm`
- `TLScriptOp_64_LoadAndMaybePlayPcm`
- `TLPcmWaveOut_LoadWaveFromStream`
- `TLRenderer_InitPalettesAndSurfaces`
- `TLRenderer_OnPaint`

Representative decompilation was spot-checked after the refresh. The updated names and prototypes are visible in the decompiler output, and the raw disassembly still confirms the patched/bypassed branch at `0x401775`.

## Remaining Work

- Complete semantic naming for every scenario opcode handler.
- Reverse the exact script header/decode transform in `TLScenarioState_LoadScriptByName`.
- Fully type the renderer and cursor-bank internal fields.
- Identify the exact class names for MFC-derived helper objects that currently remain as structural/behavioral names.

