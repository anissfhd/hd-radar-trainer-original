"""Applique au code du trainer les correspondances VERIFIEES mod -> original.

Chaque entree a ete etablie avec les outils de ce dossier (bindiff_lite,
map_operands, actor_fields, vtable_pairs, hook_sites) et controlee a la main.
Le script echoue si une valeur attendue est introuvable : il ne s'applique
qu'une fois, sur la copie de base du trainer V165.

Ce qui n'est PAS ici garde volontairement les valeurs du mod : les fonctions
concernees verifient les octets du jeu avant toute ecriture et refuseront de
s'activer sur le hde.exe d'origine (voir docs/PORTAGE.md).

Usage : python -I apply_port.py <dossier src>
"""
import re
import sys
from pathlib import Path

# --- Constantes nommees : (fichier, nom, ancienne valeur, nouvelle valeur) ---
CONSTANTS = [
    # Adresses globales (votes unanimes sur les fonctions associees).
    ('trainer_process.cpp', 'kHDTickClassPointerRva', '0x0010AD4C', '0x000FA7E4'),
    ('gameplay_mods.cpp', 'kMissionPointerRva', '0x0010AD4C', '0x000FA7E4'),
    ('gameplay_mods.cpp', 'kGameConfigurationRva', "0x0010'86E0", "0x000F'8A68"),
    ('gameplay_mods.cpp', 'kInventoryTablesRva', "0x0010'AAD0", "0x000F'A570"),
    ('gameplay_mods.cpp', 'kInventorySceneGlobalRva', "0x0010'AC08", "0x000F'A6C0"),
    ('gameplay_mods.cpp', 'kStockWheelTurnRateAddress', "0x004F'66C0", "0x004E'77A4"),
    ('radar.cpp', 'kCollisionTablePointerRva', '0x0010AC04', '0x000FA6BC'),
    ('radar.cpp', 'kNetHostRva', '0x0010ABE4', '0x000FA69C'),
    ('radar.cpp', 'kNetJoinRva', '0x0010ABE5', '0x000FA69D'),
    ('weapon_mods.cpp', 'kWeaponTablePointerRva', '0x0010AAD0', '0x000FA570'),
    ('weapon_mods.cpp', 'kGameModeRva', '0x001086E0', '0x000F8A68'),

    # Code : fonctions associees dont les octets au point d'entree sont
    # identiques ou dont le code pose rejoue les octets lus en memoire.
    ('gameplay_mods.cpp', 'kProcessCheatHookRva', "0x0009'FC10", "0x0009'6360"),
    ('gameplay_mods.cpp', 'kProcessCheatHookRva', '0x0009FC10', '0x00096360'),
    ('gameplay_mods.cpp', 'kSetSelectedInventoryItemRva', '0x000076E0', '0x00006F40'),
    ('gameplay_mods.cpp', 'kSetSelectedItemRva', "0x0000'76E0", "0x0000'6F40"),
    ('gameplay_mods.cpp', 'kDeleteAllItemsRva', '0x00062E80', '0x00058EB0'),
    ('gameplay_mods.cpp', 'kWatchVectorEraseRva', '0x00039CB0', '0x00032FB0'),
    ('gameplay_mods.cpp', 'kHumanDieRva', "0x0002'08B0", "0x0001'C520"),
    ('radar.cpp', 'kMapManagerTickRva', '0x000B1AD0', '0x000A5320'),

    # Rangs de vtable (vtables C_player / C_enemy realignees ; le mod ajoute
    # huit methodes virtuelles a partir du rang 0x80).
    ('gameplay_mods.cpp', 'kPlayerIsEnemyVtableOffset', '0xA4', '0x9C'),
    ('gameplay_mods.cpp', 'kPlayerHitVtableOffset', '0x104', '0xEC'),
    ('gameplay_mods.cpp', 'kPlayerDieVtableOffset', '0x100', '0xE8'),
    ('gameplay_mods.cpp', 'kPlayerExplodeVtableOffset', '0xDC', '0xD0'),

    # Champs C_human / C_player : -0x14 entre 0x178 et 0x2E4 (le mod insere
    # 0x14 octets avant 0x178). Votes concordants, voir docs/analyse.
    ('gameplay_mods.cpp', 'kActorMoveDirectionOffset', '0x1AC', '0x198'),
    ('gameplay_mods.cpp', 'kActorFallSpeedOffset', '0x1B8', '0x1A4'),
    ('gameplay_mods.cpp', 'kActorCurrentPoseOffset', '0x1BC', '0x1A8'),
    ('gameplay_mods.cpp', 'kActorBrestFrameOffset', '0x1C4', '0x1B0'),
    ('gameplay_mods.cpp', 'kActorAimDirectionOffset', '0x1D0', '0x1BC'),
    ('gameplay_mods.cpp', 'kActorAimCountOffset', '0x1E8', '0x1D4'),
    ('gameplay_mods.cpp', 'kHumanNetworkSyncPositionOffset', '0x204', '0x1F0'),
    ('gameplay_mods.cpp', 'kActorUsingItemOffset', '0x250', '0x23C'),
    ('gameplay_mods.cpp', 'kHumanStayModeOffset', '0x254', '0x240'),
    ('gameplay_mods.cpp', 'kSelectedInventoryItemOffset', '0x258', '0x244'),
    ('gameplay_mods.cpp', 'kActorSelectedIndexOffset', '0x258', '0x244'),
    ('gameplay_mods.cpp', 'kActorFallingOffset', '0x264', '0x250'),
    ('gameplay_mods.cpp', 'kActorCollisionTestCountdownOffset', '0x274', '0x260'),
    ('gameplay_mods.cpp', 'kVoiceInstalledOffset', '0x280', '0x26C'),
    ('gameplay_mods.cpp', 'kHumanProgramOffset', '0x284', '0x270'),
    ('gameplay_mods.cpp', 'kProgramBeginOffset', '0x288', '0x274'),
    ('gameplay_mods.cpp', 'kProgramEndOffset', '0x28C', '0x278'),
    ('gameplay_mods.cpp', 'kHumanProgramDirtyOffset', '0x290', '0x27C'),
    ('gameplay_mods.cpp', 'kHumanCommandNewOffset', '0x291', '0x27D'),
    ('gameplay_mods.cpp', 'kHumanHoldingFireOffset', '0x292', '0x27E'),
    ('gameplay_mods.cpp', 'kHumanActorEnumCountOffset', '0x294', '0x280'),
    ('gameplay_mods.cpp', 'kHoldingFireInstalledOffset', '0x296', '0x282'),
    ('gameplay_mods.cpp', 'kHoldingFireOffset', '0x296', '0x282'),
    ('gameplay_mods.cpp', 'kHumanWatchActorsOffset', '0x298', '0x284'),
    ('gameplay_mods.cpp', 'kActorEnumInstalledOffset', '0x298', '0x284'),
    ('gameplay_mods.cpp', 'kActorEnumOffset', '0x298', '0x284'),
    ('gameplay_mods.cpp', 'kWatchVectorInstalledOffset', '0x29C', '0x288'),
    ('gameplay_mods.cpp', 'kWatchVectorOffset', '0x29C', '0x288'),
    ('gameplay_mods.cpp', 'kPlayerModeOffset', '0x2B4', '0x2A0'),
    ('gameplay_mods.cpp', 'kPlayerNoHitCheatOffset', '0x2D4', '0x2C0'),
    ('gameplay_mods.cpp', 'kPlayerInitResistanceOffset', '0x2D8', '0x2C4'),
    ('weapon_mods.cpp', 'kEquippedWeaponOffset', '0x244', '0x230'),
    ('weapon_mods.cpp', 'kSelectedIndexOffset', '0x258', '0x244'),
    ('weapon_mods.cpp', 'kShootCountdownOffset', '0x260', '0x24C'),
    ('radar.cpp', 'kActorHeadFrameOffset', '0x1C8', '0x1B4'),
    ('radar.cpp', 'kActorStayModeOffset', '0x254', '0x240'),
    ('radar.cpp', 'kActorActivePlayerOffset', '0x2B8', '0x2A4'),
]

# --- Octets attendus aux points de hook : (fichier, ancien, nouveau, nombre) ---
BYTES = [
    # ProcessCheat : `mov eax,105Ch` -> `sub esp,38h / push ebx / push ebp`.
    ('gameplay_mods.cpp', '0xB8, 0x5C, 0x10, 0x00, 0x00', '0x83, 0xEC, 0x38, 0x53, 0x55', 16),
    # C_map_manager::Tick : `mov eax,[0050AAE0]` -> `mov eax,[004FA580]`.
    ('radar.cpp', '0xA1, 0xE0, 0xAA, 0x50, 0x00', '0xA1, 0x80, 0xA5, 0x4F, 0x00', 1),
    # SetSelectedItem : `cmp [esi+258h],eax` -> `cmp [esi+244h],eax`.
    ('gameplay_mods.cpp', '0x39, 0x86, 0x58, 0x02, 0x00, 0x00', '0x39, 0x86, 0x44, 0x02, 0x00, 0x00', 2),
    # C_player::Explode : sub esp,44h / xor edx,edx / push ebx / push ebp /
    # push esi / mov esi,ecx (dix octets d'instructions completes).
    ('gameplay_mods.cpp', '0x83, 0xEC, 0x44, 0x53, 0x55, 0x56, 0x8B, 0xF1, 0x33, 0xC9',
     '0x83, 0xEC, 0x44, 0x33, 0xD2, 0x53, 0x55, 0x56, 0x8B, 0xF1', 2),
]


def main():
    src = Path(sys.argv[1])
    texts = {}
    for f in {e[0] for e in CONSTANTS} | {e[0] for e in BYTES}:
        with open(src / f, encoding='utf-8', newline='') as fh:
            texts[f] = fh.read()
    for f, name, old, new in CONSTANTS:
        pat = re.compile(r'(constexpr\s+std::\w+\s+' + name + r'\s*=\s*)' + re.escape(old) + r'\b')
        texts[f], n = pat.subn(lambda m: m.group(1) + new, texts[f])
        if n == 0:
            sys.exit(f'ECHEC : {name} = {old} introuvable dans {f}')
        print(f'{f}: {name} {old} -> {new} ({n})')
    for f, old, new, count in BYTES:
        n = texts[f].count(old)
        if n != count:
            sys.exit(f'ECHEC : {old!r} trouve {n} fois dans {f} (attendu {count})')
        texts[f] = texts[f].replace(old, new)
        print(f'{f}: octets [{old}] -> [{new}] ({n})')
    for f, t in texts.items():
        with open(src / f, 'w', encoding='utf-8', newline='') as fh:
            fh.write(t)


if __name__ == '__main__':
    main()
