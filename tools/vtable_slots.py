"""Compare les vtables qui contiennent une fonction donnee, rang par rang.

Une vtable est reperee dans .rdata par la presence de la fonction ; on remonte
jusqu'au debut de la suite de pointeurs de code. Les deux vtables (modde /
original) sont affichees cote a cote avec l'association bindiff_lite.

Usage : python -I vtable_slots.py <HDE_mod.exe> <hde_orig.exe> va_mod:va_orig [...]
"""
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary, match, similarity  # noqa: E402


def tables_with(binary, func):
    out = []
    for s in binary.pe.sections:
        if s.Name.startswith(b'.text'):
            continue
        data = s.get_data()
        va0 = binary.base + s.VirtualAddress
        for off in range(0, len(data) - 3, 4):
            if int.from_bytes(data[off:off + 4], 'little') != func:
                continue
            start = off
            while start >= 4 and binary.in_text(int.from_bytes(data[start - 4:start], 'little')):
                start -= 4
            end = off
            while end + 4 <= len(data) - 4 and binary.in_text(int.from_bytes(data[end + 4:end + 8], 'little')):
                end += 4
            out.append((va0 + start, [int.from_bytes(data[o:o + 4], 'little') for o in range(start, end + 4, 4)],
                        (off - start) // 4))
    return out


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    for spec in sys.argv[3:]:
        fm, fo = (int(x, 16) for x in spec.split(':'))
        tm, to = tables_with(mod, fm), tables_with(orig, fo)
        print(f'\n##### {fm:#x} <-> {fo:#x} : vtables modde={[(hex(a), k) for a, _, k in tm]} orig={[(hex(a), k) for a, _, k in to]}')
        for (am, em, km), (ao, eo, ko) in zip(tm, to):
            print(f'  vtable modde {am:#x} (rang {km}, octet +{km * 4:#x}) | orig {ao:#x} (rang {ko}, octet +{ko * 4:#x})')
            for k in range(max(len(em), len(eo))):
                a = em[k] if k < len(em) else None
                b = eo[k] if k < len(eo) else None
                ok = a is not None and pairs.get(a) == b
                sim = f'{similarity(mod, orig, a, b):.2f}' if a in mod.funcs and b in orig.funcs else '-'
                print(f'    +{k * 4:#05x} {a and hex(a)!s:>10} {b and hex(b)!s:>10} {"OK" if ok else "  "} sim={sim}')


if __name__ == '__main__':
    main()
