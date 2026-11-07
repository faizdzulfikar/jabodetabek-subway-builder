"""Install this authored mod without replacing any existing mod directory."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = Path.home() / 'Library/Application Support/metro-maker4/mods'


def main():
    mods = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT
    if not mods.is_dir():
        raise SystemExit('Mods folder does not exist. Pass the folder shown by Settings → Mods.')
    if not (ROOT / 'assets/JKT.pmtiles').is_file():
        raise SystemExit('Build the map assets before installing.')
    # Desktop 1.7.2 reads JSON/binary through its own /data/{CODE} server.
    # Mount our compressed assets in that data directory without duplicating them.
    data_root = mods.parent / 'cities/data'
    if not data_root.is_dir():
        raise SystemExit('City data folder not found next to mods; use the actual game data folder.')
    data_target = data_root / 'JKT'
    if data_target.exists() or data_target.is_symlink():
        if not data_target.is_symlink() or data_target.resolve() != ROOT / 'assets/JKT':
            raise SystemExit(f'Refusing to replace existing city data: {data_target}')
    else:
        data_target.symlink_to(ROOT / 'assets/JKT', target_is_directory=True)
    target = mods / 'JKT'
    if target.is_symlink() and target.resolve() == ROOT / 'mod':
        print(f'Already installed: {target}')
        return
    if target.exists() or target.is_symlink():
        raise SystemExit(f'Refusing to overwrite existing content: {target}')
    target.symlink_to(ROOT / 'mod', target_is_directory=True)
    print(f'Installed authored mod: {target} → {ROOT / "mod"}')
    print('Start the map server, then reload mods and enable Jabodetabek in Settings → Mods.')


if __name__ == '__main__':
    main()
