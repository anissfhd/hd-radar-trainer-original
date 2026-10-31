"""Vote des correspondances d'adresses globales et de deplacements [reg+disp].

Les fonctions associees sont realignees sur un code normalise ou les adresses
ET les deplacements sont masques ; chaque paire d'instructions alignees fournit
des couples (valeur modde -> valeur d'origine). Les votes sont agreges par
valeur et, pour les deplacements, par fonction (pour garder le contexte de
classe).

Usage : python -I map_operands.py <HDE_mod.exe> <hde_orig.exe> <sortie.json>
"""
import difflib
import json
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, similarity  # noqa: E402

MEM_RE = re.compile(r'\[([a-z]{3})(?: \+ [a-z]{3}\*\d)? ([+-]) (0x[0-9a-f]+)\]')
ABS_RE = re.compile(r'0x[0-9a-f]+')


def skeleton(binary, ins):
    ops = ins.op_str
    if ins.mnemonic == 'call' or ins.mnemonic.startswith('j'):
        return ins.mnemonic
    ops = MEM_RE.sub(lambda m: f'[{m.group(1)}+D]', ops)
    ops = ABS_RE.sub(lambda m: 'A' if binary.in_image(int(m.group(0), 16)) else 'I', ops)
    return ins.mnemonic + ' ' + ops


def operands(binary, ins):
    abs_ = [int(x, 16) for x in ABS_RE.findall(ins.op_str) if binary.in_image(int(x, 16))]
    disp = [(m.group(1), int(m.group(3), 16) * (-1 if m.group(2) == '-' else 1))
            for m in MEM_RE.finditer(ins.op_str)]
    return abs_, disp


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    glob_votes = defaultdict(Counter)
    disp_votes = defaultdict(Counter)       # (reg-agnostique) disp -> disp
    disp_by_func = defaultdict(list)        # fonction modde -> [(disp_m, disp_o, reg)]
    for a, b in pairs.items():
        if similarity(mod, orig, a, b) < 0.5:
            continue
        bm, bo = mod.funcs[a]['body'], orig.funcs[b]['body']
        sa = [skeleton(mod, i) for i in bm]
        sb = [skeleton(orig, i) for i in bo]
        sm = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
        for tag, a1, a2, b1, b2 in sm.get_opcodes():
            if tag != 'equal':
                continue
            for k in range(a2 - a1):
                im, io = bm[a1 + k], bo[b1 + k]
                am, dm = operands(mod, im)
                ao, do = operands(orig, io)
                for x, y in zip(am, ao):
                    glob_votes[x][y] += 1
                for (rm, x), (ro, y) in zip(dm, do):
                    if rm in ('esp', 'ebp'):
                        continue
                    disp_votes[x][y] += 1
                    disp_by_func[a].append((x, y, rm, im.address))
    out = {
        'globals': {f'{k:#x}': {f'{v:#x}': n for v, n in c.most_common(4)} for k, c in glob_votes.items()},
        'disp': {f'{k:#x}': {f'{v:#x}': n for v, n in c.most_common(6)} for k, c in disp_votes.items()},
        'disp_by_func': {f'{k:#x}': [(f'{x:#x}', f'{y:#x}', r, f'{ad:#x}') for x, y, r, ad in v]
                         for k, v in disp_by_func.items()},
    }
    json.dump(out, open(sys.argv[3], 'w'), indent=0)
    print(f'globales={len(glob_votes)} deplacements={len(disp_votes)}')


if __name__ == '__main__':
    main()
