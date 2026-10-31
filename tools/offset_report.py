"""Rapport des offsets de structure du trainer et de leurs equivalents votes.

Usage : python -I offset_report.py <operands.json> <src_dir>
"""
import glob
import json
import re
import sys

d = json.load(open(sys.argv[1]))
disp = d['disp']
seen = {}
for f in sorted(glob.glob(sys.argv[2] + r'\*.cpp')):
    if f.endswith('ai_authority_helper.cpp'):
        continue
    text = open(f, encoding='utf-8', errors='ignore').read()
    for m in re.finditer(r'constexpr\s+std::(uintptr_t|uint32_t|uint8_t)\s+(k\w*Offset\w*)\s*=\s*(0x[0-9A-Fa-f\']+|\d+)', text):
        name, val = m.group(2), int(m.group(3).replace("'", ''), 0)
        seen.setdefault((name, val), f.rsplit('\\', 1)[1])
for (name, val), f in sorted(seen.items(), key=lambda x: x[0][1]):
    v = disp.get(f'{val:#x}')
    if not v:
        status = 'aucune donnee'
    else:
        top, n = next(iter(v.items()))
        total = sum(v.values())
        status = ('IDENTIQUE' if int(top, 16) == val else f'-> {top}') + f'  ({n}/{total})  {v}'
    print(f'{val:#06x} {name:42s} {f:18s} {status}')
