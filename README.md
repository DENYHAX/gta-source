# CS:Source Mode for GTA San Andreas

Play single-player **GTA San Andreas** in first person with **Counter-Strike: Source** movement and weapons:
bunny hopping, air strafing and surfing like on a CS:S bhop server, CS:S viewmodels with their real animations
and sounds, recoil, a buy menu, and the CS:S Phoenix as your player model. The GTA HUD, missions, cars and the
rest of the game stay as they are.

## Video

[![CS:Source Mode for GTA San Andreas - gameplay video](https://img.youtube.com/vi/4XeHAlk6YMM/hqdefault.jpg)](https://www.youtube.com/watch?v=4XeHAlk6YMM)

*Recorded with an early version. The swimming, the Phoenix player model, the silencers, the spray can and several
other features listed below came later.*

> **No game files are included in this repository.** The installer builds every model, texture and sound the mod
> needs on *your* computer, from *your own* copies of Counter-Strike: Source and GTA San Andreas.
> You need to own both games.

---

## Features

**Movement (Source engine `CGameMovement`)**
- Ground friction / acceleration, air acceleration and air strafing, crouching, a 57-unit jump, CS:S gravity.
- Two presets:
  - `bhop` (the default): based on the shavit-timer "Normal" style, with autobhop, `sv_airaccelerate 1000`, a 260 u/s prestrafe and a 100 tick rate.
  - `css`: vanilla CS:S (`sv_airaccelerate 10`, jump re-press needed, 66 tick).
- Surfing on steep ramps, sliding along walls the way Source's `TryPlayerMove` does, and the launch at the top of a ramp.
- RNGFix-style fixes: the slope boost on downhill landings, no speed loss on uphill landings, and the edge bug.
- Water works like in CS:S:
  - waist-deep water means swimming, with water friction and no gravity;
  - you swim where you look, Space swims up, and you sink slowly when you let go;
  - facing a ledge while waist-deep pops you out of the water (water jump);
  - shallow water keeps normal movement, so you can bhop through it;
  - you get a splash, swim strokes and wading sounds;
  - drowning still uses GTA's breath bar.
- Mouse wheel jump/duck binds. MOUSE3 gives an optional speed boost (handy for long GTA distances).
- Mission NPCs and gang members don't block you while you're bhopping.

**Weapons**
- CS:S viewmodels for the knife, Glock-18, USP .45, Desert Eagle, M3, MP5, AK-47, M4A1 and AWP.
  - The draw, shoot, reload and silencer animations are taken from the CS:S models themselves.
  - Animation sound events (clip in, bolt pull and so on) play in sync, as in CS:S.
- CS:S damage per hitgroup, recoil and view punch, magazines, reloads, the AWP scope, and USP / M4A1 silencers on the right mouse button.
- Optional no-spread mode: recoil stays, random inaccuracy goes. This is the default.
- Shooting uses GTA's own bullet path, so you can hit car drivers through windows, blow up fuel tanks and so on.
- A CS:S style buy menu (B), with Kevlar mapped to GTA armour.
- GTA mission items go in the CS:S grenade slot (key 4):
  - the spray can, held in CS:S hands and able to paint gang tags;
  - the fire extinguisher;
  - the camera, which hands control back to GTA while you use it.

**Visuals**
- The viewmodel is drawn on top of the world like in CS:S, so it never pokes into walls.
- The CS:S Phoenix replaces CJ:
  - on foot, in cars, in mirrors and shadows, and in cutscenes;
  - the body plays walk and run animations that match your speed.
- Optional fixes for GTA at a high FOV: hidden low clouds, a smaller sun glare and less z-fighting.
- A 60 FPS cap while driving, because GTA's car physics break at high frame rates (and bhop wants the frame limiter off).

---

## Requirements

| What | Notes |
|---|---|
| **GTA San Andreas, version 1.0 US** | The Steam / Rockstar Launcher versions must be **downgraded to 1.0 US** first (use a GTA SA downgrader tool). The installer checks that `gta_sa.exe` is 14,383,616 bytes. |
| **Counter-Strike: Source** | Steam version, installed (the installer reads `cstrike/cstrike_pak_dir.vpk`). |
| **CLEO 5** (5.0 or newer, tested 5.4.0) | <https://github.com/cleolibrary/CLEO5>. It also installs the Ultimate ASI Loader. |
| **CLEO Redux** (tested 1.5.1) | <https://re.cleo.li>. Only `cleo_redux.asi` is needed next to CLEO 5. Don't copy CLEO Redux's own `CLEO_PLUGINS` over CLEO 5's plugins. |
| **Open Limit Adjuster** | <https://github.com/GTAmodding/III.VC.SA.LimitAdjuster>. The mod adds about 3000 models, more than the vanilla limit. The installer sets the needed values in its ini. |
| **Python 3.11 or newer** (64-bit) | <https://www.python.org/downloads/>. Tick **"Add python.exe to PATH"**. Only needed to run the installer. |

Recommended, not required:
- [SilentPatch](https://github.com/CookiePLMonster/SilentPatch) for general fixes.
- [skygrad](https://github.com/GTAmodding/skygrad) for a correct sky at a high FOV.
- [III.VC.SA.WindowedMode](https://github.com/ThirteenAG/III.VC.SA.WindowedMode) for windowed mode.
- Turning the in-game frame limiter **off**, because bhop is much better at a high FPS.

---

## Installation

1. Install GTA SA 1.0 US, CLEO 5, CLEO Redux and the Open Limit Adjuster (see above). Start the game once to check that it runs.
2. Download this repository (green **Code** button → *Download ZIP*) and unpack it anywhere.
3. **Close GTA San Andreas**, then double-click **`install.bat`**. It will:
   - install the two Python packages it needs (`numpy`, `Pillow`);
   - download [SourceIO](https://github.com/REDxEYE/SourceIO), an MIT-licensed Source model reader, at a pinned commit;
   - find both games through Steam (if it can't, it asks for the folders);
   - build the models, textures, sounds and the script from your game files (a few minutes);
   - install them into the GTA folder and patch `data\gta.dat` and the limit adjuster ini.

   Your original `gta.dat` and limit adjuster ini are backed up in `cssource_backup\`.
4. Start the game. CS mode switches on by itself whenever you are on foot.

Command line options (`install.bat` passes them on):

```
install.bat --gta "D:\Games\GTA San Andreas" --css "D:\Steam\steamapps\common\Counter-Strike Source"
install.bat --build-only C:\temp\cssource-out      (build only, the GTA folder is not touched)
```

Running the installer again (for example after updating the mod) rebuilds everything. Your edited `index.js` is
kept as `index.js.bak`, so copy your settings back over.

### What gets installed

| File | Content |
|---|---|
| `models\cssource.img` | viewmodel animation frames, spray can, Phoenix player + cutscene model, collision |
| `data\cssource\cssource.ide` | model definitions (IDs are picked from the free IDs of *your* game) |
| `models\txd\cshud.txd` | buy menu icons, AWP scope, cursor |
| `cleo\cssource\sound\` | CS:S sounds |
| `cleo\cssource[mem][dll]\index.js` | the mod itself (a CLEO Redux JavaScript script) |
| `data\gta.dat` | two lines added: `IMG MODELS\CSSOURCE.IMG`, `IDE DATA\CSSOURCE\CSSOURCE.IDE` |

## Uninstall

Close the game and run **`uninstall.bat`**. It removes the installed files and the two `gta.dat` lines.
The limit adjuster settings are left alone; the original ini is in `cssource_backup\`.

---

## Controls

| Key | Action |
|---|---|
| W A S D | move (hold strafe keys + turn the mouse in the air to air strafe) |
| Space / mouse wheel down | jump (hold for autobhop in the `bhop` preset) |
| Ctrl / mouse wheel up | crouch |
| Shift | walk |
| Left mouse | fire |
| Right mouse | AWP zoom / USP and M4A1 silencer on-off / knife stab |
| R | reload |
| 1 / 2 / 3 | primary / pistol / knife |
| 4 | GTA mission items (spray can, fire extinguisher, camera) |
| Q | last weapon |
| B | buy menu (1-9 or click, B to close) |
| , / . | buy primary / secondary ammo |
| Mouse 3 (wheel click) | speed boost |
| F2 | CS mode on / off (plain GTA controls) |
| F5 / F6 | FOV - / + |

CS mode turns itself off in vehicles and whenever a mission script takes control (cutscenes, shops), and comes back afterwards.

## Settings

Open `cleo\cssource[mem][dll]\index.js` in a text editor. The `CFG` block at the top has every setting with a
comment. CLEO Redux reloads the script when you save it, but restarting the game is safer. The most useful ones:

| Setting | Default | Meaning |
|---|---|---|
| `sensitivity`, `m_yaw`, `m_pitch` | 2.2, 0.033, 0.022 | same as your CS:S `config.cfg` |
| `fov` | 110 | CS:S `fov_desired` (4:3 horizontal) |
| `preset` | `"bhop"` | `"bhop"` (shavit Normal) or `"css"` (vanilla CS:S) |
| `noSpread` | `true` | no random spread, recoil stays |
| `playerModel` | `true` | play as Phoenix |
| `boostAccel`, `boostMax` | 2500, 4000 | MOUSE3 boost |
| `ghostPeds` | `"mission"` | `"mission"`, `"all"` or `false` |
| `rampCatchup` | `true` | fixes the delayed launch on ramps / surf caused by GTA's collision step |
| `carFpsLimit` | 60 | FPS cap in vehicles, 0 = off |
| `debug` | `false` | write state lines to `cleo_redux.log` |

---

## Troubleshooting

- **Nothing happens in game.** Check `cleo_redux.log` in the GTA folder for `[cssource]` lines:
  - If the script isn't listed at all, CLEO Redux is not installed correctly.
  - If it says permission denied, set `PermissionLevel=Lax` in `CLEO\.config\cleo.ini` (CLEO Redux's config). The `[mem][dll]` in the folder name asks for memory and DLL access.
- **The game crashes while loading.** The Open Limit Adjuster is missing or its `AtomicModels` value is too low (it needs about 14000 + 3000).
- **Viewmodel missing / sounds missing.** Run the installer again and check its output for warnings. Make sure your CS:S installation is complete (Steam → Properties → Installed Files → Verify).
- **The installer can't download SourceIO.** Download <https://github.com/REDxEYE/SourceIO/archive/191e9cc7f39e7259f417dc5f904ad1fe59bb2464.zip> yourself, unpack it to `installer\_deps\`, rename the folder to `SourceIO`, and create a file `installer\_deps\SourceIO\.commit` containing `191e9cc7f39e7259f417dc5f904ad1fe59bb2464`.
- **Other mods.** The script patches a few places in `gta_sa.exe` memory (render calls, the cutscene player builder, the sun and the clouds). It checks the original bytes first and skips a patch if another mod changed them, and it says so in the log.
- Only GTA SA **1.0 US** is supported: every memory address in the script belongs to that executable.

---

## How it works (short)

The mod is a single CLEO Redux script. Every frame it reads the player's state, runs the CS:S movement code at a
fixed tick rate, and writes the velocity back into GTA's physics. Collision normals for walls, slopes and surf
ramps come from GTA's own line-of-sight tests. A CS:S viewmodel is a flip book: the installer samples each
animation at 30-60 frames per second, skins the mesh on the CPU and saves every frame as a small static GTA model.
The script shows the right frame and draws it in a separate render pass on top of the world. See
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for the details: engine addresses, the render hooks and the asset pipeline.

## Legal

- This is a fan-made, non-commercial modification. It is **not affiliated with or endorsed by Valve Corporation or
  Rockstar Games / Take-Two Interactive**. Counter-Strike, Source and the Phoenix character are trademarks or
  property of Valve; Grand Theft Auto and San Andreas are trademarks of Take-Two Interactive.
- **No copyrighted game content is distributed**: no models, textures, sounds or text from either game, and no
  converted versions of them. The installer reads the files from your own legally obtained games and writes the
  result only into your own GTA folder.
- **Don't redistribute the generated files** (`cssource.img`, `cshud.txd`, the sounds or the generated `index.js`).
  Share this repository instead, and everyone builds their own.
- The mod is for single-player GTA San Andreas only.

## Credits

- **SourceIO** by REDxEYE and contributors (MIT): the Source model parser the installer downloads.
- **shavit's bhoptimer** and **RNGFix** (GPL-3.0): the reference for the bhop style settings and the slope / edge fixes.
- **gta-reversed** and **plugin-sdk**: the reverse engineering that made the GTA memory work possible.
- **CLEO 5 / CLEO Redux** by the CLEO team, **Open Limit Adjuster**, **SilentPatch**, **skygrad**.

## License

The code in this repository (the script and the installer) is licensed under the **GNU General Public License v3.0**,
see [LICENSE](LICENSE). The license covers only this code, not any game content or anything built from it.
