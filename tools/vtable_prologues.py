"""Affiche le prologue des fonctions designees par des rangs de vtable.

Usage : python -I vtable_prologues.py <exe> <va_vtable> rang_hex [...]
"""
import struct
import sys

import capstone
import pefile


def main():
    pe = pefile.PE(sys.argv[1])
    img = pe.get_memory_mapped_image()
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    vt = int(sys.argv[2], 16)
    for s in (int(x, 16) for x in sys.argv[3:]):
        f = struct.unpack('<I', img[vt - base + s:vt - base + s + 4])[0]
        raw = img[f - base:f - base + 12]
        ins = ' ; '.join(f'{i.mnemonic} {i.op_str}' for i in list(md.disasm(raw, f))[:4])
        print(f'  +{s:#05x} -> {f:#x}  {raw[:10].hex(" ")}   {ins}')


if __name__ == '__main__':
    main()
