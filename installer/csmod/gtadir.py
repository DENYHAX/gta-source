"""GTA San Andreas folder helpers: version check, free model IDs, gta.dat / limit adjuster patching."""
import os
import re

GTA_10US_SIZE = 14383616          # gta_sa.exe 1.0 US (the only version the script's memory addresses fit)
MARK = 'CSSOURCE'                 # every gta.dat line we add contains this
IMG_LINE = r'IMG MODELS\CSSOURCE.IMG'
IDE_LINE = r'IDE DATA\CSSOURCE\CSSOURCE.IDE'


def find_file(root, rel):
    """Case-insensitive lookup of a relative path (Windows is case-insensitive, other systems are not)."""
    cur = root
    for part in re.split(r'[\\/]', rel):
        if not part:
            continue
        hit = os.path.join(cur, part)
        if not os.path.exists(hit) and os.path.isdir(cur):
            low = part.lower()
            hit = next((os.path.join(cur, n) for n in os.listdir(cur) if n.lower() == low), hit)
        cur = hit
    return cur


def exe_info(gta):
    for name in ('gta_sa.exe', 'gta-sa.exe'):
        p = find_file(gta, name)
        if os.path.isfile(p):
            return p, os.path.getsize(p)
    return None, 0


def is_gta_dir(p):
    return bool(p) and os.path.isfile(find_file(p, 'data/gta.dat')) and os.path.isfile(find_file(p, 'models/gta3.img'))


def _dat_lines(path):
    with open(path, 'r', encoding='latin1') as f:
        return f.read().splitlines()


def ide_files(gta):
    """All IDE files the game loads (default.dat + gta.dat), except our own."""
    out = []
    for dat in ('data/default.dat', 'data/gta.dat'):
        p = find_file(gta, dat)
        if not os.path.isfile(p):
            continue
        for line in _dat_lines(p):
            s = line.strip()
            if not s or s.startswith('#') or s.startswith(';'):
                continue
            parts = s.split(None, 1)
            if parts[0].upper() == 'IDE' and len(parts) > 1 and MARK not in parts[1].upper():
                out.append(find_file(gta, parts[1].strip()))
    return out


def used_ids(gta):
    used = set()
    for p in ide_files(gta):
        if not os.path.isfile(p):
            continue
        for line in _dat_lines(p):
            m = re.match(r'\s*(\d+)\s*,', line)
            if m:
                used.add(int(m.group(1)))
    return used


class FreeIds:
    """Model IDs no IDE uses, highest first (GTA SA 1.0 has 20000 model slots; IDs below 3000 are left alone)."""

    def __init__(self, gta, low=3000, high=19999):
        used = used_ids(gta)
        self.free = [i for i in range(high, low - 1, -1) if i not in used]
        self.pos = 0

    def take(self):
        if self.pos >= len(self.free):
            raise RuntimeError('ran out of free model IDs')
        v = self.free[self.pos]
        self.pos += 1
        return v

    @property
    def count(self):
        return self.pos


def patch_gta_dat(gta, install=True):
    """Remove every line we ever added (contains CSSOURCE); on install add our IMG and IDE lines."""
    p = find_file(gta, 'data/gta.dat')
    with open(p, 'r', encoding='latin1') as f:
        text = f.read()
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = [l for l in text.splitlines() if MARK not in l.upper()]
    if install:
        last_img = max((i for i, l in enumerate(lines) if l.strip().upper().startswith('IMG ')), default=-1)
        lines.insert(last_img + 1, IMG_LINE)
        last_ide = max((i for i, l in enumerate(lines) if l.strip().upper().startswith('IDE ')), default=len(lines) - 1)
        lines.insert(last_ide + 1, IDE_LINE)
    with open(p, 'w', encoding='latin1', newline='') as f:
        f.write(nl.join(lines) + nl)


def patch_limit_adjuster(gta, atomic_models, memory_mb=512):
    """Open Limit Adjuster ini: [SALIMITS] AtomicModels / MemoryAvailable, [OPTIONS] DebugTextKey off (F5 is ours)."""
    p = find_file(gta, 'III.VC.SA.LimitAdjuster.ini')
    if not os.path.isfile(p):
        return False
    with open(p, 'r', encoding='latin1') as f:
        lines = f.read().splitlines()
    want = {'SALIMITS': {'AtomicModels': atomic_models, 'MemoryAvailable': memory_mb}, 'OPTIONS': {'DebugTextKey': '0x00'}}
    sec, done, out = None, set(), []
    for line in lines:
        m = re.match(r'\s*\[(\w+)\]', line)
        if m:
            # add keys that were missing from the section we are leaving
            for k, v in want.get(sec, {}).items():
                if (sec, k) not in done:
                    out.append(f'{k} = {v}'); done.add((sec, k))
            sec = m.group(1).upper()
            out.append(line)
            continue
        m = re.match(r'\s*;?\s*(\w+)\s*=\s*([^;\s]*)(.*)$', line)
        if m and sec in want and m.group(1) in want[sec] and (sec, m.group(1)) not in done:
            k = m.group(1); v = want[sec][k]
            if k == 'AtomicModels' and not line.lstrip().startswith(';'):
                try:
                    v = max(int(m.group(2)), atomic_models)
                except ValueError:
                    v = m.group(2)      # "unlimited"
            if k == 'MemoryAvailable' and not line.lstrip().startswith(';'):
                try:
                    v = max(int(m.group(2)), memory_mb)
                except ValueError:
                    v = m.group(2)
            out.append(f'{k} = {v}'); done.add((sec, k))
            continue
        out.append(line)
    for k, v in want.get(sec, {}).items():
        if (sec, k) not in done:
            out.append(f'{k} = {v}'); done.add((sec, k))
    for s, kv in want.items():
        if not any(d[0] == s for d in done):
            out.append(f'[{s}]')
            out += [f'{k} = {v}' for k, v in kv.items()]
    with open(p, 'w', encoding='latin1', newline='') as f:
        f.write('\r\n'.join(out) + '\r\n')
    return True
