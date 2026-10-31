"""Troisieme etape du portage (apres apply_port.py et apply_port_etape2.py).

Vehicule, vitesse du jeu, tir rapide, publication reseau du noclip.
Chaque point a ete verifie dans les deux binaires (octets, registres, champs
utilises par le code pose, conventions de retour) : voir docs/PORTAGE.md.

Usage : python -I apply_port_etape3.py <dossier src>
"""
import sys
from pathlib import Path

G = 'gameplay_mods.cpp'
W = 'weapon_mods.cpp'
STEPS = [
    # --- Braquage : fmul [0.6f] dans C_automobile::cbProc (CB_USE_AUTO cas 4).
    (G, "constexpr std::uintptr_t kAutomobileWheelTurnRateRva = 0x0005'52E9;",
        "constexpr std::uintptr_t kAutomobileWheelTurnRateRva = 0x0004'C276;", 1),
    (G, '0xD8, 0x0D, 0xC0, 0x66, 0x4F, 0x00};', '0xD8, 0x0D, 0xA4, 0x77, 0x4E, 0x00};', 1),
    # --- Vitesse du vehicule : fmul [ecx*4+table] (au lieu de edx*4) et fld/fmul.
    (G, "constexpr std::uintptr_t kAutomobileTargetSpeedHookRva = 0x0004'F1F3;",
        "constexpr std::uintptr_t kAutomobileTargetSpeedHookRva = 0x0004'7125;", 1),
    (G, "constexpr std::uintptr_t kAutomobileAccelerationHookRva = 0x0004'F22C;",
        "constexpr std::uintptr_t kAutomobileAccelerationHookRva = 0x0004'715E;", 1),
    (G, '0xD8, 0x0C, 0x95, 0x44, 0x7C, 0x4F, 0x00};', '0xD8, 0x0C, 0x8D, 0x54, 0x8B, 0x4E, 0x00};', 1),
    # --- Noclip vehicule : C_automobile::Tick, cadre 98h au lieu de C8h.
    (G, "constexpr std::uintptr_t kAutomobileTickRva = 0x0004'E540;",
        "constexpr std::uintptr_t kAutomobileTickRva = 0x0004'64E0;", 1),
    (G, '0x81, 0xEC, 0xC8, 0x00, 0x00, 0x00, 0x53, 0x55, 0x56, 0x8B, 0xF1};',
        '0x81, 0xEC, 0x98, 0x00, 0x00, 0x00, 0x53, 0x55, 0x56, 0x8B, 0xF1};', 1),
    # --- Vehicule invulnerable : C_automobile::Destroy, octets identiques.
    (G, "constexpr std::uintptr_t kAutomobileDestroyRva = 0x0004'FC80;",
        "constexpr std::uintptr_t kAutomobileDestroyRva = 0x0004'7AE0;", 1),
    # --- Vitesse du jeu : `sar eax,3 / mov [esp+14h],eax`, octets identiques.
    (G, "constexpr std::uintptr_t kMainLoopTimeScaleHookRva = 0x000C'D787;",
        "constexpr std::uintptr_t kMainLoopTimeScaleHookRva = 0x000B'E481;", 1),
    # --- Tir rapide : porte d'animation de C_human::UseItem.
    (W, "constexpr std::uintptr_t kUseItemAnimationGateRva = 0x0000'A02E;",
        "constexpr std::uintptr_t kUseItemAnimationGateRva = 0x0000'986E;", 1),
    (W, 'byte(0x8B); byte(0x83); dword(0x1BC);    // displaced full mov eax,[ebx+1BC]',
        'byte(0x8B); byte(0x83); dword(0x1A8);    // displaced full mov eax,[ebx+1A8]', 1),
    # --- Noclip : publication de la position reseau (dans C_human::Tick).
    (G, "constexpr std::uintptr_t kNoclipNetworkPublishRva = 0x0001'BC4E;",
        "constexpr std::uintptr_t kNoclipNetworkPublishRva = 0x0001'8087;", 1),
    (G, '0x8A, 0x45, 0xFF, 0x84, 0xC0, 0x0F,\n            0x84, 0x9B, 0x01, 0x00, 0x00};',
        '0x8A, 0x45, 0xFF, 0x84, 0xC0, 0x0F,\n            0x84, 0x99, 0x01, 0x00, 0x00};', 1),
    (G, "(module.base_address + 0x0001'BC59) -", "(module.base_address + 0x0001'8092) -", 1),
    (G, "jump_to(module.base_address + 0x0001'BDF4); // original `upd == false`",
        "jump_to(module.base_address + 0x0001'822B); // original `upd == false`", 1),
    # --- Masque de position reseau : construction de NM_HUMAN_POS.
    (G, "constexpr std::uintptr_t kHumanPositionSendRva = 0x0001'BD97;",
        "constexpr std::uintptr_t kHumanPositionSendRva = 0x0001'81CE;", 1),
    (G, '0x8D, 0x83, 0x10, 0x02, 0x00, 0x00};      // lea eax,[ebx+210h]',
        '0x8D, 0x83, 0xFC, 0x01, 0x00, 0x00};      // lea eax,[ebx+1FCh]', 1),
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
        print(f'{f}: {old.strip()[:70]!r} ({n})')
    for f, t in texts.items():
        with open(src / f, 'w', encoding='utf-8', newline='') as fh:
            fh.write(t)


if __name__ == '__main__':
    main()
