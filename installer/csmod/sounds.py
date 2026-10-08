"""CS:S sounds for the mod (copied unchanged from the user's own CS:S VPK) and the animation sound events.

- cleo/cssource/sound/<name>.wav: fire sounds, footsteps, zoom ... (TOP)
- cleo/cssource/sound/ev/<wave>.wav: sounds played by AE_CL_PLAYSOUND (5004) animation events of the weapon
  sequences, resolved through scripts/game_sounds_weapons.txt, plus a few extra ones (EXTRA_EV)
"""
import os
import re

from .srcmodel import load

TOP = {
    'ak47': 'sound/weapons/ak47/ak47-1.wav', 'm4a1': 'sound/weapons/m4a1/m4a1_unsil-1.wav',
    'm4a1_sil': 'sound/weapons/m4a1/m4a1-1.wav', 'mp5': 'sound/weapons/mp5navy/mp5-1.wav',
    'deagle': 'sound/weapons/deagle/deagle-1.wav', 'usp': 'sound/weapons/usp/usp_unsil-1.wav',
    'usp_sil': 'sound/weapons/usp/usp1.wav', 'glock': 'sound/weapons/glock/glock18-1.wav',
    'm3': 'sound/weapons/m3/m3-1.wav', 'awp': 'sound/weapons/awp/awp1.wav',
    'knife_slash': 'sound/weapons/knife/knife_slash1.wav', 'knife_stab': 'sound/weapons/knife/knife_stab.wav',
    'zoom': 'sound/weapons/zoom.wav', 'dryfire': 'sound/weapons/clipempty_rifle.wav',
    'ammopickup': 'sound/items/ammopickup.wav',
    'step1': 'sound/player/footsteps/concrete1.wav', 'step2': 'sound/player/footsteps/concrete2.wav',
    'step3': 'sound/player/footsteps/concrete3.wav', 'step4': 'sound/player/footsteps/concrete4.wav',
    'usp_silencer_on': 'sound/weapons/usp/usp_silencer_on.wav', 'usp_silencer_off': 'sound/weapons/usp/usp_silencer_off.wav',
    'm4a1_silencer_on': 'sound/weapons/m4a1/m4a1_silencer_on.wav', 'm4a1_silencer_off': 'sound/weapons/m4a1/m4a1_silencer_off.wav',
    # water: swimming strokes, shallow water footsteps, splash on entry
    **{f'wade{i}': f'sound/player/footsteps/wade{i}.wav' for i in range(1, 5)},
    **{f'slosh{i}': f'sound/player/footsteps/slosh{i}.wav' for i in range(1, 5)},
    **{f'splash{i}': f'sound/ambient/water_splash{i}.wav' for i in range(1, 4)},
}
EXTRA_EV = ['sound/player/sprayer.wav', 'sound/weapons/clipempty_pistol.wav', 'sound/weapons/clipempty_rifle.wav'] + \
    [f'sound/weapons/knife/{n}.wav' for n in ('knife_deploy1', 'knife_slash1', 'knife_slash2', 'knife_hit1', 'knife_hit2',
                                               'knife_hit3', 'knife_hit4', 'knife_hitwall1', 'knife_stab')]
GAME_SOUNDS = 'scripts/game_sounds_weapons.txt'
AE_CL_PLAYSOUND = 5004


def parse_game_sounds(text):
    """Minimal KeyValues reader: {sound script name (lower): first wave path}."""
    toks = re.findall(r'"([^"]*)"|([{}])|([^\s"{}]+)', re.sub(r'//[^\n]*', '', text))
    toks = [a or b or c for a, b, c in toks]
    out, i = {}, 0
    while i < len(toks):
        if i + 1 < len(toks) and toks[i + 1] == '{':
            name = toks[i].lower(); i += 2; depth = 1; wave = None
            while i < len(toks) and depth:
                t = toks[i]
                if t == '{':
                    depth += 1
                elif t == '}':
                    depth -= 1
                elif t.lower() == 'wave' and i + 1 < len(toks) and wave is None:
                    wave = toks[i + 1]; i += 1
                i += 1
            if wave:
                out[name] = re.sub(r'^[^A-Za-z0-9]+', '', wave).replace('\\', '/')
        else:
            i += 1
    return out


def anim_events(css_dir, weap, game_sounds):
    """{weapon: {anim: [[cycle, wave base name], ...]}} and the set of wave paths they need."""
    snd_ev, waves = {}, set()
    for wid, (mdlname, short, anims) in weap.items():
        mdl, _ = load(os.path.join(css_dir, 'models', 'weapons', mdlname))
        for an, (seq_name, fps, cap) in anims.items():
            idx = next((k for k, ad in enumerate(mdl.anim_descs) if seq_name in ad.name), None)
            if idx is None:
                continue
            seq = next((s for s in mdl.sequences if list(s.anim_desc_indices)[:1] == [idx]), None)
            if seq is None:
                continue
            evs = []
            for e in seq.events:
                if getattr(e, 'event', None) != AE_CL_PLAYSOUND:
                    continue
                wave = game_sounds.get(str(e.options).strip().lower())
                if not wave:
                    continue
                path = 'sound/' + wave
                waves.add(path)
                evs.append([round(float(e.cycle), 3), os.path.splitext(os.path.basename(wave))[0].lower()])
            if evs:
                snd_ev.setdefault(wid, {})[an] = evs
    return snd_ev, waves


def install(read_css, css_dir, weap, sound_dir, log=print):
    """Write all wav files into sound_dir (cleo/cssource/sound). Returns SND_EV for the script."""
    os.makedirs(os.path.join(sound_dir, 'ev'), exist_ok=True)
    for name, path in TOP.items():
        try:
            data = read_css(path)
        except (FileNotFoundError, KeyError):
            log(f'  warning: {path} not found in CS:S')
            continue
        with open(os.path.join(sound_dir, name + '.wav'), 'wb') as f:
            f.write(data)
    game_sounds = parse_game_sounds(read_css(GAME_SOUNDS).decode('latin1'))
    snd_ev, waves = anim_events(css_dir, weap, game_sounds)
    n = 0
    for path in sorted(waves | set(EXTRA_EV)):
        base = os.path.splitext(os.path.basename(path))[0].lower()
        try:
            data = read_css(path)
        except (FileNotFoundError, KeyError):
            log(f'  warning: {path} not found in CS:S')
            continue
        with open(os.path.join(sound_dir, 'ev', base + '.wav'), 'wb') as f:
            f.write(data)
        n += 1
    log(f'  {len(TOP)} sounds + {n} animation event sounds')
    return snd_ev
