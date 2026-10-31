"""Apparie les vtables (debut reference par le code) et compare des rangs choisis.

Debut de vtable = adresse de donnees referencee par une instruction et dont le
premier mot pointe vers une fonction. L'appariement mod -> original vient des
votes d'adresses globales (map_operands). Pour chaque paire, on indique si les
fonctions aux rangs demandes se correspondent.

Usage : python -I vtable_pairs.py <HDE_mod.exe> <hde_orig.exe> <operands.json> <va_vtable_mod|all> rangs_hex...
"""
import json
import re
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, similarity  # noqa: E402


def vtable_starts(binary):
    starts = set()
    for ins in binary.insns:
        for tok in re.findall(r'0x[0-9a-f]+', ins.op_str):
            if True:
                v = int(tok, 16)
                if binary.in_image(v) and not binary.in_text(v):
                    first = int.from_bytes(binary.image[v - binary.base:v - binary.base + 4], 'little')
                    if first in binary.funcs:
                        starts.add(v)
    return sorted(starts)


def entries(binary, start, starts):
    out = []
    va = start
    while True:
        if va != start and va in starts:
            break
        f = int.from_bytes(binary.image[va - binary.base:va - binary.base + 4], 'little')
        if not binary.in_text(f):
            break
        out.append(f)
        va += 4
    return out


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    globs = json.load(open(sys.argv[3]))['globals']
    pairs = match(mod, orig)
    sm, so = vtable_starts(mod), set(vtable_starts(orig))
    which = sys.argv[4]
    slots = [int(x, 16) for x in sys.argv[5:]]
    for vm in sm:
        if which != 'all' and vm != int(which, 16):
            continue
        vote = globs.get(f'{vm:#x}')
        if not vote:
            continue
        vo = int(next(iter(vote)), 16)
        if vo not in so:
            continue
        em, eo = entries(mod, vm, set(sm)), entries(orig, vo, so)
        good = sum(1 for k in range(min(len(em), len(eo))) if pairs.get(em[k]) == eo[k])
        line = f'vtable {vm:#x} ({len(em)}) -> {vo:#x} ({len(eo)}) rangs associes={good}'
        details = []
        for s in slots:
            k = s // 4
            a = em[k] if k < len(em) else None
            b = eo[k] if k < len(eo) else None
            if a is None or b is None:
                details.append(f'+{s:#x}:absent')
                continue
            if pairs.get(a) == b:
                details.append(f'+{s:#x}:OK')
            else:
                sim = similarity(mod, orig, a, b) if a in mod.funcs and b in orig.funcs else 0
                details.append(f'+{s:#x}:{a:#x}/{b:#x} sim={sim:.2f}')
        print(line, ' | '.join(details))


if __name__ == '__main__':
    main()
