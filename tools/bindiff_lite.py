"""Associe les fonctions du HDE.exe modde a celles du hde.exe d'origine.

Principe : chaque fonction est desassemblee puis normalisee (les adresses
absolues et les cibles d'appel sont remplacees par des jetons). Deux fonctions
dont le code normalise est identique et unique dans chaque binaire sont
associees. Les associations sont ensuite propagees par le graphe d'appels :
si A_mod <-> A_orig, le i-eme appel de A_mod correspond au i-eme appel de A_orig
lorsque les deux listes d'appels ont la meme longueur.

Usage : python -I bindiff_lite.py <HDE_mod.exe> <hde_orig.exe> <sortie.json>
"""
import difflib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict

import capstone
import pefile

ADDR_RE = re.compile(r'0x[0-9a-f]+')


class Binary:
    def __init__(self, path):
        self.pe = pefile.PE(path)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.image = self.pe.get_memory_mapped_image()
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        text = [s for s in self.pe.sections if s.Name.startswith(b'.text')][0]
        self.text_lo = self.base + text.VirtualAddress
        self.text_hi = self.text_lo + text.Misc_VirtualSize
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.md.skipdata = True
        self.insns = list(self.md.disasm(
            self.image[text.VirtualAddress:text.VirtualAddress + text.Misc_VirtualSize],
            self.text_lo))
        self.index = {ins.address: n for n, ins in enumerate(self.insns)}
        self._find_functions()
        self._build_functions()

    def in_image(self, va):
        return self.base <= va < self.base + self.size

    def in_text(self, va):
        return self.text_lo <= va < self.text_hi

    def _find_functions(self):
        starts = set()
        for ins in self.insns:
            if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
                t = int(ins.op_str, 16)
                if self.in_text(t):
                    starts.add(t)
        # Pointeurs vers .text depuis les donnees (vtables, tables de rappel).
        for s in self.pe.sections:
            if s.Name.startswith(b'.text'):
                continue
            data = s.get_data()
            for off in range(0, len(data) - 3, 4):
                v = int.from_bytes(data[off:off + 4], 'little')
                if self.in_text(v) and v in self.index:
                    starts.add(v)
        # MSVC aligne les fonctions sur 16 octets apres un ret/jmp ou du
        # remplissage (nop / int3) : chaque adresse alignee qui suit l'un
        # d'eux et qui n'est pas elle-meme du remplissage ouvre une fonction.
        for i in range(len(self.insns) - 1):
            cur, nxt = self.insns[i], self.insns[i + 1]
            if nxt.address % 16 == 0 and nxt.mnemonic not in ('nop', 'int3') \
                    and (cur.mnemonic in ('nop', 'int3', 'ret') or
                         (cur.mnemonic == 'jmp' and not cur.op_str.startswith('0x'))):
                starts.add(nxt.address)
        self.starts = sorted(s for s in starts if s in self.index)

    def _build_functions(self):
        self.funcs = {}
        for i, start in enumerate(self.starts):
            end = self.starts[i + 1] if i + 1 < len(self.starts) else self.text_hi
            a, b = self.index[start], self.index.get(end, len(self.insns))
            body = self.insns[a:b]
            # On coupe le remplissage final (nop / int3).
            while body and body[-1].mnemonic in ('nop', 'int3'):
                body.pop()
            norm, calls, strs = [], [], []
            for ins in body:
                ops = ins.op_str
                if ins.mnemonic == 'call' and ops.startswith('0x'):
                    t = int(ops, 16)
                    calls.append(t)
                    norm.append('call F')
                    continue
                if ins.mnemonic.startswith('j') and ops.startswith('0x'):
                    t = int(ops, 16)
                    if start <= t < end:
                        norm.append(f'{ins.mnemonic} L{t - start:x}')
                    else:
                        norm.append(f'{ins.mnemonic} X')
                    continue

                def repl(m):
                    v = int(m.group(0), 16)
                    if self.in_image(v):
                        return 'A'
                    return m.group(0)

                norm.append(ins.mnemonic + ' ' + ADDR_RE.sub(repl, ops))
            text = '\n'.join(norm)
            self.funcs[start] = {
                'end': end,
                'n': len(body),
                'hash': hashlib.sha1(text.encode()).hexdigest(),
                'norm': norm,
                'calls': calls,
                'body': body,
            }

    def func_containing(self, va):
        import bisect
        i = bisect.bisect_right(self.starts, va) - 1
        if i < 0:
            return None
        s = self.starts[i]
        return s if va < self.funcs[s]['end'] else None


def vtables(binary):
    """Suites d'au moins 3 pointeurs consecutifs vers des debuts de fonction."""
    out = []
    for s in binary.pe.sections:
        if s.Name.startswith(b'.text'):
            continue
        data = s.get_data()
        va0 = binary.base + s.VirtualAddress
        run = []
        for off in range(0, len(data) - 3, 4):
            v = int.from_bytes(data[off:off + 4], 'little')
            if v in binary.funcs:
                run.append(v)
            else:
                if len(run) >= 3:
                    out.append(run)
                run = []
        if len(run) >= 3:
            out.append(run)
    return out


def similarity(mod, orig, a, b):
    return difflib.SequenceMatcher(
        None, mod.funcs[a]['norm'], orig.funcs[b]['norm'], autojunk=False).ratio()


def match(mod, orig, min_ratio=0.55):
    pairs = {}
    hm = defaultdict(list)
    ho = defaultdict(list)
    for a, f in mod.funcs.items():
        if f['n'] >= 6:
            hm[f['hash']].append(a)
    for a, f in orig.funcs.items():
        if f['n'] >= 6:
            ho[f['hash']].append(a)
    for h, la in hm.items():
        lb = ho.get(h)
        if lb and len(la) == 1 and len(lb) == 1:
            pairs[la[0]] = lb[0]
    used = set(pairs.values())

    def add(x, y, check):
        if x in pairs or y in used or x not in mod.funcs or y not in orig.funcs:
            return False
        if check and similarity(mod, orig, x, y) < min_ratio:
            return False
        pairs[x] = y
        used.add(y)
        return True

    vt_mod, vt_orig = vtables(mod), vtables(orig)
    changed = True
    while changed:
        changed = False
        # 1) Listes d'appels de meme longueur : association position par position.
        for a, b in list(pairs.items()):
            ca, cb = mod.funcs[a]['calls'], orig.funcs[b]['calls']
            if len(ca) == len(cb) and ca:
                for x, y in zip(ca, cb):
                    changed |= add(x, y, False)
        # 2) Listes d'appels differentes : alignement sur les appels deja associes.
        for a, b in list(pairs.items()):
            ca, cb = mod.funcs[a]['calls'], orig.funcs[b]['calls']
            if len(ca) == len(cb) or not ca or not cb:
                continue
            ta = [f'{pairs[x]:x}' if x in pairs else 'm' + mod.funcs.get(x, {}).get('hash', '?')[:8] for x in ca]
            tb = [f'{y:x}' if y in used else 'm' + orig.funcs.get(y, {}).get('hash', '?')[:8] for y in cb]
            sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
            for tag, a1, a2, b1, b2 in sm.get_opcodes():
                if tag == 'replace' and a2 - a1 == b2 - b1:
                    for k in range(a2 - a1):
                        changed |= add(ca[a1 + k], cb[b1 + k], True)
        # 3) Vtables : une vtable modde et une vtable d'origine partageant au
        #    moins deux entrees associees sont alignees entree par entree.
        orig_slot = defaultdict(list)
        for vi, vt in enumerate(vt_orig):
            for k, f in enumerate(vt):
                orig_slot[f].append((vi, k))
        for vt in vt_mod:
            votes = Counter()
            for k, f in enumerate(vt):
                if f in pairs:
                    for vi, k2 in orig_slot.get(pairs[f], []):
                        votes[(vi, k2 - k)] += 1
            if not votes:
                continue
            (vi, shift), n = votes.most_common(1)[0]
            if n < 2:
                continue
            other = vt_orig[vi]
            for k, f in enumerate(vt):
                j = k + shift
                if 0 <= j < len(other):
                    changed |= add(f, other[j], True)
    return pairs


def main():
    mod, orig = Binary(sys.argv[1]), Binary(sys.argv[2])
    pairs = match(mod, orig)
    exact = sum(1 for a, b in pairs.items() if mod.funcs[a]['hash'] == orig.funcs[b]['hash'])
    print(f'fonctions mod={len(mod.funcs)} orig={len(orig.funcs)} associees={len(pairs)} identiques={exact}')
    json.dump({f'{a:#x}': f'{b:#x}' for a, b in pairs.items()}, open(sys.argv[3], 'w'), indent=0)


if __name__ == '__main__':
    main()
