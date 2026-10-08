#!/usr/bin/env python3
"""CS:Source Mode for GTA San Andreas - installer / uninstaller.

Builds every game asset the mod needs from YOUR OWN copies of Counter-Strike: Source and GTA San Andreas
(nothing from either game is shipped with the mod), then installs the result into the GTA folder.

  python install.py                      interactive install (finds the games through Steam)
  python install.py --gta "D:\\Games\\GTA San Andreas" --css "D:\\Steam\\steamapps\\common\\Counter-Strike Source"
  python install.py --uninstall          remove the mod again
  python install.py --build-only OUTDIR  only build the files into OUTDIR (nothing in the GTA folder changes)
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

MOD_VERSION = '1.0.0'
SCRIPT_DIR = r'cleo\cssource[mem][dll]'       # [mem][dll] = CLEO Redux permissions for memory access / DLL calls
SOUND_DIR = r'cleo\cssource\sound'
BACKUP_DIR = 'cssource_backup'
MANIFEST = os.path.join(BACKUP_DIR, 'installed.json')
GTA_STEAM_NAMES = ['Grand Theft Auto San Andreas', 'GTA San Andreas']
CSS_STEAM_NAMES = ['Counter-Strike Source']
GTA_FILES = ['spraycan.dff', 'spraycan.txd', 'male01.dff', 'csplay.dff']   # from models/gta3.img
REQUIRED = [('CLEO.asi', 'CLEO 5 (cleo.li)'), ('cleo_redux.asi', 'CLEO Redux (re.cleo.li)'),
            ('III.VC.SA.LimitAdjuster.asi', 'Open Limit Adjuster (github.com/GTAmodding/III.VC.SA.LimitAdjuster)')]


def log(*a):
    print(*a, flush=True)


def ask(q, default=None):
    try:
        v = input(f'{q}{f" [{default}]" if default else ""}: ').strip().strip('"')
    except EOFError:
        v = ''
    return v or default


def yes(q, default=True, assume=None):
    if assume is not None:
        return assume
    v = ask(f'{q} ({"Y/n" if default else "y/N"})')
    return default if not v else v.lower().startswith('y')


# ------------------------------------------------------------------ finding the games
def steam_libraries():
    roots = []
    if sys.platform == 'win32':
        try:
            import winreg
            for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                              (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam'),
                              (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam')):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        for val in ('SteamPath', 'InstallPath'):
                            try:
                                roots.append(os.path.normpath(winreg.QueryValueEx(k, val)[0]))
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
        roots += [r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam']
    else:
        roots += [os.path.expanduser('~/.steam/steam'), os.path.expanduser('~/.local/share/Steam')]
    libs = []
    for r in roots:
        vdf = os.path.join(r, 'steamapps', 'libraryfolders.vdf')
        cand = [r]
        if os.path.isfile(vdf):
            cand += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='replace').read())]
        for c in cand:
            c = os.path.normpath(c)
            if os.path.isdir(os.path.join(c, 'steamapps')) and c not in libs:
                libs.append(c)
    return libs


def find_game(names, check):
    for lib in steam_libraries():
        for n in names:
            p = os.path.join(lib, 'steamapps', 'common', n)
            if check(p):
                return p
    return None


def css_vpks(css):
    return [os.path.join(css, 'cstrike', 'cstrike_pak_dir.vpk')]


def is_css_dir(p):
    return bool(p) and os.path.isfile(os.path.join(p, 'cstrike', 'cstrike_pak_dir.vpk'))


def game_running():
    if sys.platform != 'win32':
        return False
    try:
        out = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
        return 'gta_sa.exe' in out or 'gta-sa.exe' in out
    except OSError:
        return False


# ------------------------------------------------------------------ build
def build(gta, css, out_dir, work_dir):
    from csmod import deps, gtadir, rw
    deps.ensure_sourceio(os.path.join(HERE, '_deps'), log)
    from csmod import hud, phoenix, sounds, viewmodels, vpk

    t0 = time.time()
    fs = vpk.SourceFS(css_vpks(css))
    css_dir = os.path.join(work_dir, 'css')
    need = viewmodels.css_files() + phoenix.CSS_FILES
    missing = [p for p in need if not fs.has(p)]
    if missing:
        raise SystemExit('These files are missing from your CS:S install (verify the game files in Steam):\n  ' + '\n  '.join(missing))
    log(f'Extracting {len(need)} model/texture files from CS:S ...')
    for p in need:
        fs.extract(p, os.path.join(css_dir, *p.split('/')))

    log('Reading GTA files ...')
    g3 = rw.read_img(gtadir.find_file(gta, 'models/gta3.img'), GTA_FILES)
    for n in GTA_FILES:
        if n not in g3:
            raise SystemExit(f'{n} not found in models/gta3.img')
    with open(gtadir.find_file(gta, 'models/fronten_pc.txd'), 'rb') as f:
        fronten = f.read()

    ids = gtadir.FreeIds(gta)
    log(f'{len(ids.free)} free model IDs')
    os.makedirs(os.path.join(out_dir, 'models', 'txd'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'data', 'cssource'), exist_ok=True)
    out = viewmodels.Output(os.path.join(out_dir, 'models', 'cssource.img'), ids)

    log('Building the weapon viewmodels (this takes a few minutes) ...')
    vmdata = viewmodels.build_weapons(css_dir, out, log)
    vmdata['spray'] = viewmodels.build_spray(css_dir, out, g3['spraycan.dff'], g3['spraycan.txd'], log)

    log('Building the Phoenix player model ...')
    phx_base = os.path.join(css_dir, 'models', 'player', 't_phoenix')
    out.img.add('csphoenix.dff', phoenix.build_dff(g3['male01.dff'], phx_base))
    out.img.add('csphoenix.txd', phoenix.build_txd(fs.read('materials/models/player/t_phoenix/t_phoenix.vtf')))
    out.img.add('csphxcut.dff', phoenix.build_dff(g3['csplay.dff'], phx_base))
    phx_id, cut_id = ids.take(), ids.take()
    out.peds.append(f'{phx_id}, csphoenix, csphoenix, CIVMALE, STAT_SENSIBLE_GUY, man, 0, 0, man, 1,4, PED_TYPE_GEN, VOICE_GEN_MALE01, VOICE_GEN_MALE01')
    out.hier.append(f'{cut_id}, csphxcut, csphoenix, null, 2000.0')

    out.img.add('cssource.col', out.cols)        # collision archive inside the IMG (a gta.dat COLFILE line crashes)
    n_entries = out.img.close()
    ide = ['# CS:Source Mode - generated by the installer', 'objs', *out.objs, 'end', 'peds', *out.peds, 'end', 'hier', *out.hier, 'end']
    with open(os.path.join(out_dir, 'data', 'cssource', 'cssource.ide'), 'w', newline='') as f:
        f.write('\r\n'.join(ide) + '\r\n')
    log(f'  models/cssource.img: {n_entries} files, {ids.count} model IDs')

    log('Building the HUD textures ...')
    with open(os.path.join(out_dir, 'models', 'txd', 'cshud.txd'), 'wb') as f:
        f.write(hud.build(fs.read, fronten))

    log('Copying the sounds ...')
    snd_ev = sounds.install(fs.read, css_dir, viewmodels.WEAP, os.path.join(out_dir, *SOUND_DIR.split('\\')), log)

    log('Writing the script ...')
    with open(os.path.join(ROOT, 'script', 'index.template.js'), encoding='utf-8') as f:
        tpl = f.read()
    gen = ('// ---- generated by the installer from your own game files (do not edit) ----\n'
           f'const VMDATA = {json.dumps(vmdata, separators=(",", ":"))};\n'
           f'const SND_EV = {json.dumps(snd_ev, separators=(",", ":"))};\n'
           f'const PHX_ID = {phx_id};       // ped "csphoenix"\n'
           f'const PHX_CUT_ID = {cut_id};   // hier "csphxcut" (cutscene player)\n')
    tpl = re.sub(r'^// @@GENERATED_DATA@@.*$', lambda m: gen.rstrip('\n'), tpl, count=1, flags=re.M)
    if 'const VMDATA' not in tpl:
        raise SystemExit('script template is missing the @@GENERATED_DATA@@ marker')
    sdir = os.path.join(out_dir, *SCRIPT_DIR.split('\\'))
    os.makedirs(sdir, exist_ok=True)
    with open(os.path.join(sdir, 'index.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(tpl)
    log(f'Build finished in {time.time() - t0:.0f} s')
    return {'model_ids': ids.count}


# ------------------------------------------------------------------ install / uninstall
def files_in(d):
    for base, _, names in os.walk(d):
        for n in names:
            yield os.path.relpath(os.path.join(base, n), d)


def install(gta, css, assume=None):
    from csmod import gtadir
    exe, size = gtadir.exe_info(gta)
    if size != gtadir.GTA_10US_SIZE:
        log(f'WARNING: {exe or "gta_sa.exe"} is not the 1.0 US executable (size {size}, expected {gtadir.GTA_10US_SIZE}).')
        log('         The mod only works with GTA SA 1.0 US. Downgrade first (see README).')
        if assume or not yes('Continue anyway?', False):
            return 1
    for fn, what in REQUIRED:
        if not os.path.isfile(gtadir.find_file(gta, fn)):
            log(f'WARNING: {fn} not found - install {what} first (see README).')
    if game_running():
        raise SystemExit('GTA San Andreas is running. Close it and run the installer again.')

    work = os.path.join(HERE, '_work')
    stage = os.path.join(work, 'out')
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    info = build(gta, css, stage, work)

    bdir = os.path.join(gta, BACKUP_DIR)
    os.makedirs(bdir, exist_ok=True)
    first = os.path.join(bdir, 'gta.dat.original')
    if not os.path.isfile(first):
        shutil.copy2(gtadir.find_file(gta, 'data/gta.dat'), first)
    ola = gtadir.find_file(gta, 'III.VC.SA.LimitAdjuster.ini')
    if os.path.isfile(ola) and not os.path.isfile(os.path.join(bdir, 'LimitAdjuster.ini.original')):
        shutil.copy2(ola, os.path.join(bdir, 'LimitAdjuster.ini.original'))
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    legacy_cleanup(gta, os.path.join(bdir, 'legacy-' + stamp))

    log('Installing into the GTA folder ...')
    installed = []
    for rel in files_in(stage):
        dst = os.path.join(gta, rel)
        if os.path.isfile(dst) and rel.lower().endswith('index.js'):
            shutil.copy2(dst, dst + '.bak')              # keep the user's edited settings
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(stage, rel), dst)
        installed.append(rel)
    gtadir.patch_gta_dat(gta, True)
    atomic = 14000 + info['model_ids'] + 2000
    if gtadir.patch_limit_adjuster(gta, atomic):
        log(f'Open Limit Adjuster: AtomicModels >= {atomic}, MemoryAvailable >= 512, DebugTextKey off')
    with open(os.path.join(gta, MANIFEST), 'w') as f:
        json.dump({'version': MOD_VERSION, 'date': stamp, 'files': installed}, f, indent=1)
    shutil.rmtree(stage, ignore_errors=True)
    log('\nDone! Start the game: CS mode switches on by itself whenever you are on foot (F2 = on/off).')
    return 0


def legacy_cleanup(gta, dest):
    """Files of development builds (before the installer existed) are moved out of the way."""
    from csmod import gtadir
    old = ['models/cssource2.img', 'data/cssource/cssource2.ide', 'data/cssource/cssource.col',
           'models/txd/csscope.txd', 'cleo/cleo_text/cssource.fxt']
    for rel in old:
        p = gtadir.find_file(gta, rel)
        if os.path.isfile(p):
            os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
            shutil.move(p, os.path.join(dest, rel))
            log(f'  moved old file {rel} -> {BACKUP_DIR}')


def uninstall(gta):
    from csmod import gtadir
    if game_running():
        raise SystemExit('GTA San Andreas is running. Close it first.')
    mpath = os.path.join(gta, MANIFEST)
    files = json.load(open(mpath))['files'] if os.path.isfile(mpath) else []
    for rel in files:
        p = os.path.join(gta, rel)
        if os.path.isfile(p):
            os.remove(p)
    for rel in (SCRIPT_DIR, SOUND_DIR + r'\ev', SOUND_DIR, r'cleo\cssource', r'data\cssource'):
        p = os.path.join(gta, *rel.split('\\'))
        if os.path.isdir(p) and not os.listdir(p):
            os.rmdir(p)
    gtadir.patch_gta_dat(gta, False)
    if os.path.isfile(mpath):
        os.remove(mpath)
    log(f'Removed {len(files)} files and the gta.dat lines. Backups stay in {os.path.join(gta, BACKUP_DIR)}.')
    log('The Open Limit Adjuster settings were left as they are (original copy in the backup folder).')
    return 0


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='CS:Source Mode for GTA San Andreas - installer')
    ap.add_argument('--gta', help='GTA San Andreas folder')
    ap.add_argument('--css', help='Counter-Strike: Source folder')
    ap.add_argument('--uninstall', action='store_true')
    ap.add_argument('--build-only', metavar='OUTDIR', help='only build the files into OUTDIR')
    ap.add_argument('--yes', action='store_true', help='do not ask questions')
    a = ap.parse_args()
    log(f'CS:Source Mode for GTA San Andreas {MOD_VERSION} - installer\n')
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11 or newer is needed (python.org). You have ' + sys.version.split()[0])
    from csmod import deps, gtadir
    missing = deps.check_python_packages()
    if missing:
        raise SystemExit('Missing Python packages: ' + ', '.join(missing) + '\nRun:  python -m pip install -r installer/requirements.txt')

    gta = a.gta or find_game(GTA_STEAM_NAMES, gtadir.is_gta_dir)
    while not gtadir.is_gta_dir(gta):
        if a.yes:
            raise SystemExit('GTA San Andreas folder not found, use --gta')
        gta = ask('GTA San Andreas folder (the one with gta_sa.exe)')
    log(f'GTA San Andreas: {gta}')
    if a.uninstall:
        return uninstall(gta)
    css = a.css or find_game(CSS_STEAM_NAMES, is_css_dir)
    while not is_css_dir(css):
        if a.yes:
            raise SystemExit('Counter-Strike: Source folder not found, use --css')
        css = ask('Counter-Strike: Source folder (the one with the "cstrike" folder)')
    log(f'Counter-Strike: Source: {css}\n')
    if a.build_only:
        build(gta, css, os.path.abspath(a.build_only), os.path.join(HERE, '_work'))
        return 0
    return install(gta, css, True if a.yes else None)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
