#!/usr/bin/env python3
import json, random, os
import gen     # reuse pools + SYS from generator
import expand  # reuse api/cli/batch/geometry pools

random.seed(7)
here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets")

# Build assistant-text -> category map from the generator pools
asst2cat = {}
for cat,(bad,ok) in gen.pools.items():
    for _u,a in bad+ok:
        asst2cat[a] = cat
for cat,(bad,ok) in expand.pools.items():
    for _u,a in bad+ok:
        asst2cat[a] = cat
# the 2 seed examples
asst2cat["This trace width is unsafe for MG996R startup and stall current levels. A 0.2mm trace may create excessive voltage drop and thermal stress. Increase the trace width to approximately 1.2mm or larger depending on copper thickness, expected current draw, and routing length. Keep servo power routing separated from sensitive analog EMG traces."] = "servo"
asst2cat["This routing increases the risk of switching noise injection into sensitive EMG analog signals. Long parallel routing near servo power lines can introduce ADC instability and inaccurate EMG readings. Increase separation between analog and power traces, avoid parallel routing where possible, and maintain clean analog grounding practices."] = "emg"

# Load current full corpus (train + val), dedup by user line
recs = []
seen = set()
for fn in ["train.jsonl","val.jsonl"]:
    p = os.path.join(here,fn)
    if not os.path.exists(p): continue
    for line in open(p):
        line=line.strip()
        if not line: continue
        o = json.loads(line)
        u = o["messages"][1]["content"].strip().lower()
        if u in seen: continue
        seen.add(u)
        a = o["messages"][2]["content"]
        cat = asst2cat.get(a)
        assert cat, "unlabeled: "+a[:60]
        recs.append((cat,o))

# Stratified 90/10 split
by_cat = {}
for cat,o in recs:
    by_cat.setdefault(cat,[]).append(o)

train, val = [], []
for cat, lst in by_cat.items():
    random.shuffle(lst)
    k = round(len(lst)*0.10)
    val.extend((cat,o) for o in lst[:k])
    train.extend((cat,o) for o in lst[k:])

random.shuffle(train); random.shuffle(val)

with open(os.path.join(here,"train.jsonl"),"w") as f:
    for _c,o in train: f.write(json.dumps(o)+"\n")
with open(os.path.join(here,"val.jsonl"),"w") as f:
    for _c,o in val: f.write(json.dumps(o)+"\n")

from collections import Counter
tc=Counter(c for c,_ in train); vc=Counter(c for c,_ in val)
tot=len(train)+len(val)
print(f"TOTAL {tot}  TRAIN {len(train)} ({len(train)/tot*100:.1f}%)  VAL {len(val)} ({len(val)/tot*100:.1f}%)")
print(f"{'category':12s} {'total':>5s} {'train':>5s} {'val':>4s} {'val%':>6s}")
for cat in gen.pools:
    t=tc[cat]; v=vc[cat]
    print(f"{cat:12s} {t+v:5d} {t:5d} {v:4d} {v/(t+v)*100:5.1f}%")
