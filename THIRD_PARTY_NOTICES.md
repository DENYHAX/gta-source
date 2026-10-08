# Third-party notices

This repository contains only original code. The following third-party software is used but **not included**:

| Component | License | How it is used |
|---|---|---|
| [SourceIO](https://github.com/REDxEYE/SourceIO) by REDxEYE and contributors | MIT | Downloaded by the installer at run time (pinned commit `191e9cc7f39e7259f417dc5f904ad1fe59bb2464`) into `installer/_deps/` to parse CS:S models. Not redistributed here. |
| [NumPy](https://numpy.org) | BSD-3-Clause | Installed with pip by `install.bat`. |
| [Pillow](https://python-pillow.org) | MIT-CMU (HPND) | Installed with pip by `install.bat`. |
| [CLEO 5](https://github.com/cleolibrary/CLEO5), [CLEO Redux](https://re.cleo.li), [Open Limit Adjuster](https://github.com/GTAmodding/III.VC.SA.LimitAdjuster) | their own licenses | Installed separately by the user; required at run time. |

Reference material (no code copied):
- [shavit's bhoptimer](https://github.com/shavitush/bhoptimer) and [RNGFix](https://github.com/jason-e/rngfix) (GPL-3.0): style settings and the slope / edge fix behaviour.
- [gta-reversed](https://github.com/gta-reversed/gta-reversed) and [plugin-sdk](https://github.com/DK22Pac/plugin-sdk): GTA SA memory layout and function addresses.

Game content: no files from Counter-Strike: Source or GTA San Andreas, and nothing derived from them, are part of
this repository. They are read from the user's own installation at install time.
