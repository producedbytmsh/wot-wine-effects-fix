# Building the patched DLL

The tested build uses CodeWeavers' CrossOver 26.3 source archive. Its Wine version file reports 11.0. Only the x86-64 Windows PE `ntdll.dll` is rebuilt; the matching Unix Wine component and DXMT libraries are retained.

## Requirements

- macOS on Apple Silicon, with Xcode Command Line Tools and Rosetta for the x86-64 runtime.
- GNU Bison 3 or newer; the tested version was 3.8.2.
- [LLVM-MinGW 20261104](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261104), the `ucrt-macos-universal` archive.
- [CrossOver 26.3 source](https://media.codeweavers.com/pub/crossover/source/crossover-sources-26.3.0.tar.gz), also listed on [CodeWeavers' source page](https://www.codeweavers.com/crossover/source).

The tested CrossOver source archive has SHA-256:

```text
ac99c8ca4b3848f3e81784135f023df266b61c2345726ea55a50b3e030dd6872
```

## Apply and compile

Extract the CrossOver source archive and LLVM-MinGW archive into a working directory outside this repository. The Wine source is under `sources/wine` in the extracted CrossOver archive.

Set these paths to the extracted directories and this checkout:

```sh
WINE_SOURCE='/absolute/path/to/sources/wine'
TOOLCHAIN='/absolute/path/to/llvm-mingw-20261104-ucrt-macos-universal'
FIX_REPO='/absolute/path/to/wot-wine-effects-fix'
BUILD_DIR='/absolute/path/to/wine-build'

patch --dry-run -d "$WINE_SOURCE" -p1 < "$FIX_REPO/wot-host-export.patch"
patch -d "$WINE_SOURCE" -p1 < "$FIX_REPO/wot-host-export.patch"

export PATH="$TOOLCHAIN/bin:/opt/homebrew/opt/bison/bin:$PATH"
export CC='/usr/bin/clang -arch x86_64'
export CXX='/usr/bin/clang++ -arch x86_64'

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
"$WINE_SOURCE/configure" --host=x86_64-apple-darwin --enable-win64 \
  --with-mingw=llvm-mingw --disable-tests --without-x --without-freetype \
  --without-gnutls --without-gstreamer --without-sdl --without-vulkan
make -j2 dlls/ntdll/x86_64-windows/ntdll.dll

"$TOOLCHAIN/bin/llvm-strip" --strip-debug \
  "$BUILD_DIR/dlls/ntdll/x86_64-windows/ntdll.dll"
```

The configure flags reproduce the isolated PE DLL build. They do not describe a complete replacement CrossOver distribution.

## Install in an isolated test setup

Use a private copy of the CrossOver 26.3 runtime and a separate test bottle. Keep their vendor DLLs for rollback. Do not replace the DLL inside the installed CrossOver application or the working game bottle.

The tested setup replaced `ntdll.dll` in both locations:

```text
<private-runtime>/lib/wine/x86_64-windows/ntdll.dll
<test-bottle>/drive_c/windows/system32/ntdll.dll
```

`<private-runtime>` is the CrossOver directory containing `bin/wine` and `lib/wine`, normally under `Contents/SharedSupport/CrossOver` in the application bundle. These paths describe the tested layout; confirm them in your own copy before replacing anything.

Compare the vendor and rebuilt export tables before deployment. All 1,463 named exports and their ordinals matched in the tested build. Run the three lookup checks in [TESTING.md](TESTING.md) before launching the game.

The stripped DLL from the tested build has SHA-256:

```text
ee4cf6c6adaa48458d934ad7725e0ac8da86658956219c7cb6e36adc51fbbad3
```

That is a reference for the tested artifact, not a guarantee that another toolchain produces identical bytes.

Set `WOT_HIDE_HOST_EXPORT=1` only on the game launch. To disable the behavior, omit the variable. To remove the patch entirely, close the game and restore both original DLLs.

Keep game updates separate from this test setup. If a test client shares its resource directory with the original installation, repair or update operations affect those shared resources.

## After a game update

A private client that shares the installed game's `res` directory must also use
matching executables and metadata. Updating the installed game alone leaves the
private `paths.xml` referring to removed packages and can prevent startup with
“Game resource path does not exist”.

Close the game and finish the update in the original installation. With Python
3.11 or newer, check and refresh the private copy:

```sh
python3 sync-client.py '/path/to/installed/World_of_Tanks_EU' \
  '/path/to/private/World_of_Tanks_EU' --check
python3 sync-client.py '/path/to/installed/World_of_Tanks_EU' \
  '/path/to/private/World_of_Tanks_EU' --include-mods
```

The helper requires the private `res` symlink to resolve to the installed client's
resources. It stages the root client files and `win64` before replacing them,
backs up replaced or obsolete files beside the private client, and rolls back if
replacement or verification fails. It refuses missing source packages or a running
WoT process. Keep Game Center closed during copying. Preferences, the Wine runtime,
and shared resources are outside the copied paths.

`--include-mods` also copies mods from the version paths in the new `paths.xml` and
`mods/configs`, backing up the private versions first. Omit it to retain private
mods. Mods must support the updated game; old-version replays may also stop working.
The check verifies the root client files, game executable and package availability;
it is not a full vendor integrity check. Re-run the export probes and verify startup
and effects after updating. The effects patch itself need not change for a resource
layout mismatch.
