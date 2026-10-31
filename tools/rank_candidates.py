"""Classe les fonctions de l'original candidates pour une fonction du modde.

Score = recouvrement des appelees deja associees + recouvrement des appelants
deja associes + similarite du code normalise.

Usage : python -I rank_candidates.py <HDE_mod.exe> <hde_orig.exe> <va_mod> [...]
"""
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, similarity  # noqa: E402


def callers(binary):
    out = defaultdict(set)
    for a, f in binary.funcs.items():
        for c in f['calls']:
            out[c].add(a)
    return out


def rank(mod, orig, pairs, cm, co, target, top=6):
    callee_m = {pairs[c] for c in mod.funcs[target]['calls'] if c in pairs}
    caller_m = {pairs[c] for c in cm.get(target, ()) if c in pairs}
    scores = []
    cand = set()
    for c in callee_m:
        cand |= co.get(c, set())
    for c in caller_m:
        cand.update(orig.funcs[c]['calls'])
    for b in cand:
        if b not in orig.funcs:
            continue
        ce = set(orig.funcs[b]['calls'])
        cr = co.get(b, set())
        s1 = len(callee_m & ce) / max(1, len(callee_m | ce))
        s2 = len(caller_m & cr) / max(1, len(caller_m | cr))
        scores.append((s1 + s2, s1, s2, b))
    scores.sort(reverse=True)
    out = []
    for tot, s1, s2, b in scores[:top]:
        out.append((b, tot, s1, s2, similarity(mod, orig, target, b)))
    return out, len(callee_m), len(caller_m)


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    cm, co = callers(mod), callers(orig)
    for t in (int(x, 16) for x in sys.argv[3:]):
        f = mod.func_containing(t)
        res, ne, nr = rank(mod, orig, pairs, cm, co, f)
        print(f'\n{t:#x} (fonction {f:#x}, n={mod.funcs[f]["n"]}, appelees associees={ne}, appelants associes={nr})')
        for b, tot, s1, s2, sim in res:
            print(f'   {b:#x} n={orig.funcs[b]["n"]:5d} score={tot:.2f} (appelees {s1:.2f}, appelants {s2:.2f}) sim={sim:.2f}')


if __name__ == '__main__':
    main()
