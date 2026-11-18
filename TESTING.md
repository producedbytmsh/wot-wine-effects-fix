# Test record

Tested on 18 November 2026 with World of Tanks EU HD `2.4.1.1 #993`, CrossOver 26.3, DXMT, MSync, Safe Mode, and High Presets Graph. Replay checks were performed on an M2 MacBook with 8 GB RAM. Live gameplay was subsequently tested on a Mac mini M4.

## Export lookup checks

With the source-built DLL, the following `GetProcAddress` checks passed:

| Process | `WOT_HIDE_HOST_EXPORT` | `wine_get_host_version` | `NtClose` |
| --- | --- | --- | --- |
| A differently named probe | `1` | Present | Present |
| Probe named `WorldOfTanks.exe` | Unset | Present | Present |
| Probe named `WorldOfTanks.exe` | `1` | Absent | Present |

The real `wine_get_host_version` export remains in the DLL. The old diagnostic alias `wine_get_host_versio_` is absent. All 1,463 named exports and their ordinals match the vendor DLL.

## Game checks

1. The vendor baseline loaded the replay and logged Wine/emulator detection.
2. An initial diagnostic export rename removed detection and enabled visible redesigned effects.
3. Restoring the vendor DLL restored detection.
4. The source-built, per-process patch removed detection and enabled the same visible effects without renaming the export.
5. Normal live gameplay worked with the source patch. The session exited with code 0. The original game executable, original bottle configuration, registry, preferences, and original bottle Wine DLL passed the watched-file integrity checks.

Visual checks were manual. No comparison video, Windows reference, or controlled frame-time benchmark was captured. Replay preferences had VSync enabled.

## Known limitations

Metal pipeline creation errors involving `float4`/`int4` outputs and `R16Uint`/`R32Uint` attachments remain in the logs. An `R32Uint` error also occurred in the vendor baseline. The live test showed no reported visible problem, but it does not establish that every rendering pass is correct.

This patch removes a game-side effects restriction. It does not change DXMT, fix those pipeline errors, or prove equal performance between the two modes. Other game versions, Wine versions, and renderers have not been validated.

## Reference hashes

| File | SHA-256 |
| --- | --- |
| Tested `win64/WorldOfTanks.exe` | `58325ded3e2db7134638971e33de1eab09737f8b66401554d9723a2bf246bb11` |
| Vendor x86-64 PE `ntdll.dll` | `6dff64c00793ce92124f1316985c63783f539f26b392975c70f57637458d2387` |
| Patched, debug-stripped `ntdll.dll` | `ee4cf6c6adaa48458d934ad7725e0ac8da86658956219c7cb6e36adc51fbbad3` |
