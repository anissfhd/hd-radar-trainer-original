"""Deuxieme etape du portage (a appliquer apres apply_port.py).

- Offsets de soldat ecrits en dur dans le code pose (noclip, suivi des balles).
- C_human::Tick : point d'entree (noclip, ranimer) et point apres le test
  `model == nullptr` (vie illimitee, protection de chute).
- cbProc : l'original prend TROIS arguments (ret 0Ch) au lieu de quatre
  (ret 10h) ; le mot `reserved` toujours nul n'est plus empile.
- CB_USE_AUTO : 43 dans le mod, 42 dans l'original (enum decale de -1 a
  partir de ~28).

Chaque remplacement est exact et compte ses occurrences ; rien n'est ecrit si
une seule ne correspond pas.

Usage : python -I apply_port_etape2.py <dossier src>
"""
import sys
from pathlib import Path

F = 'gameplay_mods.cpp'
STEPS = [
    # --- Noclip : champs C_human (-0x14), dans l'ordre pour eviter les collisions.
    (F, 'dword(0x1AC); dword(0); // move_dir.x', 'dword(0x198); dword(0); // move_dir.x', 1),
    (F, 'dword(0x1B0); dword(0); // move_dir.y', 'dword(0x19C); dword(0); // move_dir.y', 1),
    (F, 'dword(0x1B4); dword(0); // move_dir.z', 'dword(0x1A0); dword(0); // move_dir.z', 1),
    (F, 'dword(0x1B8); dword(0); // fall_speed', 'dword(0x1A4); dword(0); // fall_speed', 1),
    (F, 'dword(0x264); byte(0);  // falling', 'dword(0x250); byte(0);  // falling', 1),
    (F, 'dword(0x274); dword(kNoclipCollisionHoldMs);', 'dword(0x260); dword(kNoclipCollisionHoldMs);', 1),
    # --- Suivi des balles : shoot_countdown, stay_mode, frm_head.
    (F, 'byte(0xC7); byte(0x80); dword(0x260); dword(0);', 'byte(0xC7); byte(0x80); dword(0x24C); dword(0);', 1),
    (F, 'dword(0x254)', 'dword(0x240)', 3),
    (F, 'dword(0x1C8)', 'dword(0x1B4)', 4),
    # --- C_human::Tick.
    (F, "constexpr std::uintptr_t kHumanTickRva = 0x0001'A560;",
        "constexpr std::uintptr_t kHumanTickRva = 0x0001'6FD0;", 1),
    (F, "constexpr std::uintptr_t kLifeUnlimitedTickHookRva = 0x0001'A583;",
        "constexpr std::uintptr_t kLifeUnlimitedTickHookRva = 0x0001'6FF3;", 1),
    # push ebp / mov ebp,esp / sub esp,348h (au lieu de 36Ch).
    (F, '0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x6C, 0x03, 0x00, 0x00',
        '0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x48, 0x03, 0x00, 0x00', 2),
    # Cible du saut apres `model == nullptr` : mov ecx,[ebx+1A8h] (6 octets).
    (F, '0x8B, 0x83, 0xCC, 0x00, 0x00, 0x00', '0x8B, 0x8B, 0xA8, 0x01, 0x00, 0x00', 2),
    # --- cbProc a trois arguments.
    (F, '    byte(0x6A); byte(0x00);                       // push prm3 = 0\n', '', 1),
    (F, '        byte(0x6A); byte(0x00);            // reserved = 0\n', '', 1),
    (F, '    byte(0x6A); byte(0x00);                  // reserved\n', '', 2),
    (F, '    byte(0x6A); byte(0x00);               // push reserved = 0\n', '', 2),
    (F, 'constexpr std::uint32_t kUseAutomobileCallback = 43;',
        'constexpr std::uint32_t kUseAutomobileCallback = 42;', 1),
]


def main():
    src = Path(sys.argv[1])
    texts = {}
    for f in {s[0] for s in STEPS}:
        with open(src / f, encoding='utf-8', newline='') as fh:
            texts[f] = fh.read()
    for f, old, new, count in STEPS:
        n = texts[f].count(old)
        if n != count:
            sys.exit(f'ECHEC : {old!r} trouve {n} fois (attendu {count}) dans {f}')
        texts[f] = texts[f].replace(old, new)
        print(f'{f}: {old.strip()[:60]!r} -> {new.strip()[:60]!r} ({n})')
    for f, t in texts.items():
        with open(src / f, 'w', encoding='utf-8', newline='') as fh:
            fh.write(t)


if __name__ == '__main__':
    main()
