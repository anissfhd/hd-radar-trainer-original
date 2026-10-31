"""Affiche les vtables qui contiennent une fonction du binaire modde et les
entrees correspondantes dans l'original.

Usage : python -I inspect_vtables.py <HDE_mod.exe> <hde_orig.exe> <va_mod> [...]
"""
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, vtables, similarity  # noqa: E402


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    inv = {b: a for a, b in pairs.items()}
    vm, vo = vtables(mod), vtables(orig)
    for target in (int(x, 16) for x in sys.argv[3:]):
        for vt in vm:
            if target not in vt:
                continue
            votes = Counter()
            for k, f in enumerate(vt):
                if f in pairs:
                    for vi, other in enumerate(vo):
                        if pairs[f] in other:
                            votes[(vi, other.index(pairs[f]) - k)] += 1
            print(f'\n=== vtable modde contenant {target:#x} ({len(vt)} entrees), votes={votes.most_common(3)}')
            best = votes.most_common(1)[0][0] if votes else None
            for k, f in enumerate(vt):
                o = None
                if best:
                    vi, sh = best
                    if 0 <= k + sh < len(vo[vi]):
                        o = vo[vi][k + sh]
                mark = '<==' if f == target else ''
                p = pairs.get(f)
                r = f'{similarity(mod, orig, f, o):.2f}' if o else '-'
                print(f'  [{k:2d}] mod {f:#x} n={mod.funcs[f]["n"]:4d}  pair={p and hex(p)}  slot_orig={o and hex(o)} '
                      f'n={o and orig.funcs[o]["n"]} sim={r} {mark}')


if __name__ == '__main__':
    main()
