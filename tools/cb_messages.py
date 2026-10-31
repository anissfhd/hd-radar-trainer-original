"""Associe les numeros de message cbProc du modde a ceux de l'original.

cbProc commence par `msg-2` puis un switch a deux tables (octets d'index puis
adresses). Pour chaque message, le code de la branche (jusqu'au premier ret ou
saut inconditionnel, 40 instructions max) est normalise et compare entre les
deux binaires ; chaque message du modde recoit le message d'origine le plus
semblable.

Usage : python -I cb_messages.py <HDE_mod.exe> <hde_orig.exe> va_cbproc_mod va_cbproc_orig [msg...]
"""
import difflib
import re
import struct
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from bindiff_lite import Binary  # noqa: E402
from map_operands import skeleton  # noqa: E402


def switch_table(b, fn):
    body = b.funcs[fn]['body'] if fn in b.funcs else []
    lo = count = idx_tbl = jmp_tbl = None
    for ins in body[:20]:
        m = re.match(r'(?:add|lea) .*?(-?0x[0-9a-f]+|-\d+)', f'{ins.mnemonic} {ins.op_str}')
        if ins.mnemonic == 'add' and ins.op_str.endswith('-2'):
            lo = 2
        if ins.mnemonic == 'lea' and '- 2]' in ins.op_str:
            lo = 2
        if ins.mnemonic == 'cmp' and ins.op_str.startswith('eax, 0x'):
            count = int(ins.op_str.split(', ')[1], 16) + 1
        if ins.mnemonic == 'mov' and 'byte ptr [eax + 0x' in ins.op_str:
            idx_tbl = int(re.search(r'0x[0-9a-f]+', ins.op_str.split('[')[1]).group(0), 16)
        if ins.mnemonic == 'jmp' and '*4 + 0x' in ins.op_str:
            jmp_tbl = int(re.search(r'\+ (0x[0-9a-f]+)', ins.op_str).group(1), 16)
    out = {}
    for k in range(count):
        i = b.image[idx_tbl - b.base + k]
        out[lo + k] = struct.unpack('<I', b.image[jmp_tbl - b.base + 4 * i:jmp_tbl - b.base + 4 * i + 4])[0]
    return out


def branch(b, va, limit=40):
    n = b.index.get(va)
    if n is None:
        return []
    out = []
    for ins in b.insns[n:n + limit]:
        out.append(skeleton(b, ins))
        if ins.mnemonic in ('ret', 'jmp'):
            break
    return out


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    tm = switch_table(mod, int(sys.argv[3], 16))
    to = switch_table(orig, int(sys.argv[4], 16))
    default_m = max(set(tm.values()), key=list(tm.values()).count)
    default_o = max(set(to.values()), key=list(to.values()).count)
    want = [int(x) for x in sys.argv[5:]] or sorted(tm)
    for msg in want:
        h = tm.get(msg)
        if h is None:
            print(f'msg {msg}: hors table')
            continue
        if h == default_m:
            print(f'msg {msg:2d}: branche par defaut (ignore)')
            continue
        bm = branch(mod, h)
        scores = []
        for mo, ho in to.items():
            if ho == default_o:
                continue
            r = difflib.SequenceMatcher(None, bm, branch(orig, ho), autojunk=False).ratio()
            scores.append((r, mo))
        scores.sort(reverse=True)
        best = ', '.join(f'{mo}({r:.2f})' for r, mo in scores[:3])
        print(f'msg {msg:2d} -> {best}')


if __name__ == '__main__':
    main()
