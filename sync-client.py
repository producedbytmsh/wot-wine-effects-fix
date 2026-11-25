#!/usr/bin/env python3
"""Refresh a private WoT client that shares the installed client's res directory."""
import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT_FILES = ('WorldOfTanks.exe', 'openwg.utils.dll', 'wgc_api.exe',
              'paths.xml', 'version.xml', 'loc_version.xml', 'app_type.xml',
              'game_info.xml', 'data.wgpdc')


def version(root):
    return ET.parse(root / 'version.xml').findtext('version', '').strip()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def packages(root):
    return [p.text.strip() for p in ET.parse(root / 'paths.xml').iter('Package')
            if p.text and p.text.strip()]


def check(source, target):
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Source and private client must be separate directories.')
    if not (target / 'res').is_symlink() or (target / 'res').resolve() != (source / 'res').resolve():
        raise ValueError('Private res must be a symlink to the source resources.')
    if not (source / 'win64/WorldOfTanks.exe').is_file():
        raise ValueError('Source game executable is missing.')
    missing = [p for p in packages(source) if not (source / p).is_file()]
    if missing:
        raise ValueError('Installed client has missing packages; finish its update first: ' + ', '.join(missing))
    changed = [name for name in ROOT_FILES + ('win64/WorldOfTanks.exe',)
               if (source / name).is_file() != (target / name).is_file()
               or ((source / name).is_file() and digest(source / name) != digest(target / name))]
    missing = [p for p in packages(target) if not (target / p).is_file()]
    return changed, missing


def sync(source, target, include_mods):
    # Never replace a directory used by a running client, including other bottles.
    rows = subprocess.check_output(['ps', '-axo', 'comm='], text=True)
    if 'WorldOfTanks.exe' in rows:
        raise ValueError('Close World of Tanks before refreshing the private client.')
    names = list(ROOT_FILES) + ['win64']
    mod_names = []
    if include_mods:
        for entry in ET.parse(source / 'paths.xml').iter('Path'):
            relative = Path((entry.text or '').strip())
            if relative.parts and relative.parts[0] in ('mods', 'res_mods'):
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Unsafe mod path in paths.xml.')
                mod_names.append(str(relative))
        if (source / 'mods/configs').is_dir():
            mod_names.append('mods/configs')
        names += list(dict.fromkeys(mod_names))
    for name in names:
        for root in (source, target):
            p = root / name
            if p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent != root and root in parent.parents):
                raise ValueError('Managed client paths must not be symlinks: ' + str(p))
    backup = target.parent / ('client-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir()
    # Stage before changing the private client. Never copy or write shared resources.
    with tempfile.TemporaryDirectory(prefix='.client-stage-', dir=target.parent) as temp:
        stage = Path(temp)
        for name in names:
            src, dst = source / name, stage / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('Logs', 'Reports', '*.log', '*.dmp', '.DS_Store'))
            elif src.is_file():
                shutil.copy2(src, dst)
        if version(source) != version(stage) or digest(source / 'paths.xml') != digest(stage / 'paths.xml') or digest(source / 'win64/WorldOfTanks.exe') != digest(stage / 'win64/WorldOfTanks.exe'):
            raise ValueError('Source changed during staging. Finish its update and retry.')
        moved, installed = [], []
        try:
            for name in names:
                dst, old, new = target / name, backup / name, stage / name
                old.parent.mkdir(parents=True, exist_ok=True)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    dst.rename(old)
                    moved.append(name)
                if new.exists():
                    new.rename(dst)
                    installed.append(name)
            changed, missing = check(source, target)
            if changed or missing:
                raise ValueError('Post-copy verification failed.')
        except BaseException:
            for name in reversed(installed):
                p = target / name
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            for name in reversed(moved):
                (backup / name).rename(target / name)
            raise
    print('Private client refreshed:', version(target))
    print('Rollback copy:', backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Installed client directory')
    parser.add_argument('target', type=Path, help='Private client directory with shared res symlink')
    parser.add_argument('--check', action='store_true', help='Read-only consistency check')
    parser.add_argument('--include-mods', action='store_true', help='Also copy active-version mods and mod configs (backed up first)')
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    try:
        changed, missing = check(source, target)
        print('Installed:', version(source), '| Private:', version(target))
        if args.check:
            if changed or missing:
                raise ValueError('Private client needs refresh. Changed: ' + ', '.join(changed) + '; missing packages: ' + str(len(missing)))
            print('Private executable, metadata and package references match the installed client.')
        else:
            sync(source, target, args.include_mods)
    except (ValueError, OSError, ET.ParseError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
