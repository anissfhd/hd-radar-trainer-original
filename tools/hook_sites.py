"""Compare les octets aux points de hook (modde vs original).

Usage : python -I hook_sites.py <HDE_mod.exe> <hde_orig.exe> NOM=rva_mod:rva_orig [...]
"""
import sys

import capstone
import pefile


def show(path, rva, n=24):
    pe = pefile.PE(path)
    img = pe.get_memory_mapped_image()
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    raw = img[rva:rva + n]
    lines = [f'{i.address - base:#08x}: {i.bytes.hex():16s} {i.mnemonic} {i.op_str}'
             for i in md.disasm(raw, base + rva)][:6]
    return raw, lines


def main():
    for spec in sys.argv[3:]:
        name, rest = spec.split('=')
        a, b = (int(x, 16) for x in rest.split(':'))
        ra, la = show(sys.argv[1], a)
        rb, lb = show(sys.argv[2], b)
        same = ra[:8] == rb[:8]
        print(f'\n=== {name}  mod {a:#x}  orig {b:#x}  8 premiers octets {"IDENTIQUES" if same else "DIFFERENTS"}')
        for x, y in zip(la, lb):
            print(f'  {x:60.60s} | {y}')


if __name__ == '__main__':
    main()
