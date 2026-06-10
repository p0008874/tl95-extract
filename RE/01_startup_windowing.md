# Startup, Configuration, and Windowing

## Runtime Startup

The executable starts at `0x415C52`, which is standard VC CRT entry code. Control flows through `_WinMain@16` at `0x41C444` into an MFC `AfxWinMain`-like path around `0x421C54`. The MFC layer obtains the thread/module state, calls the app virtual `InitInstance`, runs the message loop, and then calls exit/destructor paths.

The global app object is constructed at `0x401010` and is now named `TLApp_ctor`. It installs the app vtable, seeds runtime random state with `timeGetTime`, and initializes CString-like global path/title members. The main app object is at `0x430970` and is named `g_tlApp`.

## App Object Layout

Important `TLApp` fields observed through decompilation:

| Offset | Meaning |
| --- | --- |
| `+0xC0` | `DEVMODE` scratch/current display mode |
| `+0x154` | display capability/state flags |
| `+0x158` | fullscreen/window mode capability flag |
| `+0x15C` | palette animation/support flag |
| `+0x160` | `SaveDir` string pointer |
| `+0x164` | `DataDir` string pointer |
| `+0x168` | `VoiceDir` string pointer |
| `+0x16C` | `Title` string pointer |
| `+0x170` | `StartScenario` string pointer |
| `+0x174` | language id |
| `+0x178` | app icon handle |
| `+0x17C` | app cursor handle |
| `+0x180` | last tick time used by idle loop |

The corresponding globals were renamed as `g_saveDirCString`, `g_dataDirCString`, `g_voiceDirCString`, `g_windowTitleCString`, `g_startScenarioCString`, `g_languageId`, `g_appIcon`, and `g_appCursor`.

## InitInstance

`0x401170` is now `TLApp_InitInstance_CheckInstallAndCreateMainWindow`.

Observed behavior:

- Allocates and frees a large global memory block as an early availability probe.
- Calls `TLApp_ReadRegistryConfigAndValidateFiles`.
- Uses the configured title to find an existing window and bring it to the foreground when another instance is already running.
- Calls `TLApp_CheckInstallIniTitle_BypassedDriveLoop`.
- Calls `TLApp_ProbeDisplayAudioCapabilities`.
- Loads icon/cursor resources.
- Allocates and constructs the main frame object.
- Creates the game frame window.

Failure paths show resource/string-backed errors such as `Register information is not correct, please reinstall.` and `Put %s CD into the CD-ROM drive.`

## Registry and Config Validation

`0x401370` is now `TLApp_ReadRegistryConfigAndValidateFiles`.

This function opens:

`HKCU\SOFTWARE\PARSLEY\TRUELOVE`

It reads these values:

- `Title`
- `DataDir`
- `VoiceDir`
- `SaveDir`
- `StartScenario`
- `language`

It then validates files in the save directory using the `SAVE.` prefix and `END.` name. The pointer table at `0x42F248` was documented and typed as config string pointers.

## Install/CD/INI Check

`0x401650` is now `TLApp_CheckInstallIniTitle_BypassedDriveLoop`.

The intended behavior appears to be:

- Build a root path for drive probing.
- Use `GetDriveTypeA`.
- Build a `TRUELOVE.INI` path.
- Read `[SetupInfo] Title` with `GetPrivateProfileStringA`.
- Compare the INI title against the registry title using `__mbscmp`.
- Fall back to scanning drives if needed.

The observed build is patched or altered:

- The compare result is computed at `0x40175C`.
- `0x40176F` tests the result.
- `0x401775` immediately jumps to the cleanup/success path.
- The fallback drive loop beginning at `0x401777` is unreachable from normal flow.

This means the function effectively succeeds after the INI-read path, even though the old control-flow shape still contains a drive loop.

## Display and Audio Capability Probe

`0x4017B0` is now `TLApp_ProbeDisplayAudioCapabilities`.

Observed checks:

- Uses `GetDeviceCaps` to inspect color/palette conditions.
- Uses `EnumDisplaySettingsA` and `GetSystemMetrics` to find compatible display presentation options.
- Checks whether the app can run in a 640x480-compatible mode or adjusted windowed mode.
- Constructs/probes the PCM helper and the MCI MIDI helper.
- Prompts the user when MIDI or PCM playback is unavailable, allowing the app to continue without those capabilities.

Relevant user-visible strings:

- `Cannot use BGM because this system can not play MIDI files. Do you want to continue?`
- `Cannot play sound effects because this system can not play PCM files. Do you want to continue?`
- A prompt about needing 256 colors.

## Main Frame

The global main-frame pointer at `0x430AF4` is now `g_mainFrame`. The constructor at `0x4060D0` is now `TLMainFrame_ctor`.

Important observed fields:

| Offset | Meaning |
| --- | --- |
| `+0xBC` | PCM `waveOut` helper |
| `+0xC0` | MCI BGM/MIDI helper |
| `+0xC4` | sound archive manager |
| `+0xC8` | PCM loop/mode flag |
| `+0xCC` | MIDI archive |
| `+0xD0` | renderer child |
| `+0xD4` | scenario VM/state |
| `+0xD8` | message/text state |
| `+0xDC..+0xEC` | five cursor/state banks |
| `+0xF0` | active cursor bank |
| `+0xF4` | save helper |
| `+0xF8` | MRS image archive |
| `+0xFC` | helper object |
| `+0x100` | cursor library/manager |
| `+0x104` | PCM availability/state flag |
| `+0x108` | accelerator handle |
| `+0x10C` | captured system colors |
| `+0x110` | window style/state |

## Main Frame Creation

`0x406200` is now `TLMainFrame_Create640x480Window`.

It registers the game frame class through MFC, chooses the frame style based on the display-mode flag, adjusts the window rectangle for a 640x480 frame, creates the frame, and shows it either windowed or maximized depending on the startup display decision.

## Main Frame Subsystem Creation

`0x4062F0` is now `TLMainFrame_InitGameSubsystems`.

It constructs or initializes:

- Accelerator resource `0x84`
- WAV archive manager
- MIDI archive
- PCM `waveOut` helper
- MCI BGM helper
- 640x400 renderer child
- Message/text state object
- Five cursor/state banks
- Save helper
- MRS image archive
- Scenario VM
- Optional cursor library

This function is the main ownership hub for runtime objects.

## Main Frame Message Behavior

Documented handlers and message-map targets:

- `0x4067B0` `TLMainFrame_OnActivatePauseResumeAudio`: pauses/resumes MCI BGM and PCM playback on activation changes.
- `0x406830` `TLMainFrame_OnSizeAdjustPaletteAndDisplay`: handles palette use, display settings, invalidation, size adjustment, and renderer centering.
- `0x4069E0` `TLMainFrame_PreTranslateMessage`: gives `TranslateAcceleratorA` first chance, then falls back to MFC frame processing.
- `0x406A10` `TLMainFrame_AdjustShowStateForClientSize`: toggles/restores window state based on iconic/client size and display mode.
- `0x406AF0`: line-commented help command target, calls `WinHelpA(hwnd, "TLOVE.HLP", 3, 0)`.
- `0x406B10` `TLMainFrame_OnCloseConfirm`: formats `Quit %s. OK?` and only destroys the window on confirmation.
- `0x406BA0` `TLMainFrame_TickAudioCursorRenderer`: per-frame runtime tick for cursors, BGM state, cursor banks, and renderer.
- `0x406CA0`: line-commented `WM_SETCURSOR` target, delegates cursor selection to the cursor manager.

## Idle Loop

`0x401A30` is now `TLApp_OnIdleRunScriptTick`.

The function is an MFC idle callback/script pump:

- Uses elapsed time around 17 ms to tick frame-level audio/cursor/rendering.
- Does not dispatch scenario opcodes while the main frame is iconic.
- Asks `TLScenarioState_IsReadyForNextOpcode` before dispatch.
- Calls `TLScenarioState_DispatchNextOpcode`.
- Stops after 50 script operations in one idle cycle.
- If dispatch fails or requests shutdown, closes the frame and sets `g_shutdownRequested`.

