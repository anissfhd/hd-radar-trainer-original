"""Table des champs des classes acteur (C_actor / C_human / C_player / C_enemy).

Utilise les paires associees + les meilleurs candidats (rank_candidates) des
fonctions non associees situees dans une plage d'adresses du binaire modde, puis
vote champ par champ sur le code realigne.

Usage : python -I actor_fields.py <HDE_mod.exe> <hde_orig.exe> <lo> <hi> [min_disp] [max_disp]
"""
import difflib
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, similarity  # noqa: E402
from map_operands import operands, skeleton  # noqa: E402
from rank_candidates import callers, rank  # noqa: E402


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
    dmin = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0xF0
    dmax = int(sys.argv[6], 16) if len(sys.argv) > 6 else 0x400
    pairs = match(mod, orig)
    cm, co = callers(mod), callers(orig)
    work = {}
    for a in mod.funcs:
        if not lo <= a < hi:
            continue
        if a in pairs:
            if similarity(mod, orig, a, pairs[a]) >= 0.4:
                work[a] = pairs[a]
            continue
        res, _, _ = rank(mod, orig, pairs, cm, co, a, top=3)
        if res:
            b, tot, _, _, sim = max(res, key=lambda r: r[1] + r[4])
            if tot + sim >= 0.9 and sim >= 0.35:
                work[a] = b
    fields = defaultdict(Counter)
    where = defaultdict(set)
    for a, b in work.items():
        bm, bo = mod.funcs[a]['body'], orig.funcs[b]['body']
        sm = difflib.SequenceMatcher(None, [skeleton(mod, i) for i in bm],
                                     [skeleton(orig, i) for i in bo], autojunk=False)
        for tag, a1, a2, b1, b2 in sm.get_opcodes():
            if tag != 'equal':
                continue
            for k in range(a2 - a1):
                _, dm = operands(mod, bm[a1 + k])
                _, do = operands(orig, bo[b1 + k])
                for (rm, x), (ro, y) in zip(dm, do):
                    if rm in ('esp', 'ebp') or not dmin <= x < dmax:
                        continue
                    fields[x][y] += 1
                    where[x].add(a)
    print(f'fonctions utilisees: {len(work)}')
    for x in sorted(fields):
        c = fields[x]
        top, n = c.most_common(1)[0]
        print(f'{x:#06x} -> {top:#06x} ({top - x:+#x})  {n}/{sum(c.values())}  {dict((hex(k), v) for k, v in c.most_common(4))}  '
              f'fonctions={len(where[x])}')


if __name__ == '__main__':
    main()
