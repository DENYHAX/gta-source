# Technical notes

Notes for anyone who wants to change the mod. All addresses are for **GTA SA 1.0 US** (`gta_sa.exe`, 14,383,616
bytes). Most of them were found with the help of [gta-reversed](https://github.com/gta-reversed/gta-reversed) and
plugin-sdk.

## Layout

```
script/index.template.js   the mod (CLEO Redux JavaScript). The installer replaces the @@GENERATED_DATA@@ line
                           with VMDATA (viewmodel frame model IDs), SND_EV (animation sound events), PHX_ID, PHX_CUT_ID
installer/install.py       finds the games, builds, installs / uninstalls
installer/csmod/
  vpk.py         VPK reader (cstrike_pak_dir.vpk)
  srcmodel.py    MDL/VVD/VTX loading via SourceIO, CPU skinning, keyframe interpolation (lerp / slerp)
  vtf.py         VTF reader (DXT1/3/5, BGRA ...)
  viewmodels.py  weapon flip books, the silencer sequences, the spray can in CS:S hands
  phoenix.py     t_phoenix retargeted onto GTA's ped skeleton (male01.dff) and the cutscene skeleton (csplay.dff)
  hud.py         buy menu icons, AWP scope quadrants, GTA's mouse cursor -> cshud.txd
  sounds.py      CS:S wav files + AE_CL_PLAYSOUND (5004) events resolved through game_sounds_weapons.txt
  rw.py          RenderWare writers (DFF, TXD, COL1) and IMG VER2 reader / writer
  gtarw.py, gtaped.py   RenderWare readers (static DFF, TXD, ped DFF with skin)
  gtadir.py      free model IDs, gta.dat and limit adjuster patching
  deps.py        SourceIO download (pinned commit)
```

## Movement

Order inside `CGame::Process`: `UpdatePads` → `CTheScripts::Process` (our script runs here) → `CWorld::Process`
(`ProcessControl`, `ProcessCollision`) → `TheCamera.Process`.

Each frame the script:
1. Reads the ped's `m_vecMoveSpeed` (+0x44, units per 1/50 s) and ped flags (+0x46C: bit0 `bIsStanding`, bit1 `bWasStanding`).
2. Probes the surroundings with `CWorld::ProcessLineOfSight` (0x56BA00). The player is treated as a capsule (r 0.35 m, half height 0.65 m). The probes give:
   - ground: nz >= 0.7, and vz <= 140 (`NON_JUMP_VELOCITY`);
   - surf ramps: 0.05 < nz < 0.7;
   - walls: |nz| < 0.7;
   - ceilings.
3. Runs Friction / Accelerate / AirAccelerate (air speed cap 30) and the jump (sqrt(2·800·57) = 301.99 u/s) at a fixed tick rate. The view yaw is interpolated across the ticks of the frame. Surf, wall and ceiling contacts are clipped every tick (Source `ClipVelocity`, overbounce 1).
4. Writes the velocity back. Before that it clears `bIsStanding` so GTA's animation doesn't overwrite the speed, and pre-compensates GTA's gravity (+0.008 · timestep) so the vertical speed is exactly ours. While standing still with no input, `bIsStanding` is kept, because scripts check `CTheScripts::IsPedStopped` (shop markers etc.).

On top of that:
- **Obstacles the rays miss.** If GTA's collision stopped the ped on something the rays don't see (poles, props, cars), the lost velocity or position gives that obstacle's normal, which is then clipped. A plain parallel scale-down (GTA's air drag) is not treated as an obstacle.
- **RNGFix.** On a landing, the velocity is clipped against the ground normal before vz is zeroed: downhill gives the boost, uphill keeps the horizontal speed. A deflected vz above 140 is a slide, not a landing. The edge bug (falling, GTA stopped the fall, jump held) becomes a jump.
- **rampCatchup.** `CPhysical::ProcessCollision` resets the matrix to the start of the frame when `CheckCollision` hits something. While sliding along a ramp, that swallows whole frames of movement. The script remembers the expected displacement and gives back the missing part, only along that vector and only if two rays find the target position free.

- **Water** (`CheckWater` / `WaterMove` / `CheckWaterJump` / `WaterJump`):
  - The water surface comes from `CWaterLevel::GetWaterLevel` (0x6EB690).
  - Water levels: 1 = feet wet, normal movement; 2 = waist deep (36 u, or 27 u ducked), swimming; 3 = eyes under water.
  - While swimming: no gravity, water friction, the wish direction follows the view pitch, Space gives vz = 100, and with no input you drift down at -60.
  - Water jump: if there is solid ground at the waist and free space at eye + 8 u, with a standable surface behind it, you get vz = 256 and a 50 u/s push for up to 2 s.
  - GTA's buoyancy and swim task are disabled for the player while CS mode runs: the call to `cBuoyancy::ProcessBuoyancy` at 0x5E2009 goes to a stub that answers "not in water" (`xor eax,eax; ret 0x10`).
  - Drowning: `CPlayerPed::HandlePlayerBreath` (0x60A8D0) is called while the eyes are under water. The entry splash uses `Fx_c::TriggerWaterSplash` (0x4A1070, g_fx 0xA9AE00).

## Rendering hooks (the script writes them into a VirtualAlloc'd RWX page)

| Call site in `Idle` | Original target | Stub does |
|---|---|---|
| 0x53EAD3 `call RenderEffects` | 0x53E170 | then draws the viewmodel: CreateRwObject if needed, `UpdateRwMatrix` 0x446F90 / `UpdateRwFrame` 0x532B00, `RwCameraEndUpdate` 0x7EE180 → `SetNearClipPlane(0.02)` 0x7EE1D0 → `BeginUpdate` 0x7EE190, clear Z 0x7EE340, `DefinedState` 0x734650, vtbl SetupLighting +0x4C / `CEntity::Render` 0x534310 / RemoveLighting +0x50, restore near plane |
| 0x53EABF `RenderScene` / 0x53EAC4 `RenderWeaponPedsForPC` | 0x53DF40 / 0x732F30 | hide the first-person body (`bDontRender`, ped +0x474 bit1) only during the main scene, so mirrors, shadows and animation still see it |
| 0x53EA0D shadows / 0x53EA12 mirrors | 0x706AB0 / 0x727140 | (kept for compatibility, inactive) |

The viewmodel object itself has `CObject` `bDoNotRender` set (+0x143 bit1), so the world renderer prepares it
(including its RwObject) but only our pass draws it.

Other patches, each checked against the original bytes first:
- Low clouds: `jmp +0x207` at 0x71401E.
- Sun glare: the fmul operands at 0x6FC65E and 0x6FC6EA are pointed at our own floats.
- `CClothes::RebuildCutscenePlayer` (0x5A8270) jumps to a stub. The stub clones the `csphxcut` clump into model 1 (`csplay`), using `RpClumpClone` 0x749F70, `AddTexDictionaryRef` 0x4C4B80, vtbl+0x20 `DeleteRwObject`, vtbl+0x40 `SetClump` and `RemoveTexDictionaryRef` 0x4C4B90. A file with the same name in another IMG cannot replace gta3.img's csplay, because the first IMG wins.
- Vehicles: `CMenuManager::m_bPrefsFrameLimiter` (0xBA6794) and `RsGlobal.frameLimit` (0xC1704C).

## Weapons

- Bullets go through `ProcessLineOfSight`, then `CWeapon::CheckForShootingVehicleOccupant` (0x73F480), then `CWeapon::DoBulletImpact` (0x73B550). The CS:S damage × hitgroup multiplier is written into `aWeaponInfo` (0xC8AAB8 + 0x70·type, damage +0x22) only for that call.
- The matching GTA weapon sits in CJ's hand for the HUD icon and the ammo counter (`CWeapon` slots at ped +0x5A0, 0x1C each; active slot +0x718).
- GTA reads the mouse buttons directly (0xB73418) for aiming. They are zeroed every frame, otherwise RMB with the sniper rifle enters GTA's sniper camera.
- The spray can uses `CWeapon::Fire` (0x742300) every frame for GTA's own spray effect and tagging.

## Asset pipeline (installer)

- **Viewmodels.** Each animation is sampled at 30-60 fps (`frames = round(duration · fps) + 1`, at most 200). Poses are interpolated between keyframes, the mesh is skinned, and the result is converted to GTA ped space (x right, y forward, z up, metres) with the forward axis scaled by tan 27° / tan 45° (viewmodel_fov 54 vs fov 90). Everything except the knife is mirrored, like `cl_righthand 1`. Each frame becomes one static DFF; all frames of a weapon share one TXD.
- **Collision.** Each model gets a COL1 entry with one tiny sphere, stored as `cssource.col` *inside* the IMG. A `COLFILE` line in gta.dat crashes the loader.
- **Model IDs.** Every ID from 19999 down to 3000 that no IDE in `default.dat` / `gta.dat` uses (about 2970 are needed).
- **Phoenix.** Source model space is mapped onto the template's skin space using its joints. Each major bone gets a rotation that aligns its limb direction plus a translation onto the GTA joint; helper bones follow their mapped ancestor; weights are merged onto the GTA bones (at most 4). The template's frame list, HAnim hierarchy and inverse bind matrices are copied unchanged.

## Lessons learned

- `setCoordinatesNoOffset` zeroes the velocity, so the velocity must be written after it.
- A hidden entity (`m_bIsVisible` cleared) never gets an RwObject, because it is created lazily by `CRenderer::SetupEntityVisibility`.
- `LOAD_SPRITE` reads only 7 characters of the texture name.
- `FxtStore.insert` does not reach the game's text lookup in CLEO Redux delegate mode; `Text.AddLabel` (CLEO 5) does.
- After a teleport or an interior change, objects keep a stale world sector and have to be recreated.
- The CLEO Redux hot reload sometimes panics. Restart the game after editing the script.
