"""Controle hors jeu : les octets attendus par le trainer porte existent-ils
bien aux adresses visees dans le hde.exe d'origine ?

Usage : python -I verify_hooks.py <hde_orig.exe>
"""
import sys

import pefile

# (nom, RVA, octets attendus par le trainer porte)
SITES = [
    ('ProcessCheat', 0x96360, '83 EC 38 53 55'),
    ('SetSelectedItem', 0x6F40, '8B 44 24 04 56 8B F1 39 86 44 02 00 00'),
    ('DeleteAllItems', 0x58EB0, '55 8B E9 8B 45 14 85 C0 74 05'),
    ('WatchVectorErase', 0x32FB0, '8B 54 24 08 8B C1'),
    ('C_human::Die', 0x1C520, '83 EC 44 53 55 8B E9 56 57'),
    ('C_player::Die (vtable +E8)', 0x23730, 'A1 80 A5 4F 00 81 EC 18 01 00 00'),
    ('C_player::Explode (vtable +D0)', 0x25AB0, '83 EC 44 33 D2 53 55 56 8B F1'),
    ('C_player::Hit (vtable +EC)', 0x23CD0, '83 EC 6C 53 55'),
    ('C_player::IsEnemy (vtable +9C)', 0x24ED0, '8B 4C 24 04 8B 41 1C 48 74 23 48 75 20'),
    ('C_enemy::IsEnemy (vtable +9C)', 0x2F440, '56 8B F1 57 8B 46 28'),
    ('C_player::SetActive (vtable +6C)', 0x24F20, '53 8B 5C 24 08 56 8B F1 57'),
    ('C_map_manager::Tick', 0xA5320, 'A1 80 A5 4F 00'),
    ('C_camera::Tick', 0x54600, '55 8B EC 81 EC 4C 02 00 00'),
    ('LoadLoop', 0x58FA5, 'A1 C0 A6 4F 00'),
    ('ReleaseModelBranch', 0x593E5, '74 0C'),
    ('C_human::Tick', 0x16FD0, '55 8B EC 81 EC 48 03 00 00'),
    ('C_human::Tick apres model==null', 0x16FF3, '8B 8B A8 01 00 00'),
    ('Noclip publication', 0x18087, '8A 45 FF 84 C0 0F 84 99 01 00 00'),
    ('Noclip bloc mise a jour', 0x18092, '8B 43 28'),
    ('NM_HUMAN_POS', 0x181CE, '8B 4D F4 8D 83 FC 01 00 00'),
    ('Braquage', 0x4C276, 'D8 0D A4 77 4E 00'),
    ('Vitesse cible', 0x47125, 'D8 0C 8D 54 8B 4E 00'),
    ('Acceleration', 0x4715E, 'D9 44 24 20 D8 08'),
    ('C_automobile::Tick', 0x464E0, '81 EC 98 00 00 00 53 55 56 8B F1'),
    ('C_automobile::Destroy', 0x47AE0, '51 53 55 56 8B F1 57 33 FF 8B 46 24'),
    ('Boucle principale', 0xBE481, 'C1 F8 03 89 44 24 14'),
    ('UseItem tir rapide', 0x986E, '84 C0 74 18 8B 83 A8 01 00 00'),
    ('C_game_mission::CreateActor', 0x31010, '56 57 8B F9 8B 4C 24 0C'),
]


def main():
    pe = pefile.PE(sys.argv[1])
    img = pe.get_memory_mapped_image()
    ok = 0
    for name, rva, hexbytes in SITES:
        want = bytes.fromhex(hexbytes.replace(' ', ''))
        got = img[rva:rva + len(want)]
        good = got == want
        ok += good
        print(f'{"OK " if good else "KO "} {rva:#08x} {name:34s} {got.hex(" ").upper()}')
    print(f'\n{ok}/{len(SITES)} points conformes')
    sys.exit(0 if ok == len(SITES) else 1)


if __name__ == '__main__':
    main()
