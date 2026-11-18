# World of Tanks Wine effects fix

Enables the redesigned World of Tanks effects on macOS by hiding one Wine-specific function from the game.

Tested with the EU HD client **2.4.1.1 #993**, **CrossOver 26.3**, **DXMT**, and **MSync**. The effects appeared in replay tests and worked in live gameplay on Apple Silicon.

## What it changes

World of Tanks looks up `ntdll!wine_get_host_version` to detect Wine. When that lookup succeeds, the game sets an emulator flag that disables its prefab effects.

[wot-host-export.patch](wot-host-export.patch) changes Wine's `LdrGetProcedureAddress` so that this lookup returns `STATUS_PROCEDURE_NOT_FOUND` with a null address only when:

- The executable is named `WorldOfTanks.exe`, ignoring case.
- The process environment contains `WOT_HIDE_HOST_EXPORT=1`.

The check compares the resolved function address, so it also covers ordinal lookups. The DLL's export table stays intact. Other processes and launches without the option keep their normal behavior.

The game executable, resources, shaders, and DXMT are unchanged. The renderer already displays the effects once the game's Wine check stops blocking them.

## Use

This repository contains the source patch, not a ready-to-install DLL. See [BUILD.md](BUILD.md) for the tested build procedure and deployment notes.

With the patched DLL installed in a private runtime and bottle, launch the game with:

```sh
WOT_HIDE_HOST_EXPORT=1 /path/to/private/runtime/bin/wine \
  --bottle Effects-Test \
  --workdir 'C:\Games\World_of_Tanks_EU' \
  --cx-app 'C:\Games\World_of_Tanks_EU\win64\WorldOfTanks.exe' -safe
```

The environment variable has no effect on an unpatched Wine build. Close the game before changing DLLs or switching between patched and original runtimes.

## Results

The original Wine DLL blocked the effects. The patched DLL enabled them in the same replay. Restoring the original DLL restored Wine detection. Live gameplay was then tested successfully on 18 November 2026.

See [TESTING.md](TESTING.md) for the checks and remaining limitations. Metal pipeline errors still occur in the logs; this patch does not fix those errors or establish a performance improvement.

## Upstream

CodeWeavers could scope this behavior to World of Tanks through an application compatibility setting. Wargaming could remove or narrow the game's Wine-specific effects restriction. This is an independent workaround, not an official fix from either company.

## License

LGPL-2.1-or-later, matching Wine's `dlls/ntdll/loader.c`. See [LICENSE](LICENSE).
