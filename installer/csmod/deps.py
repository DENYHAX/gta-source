"""Third-party Python code the installer needs at run time (downloaded, never shipped in this repository)."""
import io
import os
import shutil
import sys
import urllib.request
import zipfile

# SourceIO by REDxEYE (MIT license): Source engine MDL / VVD / VTX parser. Pinned to a known-good commit.
SOURCEIO_COMMIT = '191e9cc7f39e7259f417dc5f904ad1fe59bb2464'
SOURCEIO_URL = f'https://github.com/REDxEYE/SourceIO/archive/{SOURCEIO_COMMIT}.zip'


def check_python_packages():
    missing = []
    for mod, pkg in (('numpy', 'numpy'), ('PIL', 'Pillow')):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def ensure_sourceio(deps_dir, log=print):
    """Download + unpack SourceIO into deps_dir/SourceIO (once) and put deps_dir on sys.path."""
    target = os.path.join(deps_dir, 'SourceIO')
    stamp = os.path.join(target, '.commit')
    if not (os.path.isfile(stamp) and open(stamp).read().strip() == SOURCEIO_COMMIT):
        log(f'Downloading SourceIO ({SOURCEIO_COMMIT[:10]}) from GitHub ...')
        req = urllib.request.Request(SOURCEIO_URL, headers={'User-Agent': 'cssource-mode-installer'})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(deps_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = z.namelist()[0].split('/')[0]
            z.extractall(deps_dir)
        os.rename(os.path.join(deps_dir, root), target)
        with open(stamp, 'w') as f:
            f.write(SOURCEIO_COMMIT)
    if deps_dir not in sys.path:
        sys.path.insert(0, deps_dir)
    import SourceIO  # noqa: F401  (fails early with a clear error if Python is too old)
