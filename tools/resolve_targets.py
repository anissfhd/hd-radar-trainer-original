"""Traduit les adresses de code du trainer (HDE.exe modde) vers hde.exe d'origine.

Pour chaque RVA : trouve la fonction qui la contient dans le binaire modde,
la fonction associee dans l'original (bindiff_lite, sinon meilleur candidat de
rank_candidates), puis l'instruction correspondante par alignement difflib du
code normalise. Le contexte (instructions autour) est affiche pour verification.

Usage : python -I resolve_targets.py <HDE_mod.exe> <hde_orig.exe> <src_dir> [nom...]
"""
import difflib
import glob
import re
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match  # noqa: E402
from rank_candidates import callers, rank  # noqa: E402


def code_constants(src_dir):
    out = {}
    for f in glob.glob(src_dir + r'\*.cpp'):
        if f.endswith('ai_authority_helper.cpp'):
            continue
        text = open(f, encoding='utf-8', errors='ignore').read()
        for m in re.finditer(r'constexpr[^;\n]*?\b(k\w*Rva\w*)\s*=\s*(0x[0-9A-Fa-f\']+)', text):
            out[m.group(1)] = int(m.group(2).replace("'", ''), 16)
    return out


def align(mod, orig, fm, fo, im):
    sm = difflib.SequenceMatcher(None, mod.funcs[fm]['norm'], orig.funcs[fo]['norm'], autojunk=False)
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal' and a1 <= im < a2:
            return b1 + (im - a1), True
        if tag == 'replace' and a1 <= im < a2 and a2 - a1 == b2 - b1:
            return b1 + (im - a1), False
    return None, False


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    cm, co = callers(mod), callers(orig)
    wanted = set(sys.argv[4:])
    for name, rva in sorted(code_constants(sys.argv[3]).items(), key=lambda x: x[1]):
        if 'I3d' in name or (wanted and name not in wanted):
            continue
        va = mod.base + rva
        if not mod.in_text(va):
            continue
        fm = mod.func_containing(va)
        fo, how = pairs.get(fm), 'associee'
        if fo is None:
            res, _, _ = rank(mod, orig, pairs, cm, co, fm, top=3)
            if res:
                fo, tot, _, _, sim = max(res, key=lambda r: r[1] + r[4])
                how = f'candidat score={tot:.2f} sim={sim:.2f}'
        if fo is None:
            print(f'{name:36s} {rva:#08x}  AUCUN CANDIDAT (fonction {fm:#x})')
            continue
        bm, bo = mod.funcs[fm]['body'], orig.funcs[fo]['body']
        im = next((i for i, ins in enumerate(bm) if ins.address == va), None)
        if im is None:
            print(f'{name:36s} {rva:#08x}  pas sur une frontiere d\'instruction')
            continue
        io, exact = align(mod, orig, fm, fo, im)
        if io is None:
            print(f'{name:36s} {rva:#08x}  fonction {fm:#x} -> {fo:#x} ({how}) : instruction sans equivalent')
            continue
        t = bo[io].address
        print(f'{name:36s} {rva:#08x} -> {t - orig.base:#08x}  [{fm:#x}+{va - fm:#x} -> {fo:#x}+{t - fo:#x}] '
              f'{how} {"exact" if exact else "remplace"}')
        for k in range(-2, 4):
            a = bm[im + k] if 0 <= im + k < len(bm) else None
            b = bo[io + k] if 0 <= io + k < len(bo) else None
            sa = f'{a.mnemonic} {a.op_str}' if a else ''
            sb = f'{b.mnemonic} {b.op_str}' if b else ''
            print(f'      {sa:48.48s} | {sb}')


if __name__ == '__main__':
    main()
