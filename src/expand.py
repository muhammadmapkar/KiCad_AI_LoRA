#!/usr/bin/env python3
"""Expand train.jsonl with pcbnew API / scripting / failure-fix examples."""
import json, os

here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets")

SYS = "You are KiCad AI Console, an advanced PCB engineering AI specializing in mixed-signal PCB design, EMG systems, servo power routing, grounding analysis, analog signal integrity, robotics electronics, and KiCad workflows."

def typo(s):
    subs = [("width","widht"),("ground","grond"),("servo","srvo"),("trace","trce"),
            ("script","scrpit"),("footprint","footprnt"),("clearance","clearence"),
            ("routing","routng"),("separate","seperate"),("position","postion"),
            ("layer","layr"),("board","baord")]
    for a,b in subs:
        if a in s:
            return s.replace(a,b,1)
    for i,ch in enumerate(s):
        if ch.lower() in "aeiou":
            return s[:i]+ch+s[i:]
    return s+"?"

def variant(u, mode):
    base = u.rstrip(".")
    if mode == 0:  return u
    if mode == 1:  return base.lower()
    if mode == 2:  return f"Is this a problem? {base}."
    if mode == 3:  return f"On my Teensy 4.0 robotics board: {base}. Review this."
    if mode == 4:  return typo(u)
    if mode == 5:  return base
    if mode == 6:  return f"Quick check - {base.lower()}."
    if mode == 7:  return f"Reviewing my KiCad script: {base}."
    if mode == 8:  return f"{base}. Any concerns?"
    if mode == 9:  return f"Script note: {base}."
    if mode == 10: return f"hey, {base.lower()}"
    if mode == 11: return f"{base} -- thoughts?"
    return u

# ---- pcbnew scripting pools: (user, assistant) ----------------------------
# units & VECTOR2I
p_units_bad = [
 ("My pcbnew script does track.SetWidth(1.5) to make a 1.5mm trace.",
  "SetWidth takes internal units (nanometers), so 1.5 sets a 1.5nm width. Convert first: track.SetWidth(pcbnew.FromMM(1.5)). All geometry setters in pcbnew expect internal units, so always wrap millimeter values in pcbnew.FromMM()."),
 ("Using pcbnew.wxPoint(pcbnew.FromMM(10), pcbnew.FromMM(20)) but it errors in KiCad 7.",
  "wxPoint was removed from the pcbnew API in KiCad 7. Use pcbnew.VECTOR2I(pcbnew.FromMM(10), pcbnew.FromMM(20)) instead. Anywhere old scripts used wxPoint/wxSize, switch to VECTOR2I/VECTOR2I for positions and sizes."),
 ("I read a pad position and it prints 10000000, I expected 10.",
  "Positions are stored in internal units (nanometers), so 10mm reads as 10000000. Convert for display with pcbnew.ToMM(pos.x) (and pos.y). Use FromMM when writing, ToMM when reading."),
 ("fp.SetPosition((pcbnew.FromMM(5), pcbnew.FromMM(5))) throws a type error.",
  "SetPosition expects a VECTOR2I, not a Python tuple. Wrap it: fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(5), pcbnew.FromMM(5))). The same applies to any position/size setter in the API."),
 ("I set clearance with pcbnew.FromMM(0.2) then multiply by 1e6 for nm.",
  "That double-converts. pcbnew.FromMM(0.2) already returns the value in nanometers (200000). Don't multiply again; pass FromMM's result directly."),
]
p_units_ok = [
 ("I convert every mm value with pcbnew.FromMM() before SetWidth or SetPosition.",
  "Correct. Internal units are nanometers, and pcbnew.FromMM() is the right converter for all geometry setters. Pair it with pcbnew.ToMM() when reading values back. No change needed."),
 ("Reading coordinates back I display them via pcbnew.ToMM().",
  "That's the right pairing: FromMM to write internal units, ToMM to read them back as millimeters. Good practice."),
]

# track width scripting
p_track_bad = [
 ("I loop over board.GetTracks() and SetWidth each one, but my vias got resized weirdly.",
  "board.GetTracks() also returns vias (PCB_VIA subclasses PCB_TRACK), so SetWidth hits them too. Filter first: for t in board.GetTracks(): if t.Type()==pcbnew.PCB_TRACE_T: t.SetWidth(pcbnew.FromMM(w)). Handle vias separately with SetWidth/SetDrill on PCB_VIA."),
 ("Widen only the /SERVO_PWR net tracks to 1.5mm via script.",
  "Iterate and filter by net and type:\n\nimport pcbnew\nb = pcbnew.LoadBoard(path)\nfor t in b.GetTracks():\n    if t.Type()==pcbnew.PCB_TRACE_T and t.GetNetname()=='/SERVO_PWR':\n        t.SetWidth(pcbnew.FromMM(1.5))\npcbnew.SaveBoard(path, b)\n\nSkipping vias avoids resizing them; SaveBoard persists the change."),
 ("My widen script runs with no error but the .kicad_pcb file is unchanged.",
  "You edited the in-memory board but never wrote it back. After the edits call pcbnew.SaveBoard(path, board) (or board.Save(path)). LoadBoard returns a copy, so changes are lost unless you save."),
 ("After SetWidth to 1.5mm my DRC now reports clearance violations.",
  "Widening the trace ate into the spacing to neighboring copper. Either reroute for more room, reduce the width increase, or increase clearance in the netclass. Always re-run DRC after batch width changes to catch new clearance errors."),
]
p_track_ok = [
 ("Before SetWidth I check t.Type()==pcbnew.PCB_TRACE_T so vias are skipped.",
  "Correct filtering. Vias are PCB_VIA and share the track container, so gating on PCB_TRACE_T keeps SetWidth off them. Handle via sizes with their own SetWidth/SetDrill. No change needed."),
]

# footprint query / placement
p_fp_bad = [
 ("board.GetFootprints() to find U1 but my reference comparison never matches.",
  "GetReference() returns a plain string, so compare with fp.GetReference()=='U1'. If it still misses, print the references to confirm exact casing/whitespace. Don't compare against the FOOTPRINT object itself."),
 ("Move every servo connector 5mm to the right in a script.",
  "for fp in board.GetFootprints():\n    if fp.GetReference().startswith('J'):\n        p = fp.GetPosition()\n        fp.SetPosition(pcbnew.VECTOR2I(p.x + pcbnew.FromMM(5), p.y))\nThen refill zones and pcbnew.SaveBoard(path, board). SetPosition on the FOOTPRINT moves its pads and silk together."),
 ("I called SetPosition but only the silkscreen moved, pads stayed.",
  "You moved a child graphic, not the footprint. Call SetPosition on the PCB_FOOTPRINT object from board.GetFootprints(); that relocates pads, silk, and courtyard together. Don't move individual drawings."),
]
p_fp_ok = [
 ("I place parts with fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))) then SaveBoard.",
  "Correct. SetPosition on the footprint moves the whole part in internal units, and SaveBoard persists it. Refill zones afterward if pours depend on the new location. Otherwise good."),
]

# zone fill
p_zone_bad = [
 ("I moved a GND footprint by script and saved, but the copper pour still shows the old shape.",
  "Zones aren't auto-refilled after edits. Run the filler before saving:\n\nfiller = pcbnew.ZONE_FILLER(board)\nfiller.Fill(board.Zones())\npcbnew.SaveBoard(path, board)\n\nThis recomputes the pour around the moved part."),
 ("How do I refill all copper pours from a script?",
  "Use the zone filler:\n\nfiller = pcbnew.ZONE_FILLER(board)\nfiller.Fill(board.Zones())\n\nCall it after any geometry edit and before pcbnew.SaveBoard() so the saved file has current pours."),
 ("My ground pour connects to a signal net instead of GND.",
  "The zone's net code is wrong. Set it from the net name and refill:\n\nz.SetNetCode(board.FindNet('GND').GetNetCode())\npcbnew.ZONE_FILLER(board).Fill(board.Zones())\n\nConfirm the exact net name (it may be '/GND') before assigning."),
]
p_zone_ok = [
 ("After moving parts I always run ZONE_FILLER.Fill(board.Zones()) before saving.",
  "Correct workflow. Refilling after edits keeps the pours consistent with the new geometry, and saving afterward persists it. No change needed."),
]

# nets & pads
p_net_bad = [
 ("Counting pads on /GND, but pad.GetNet() gives an object, not the name.",
  "GetNet() returns the NETINFO_ITEM. For the string use pad.GetNetname(), or pad.GetNet().GetNetname(). Compare that against '/GND'."),
 ("board.FindNet('GND') returns None.",
  "Net names are case-sensitive and often prefixed, so the net may be '/GND' rather than 'GND'. Enumerate board.GetNetInfo().NetsByName() (or print each pad's GetNetname()) to find the exact name, then pass that to FindNet."),
]
p_net_ok = [
 ("I look up nets with board.FindNet(name) and guard against a None result.",
  "Good defensive coding. FindNet returns None for an unknown name, so checking before use avoids an AttributeError. Confirm the exact prefixed name and you're set."),
]

# save / load
p_io_bad = [
 ("My standalone script does LoadBoard, edits, then ends, but the file is untouched.",
  "LoadBoard returns an in-memory copy; edits don't persist automatically. End with pcbnew.SaveBoard(path, board) to write the changes back to the .kicad_pcb file."),
 ("board.Save() in a standalone script raises an error.",
  "In a standalone (non-GUI) script use pcbnew.SaveBoard(path, board). board.Save() needs an explicit path too. Pass the file path so KiCad knows where to write."),
]
p_io_ok = [
 ("Standalone pattern: b=pcbnew.LoadBoard(p); edits; pcbnew.SaveBoard(p, b).",
  "That's the correct standalone read-modify-write pattern. LoadBoard for the in-memory board, edits, then SaveBoard to persist. No change needed."),
]

# layers
p_layer_bad = [
 ("I put a track on layer 31 to get bottom copper.",
  "Avoid magic layer numbers. Use the named constant: track.SetLayer(pcbnew.B_Cu) for bottom copper and pcbnew.F_Cu for top. Named constants are stable across versions; raw indices are not."),
 ("My silkscreen text ended up on F_Cu instead of the silk layer.",
  "You set the wrong layer constant. For front silkscreen use pcbnew.F_SilkS (and pcbnew.B_SilkS for the back). Set it with text.SetLayer(pcbnew.F_SilkS)."),
]
p_layer_ok = [
 ("I select copper layers with pcbnew.F_Cu and pcbnew.B_Cu constants.",
  "Correct. Named layer constants are the stable, readable way to target layers and won't break between KiCad versions. No change needed."),
]

# vias
p_via_bad = [
 ("via.SetDrill(0.3) but the drill didn't become 0.3mm.",
  "SetDrill expects internal units, so 0.3 is 0.3nm. Use via.SetDrill(pcbnew.FromMM(0.3)). Same for via.SetWidth(pcbnew.FromMM(...))."),
 ("I shrank via size in a script and now the annular ring looks too small.",
  "Annular ring = (width - drill)/2. After resizing, check that value stays above the fab minimum (~0.15mm). If via.GetWidth() is too close to via.GetDrill(), increase the pad width or reduce the drill."),
]
p_via_ok = [
 ("via.SetWidth(pcbnew.FromMM(0.6)); via.SetDrill(pcbnew.FromMM(0.3)) for a 0.15mm ring.",
  "Correct. A 0.6mm pad over a 0.3mm drill gives a 0.15mm annular ring, which meets typical fab minimums, and both values use FromMM. No change needed."),
]

# kicad-cli automation
p_cli_bad = [
 ("How do I run DRC from the pcbnew Python API?",
  "There isn't a clean in-process DRC in the older Python API. In KiCad 7+ run it via the CLI instead: kicad-cli pcb drc board.kicad_pcb --output drc.rpt. Add --exit-code-violations to fail a script/CI on any violation."),
 ("I export gerbers by hand from the GUI every time.",
  "Automate it with the CLI: kicad-cli pcb export gerbers -o gerbers/ board.kicad_pcb and kicad-cli pcb export drill -o gerbers/ board.kicad_pcb. Script both so fab output is one command."),
 ("kicad-cli pcb export gerber fails with unknown subcommand.",
  "The subcommand is plural: kicad-cli pcb export gerbers. Run kicad-cli pcb export --help to see the exact export targets (gerbers, drill, pos, etc.)."),
]
p_cli_ok = [
 ("CI runs kicad-cli pcb drc board.kicad_pcb --exit-code-violations to gate merges.",
  "Correct. --exit-code-violations returns nonzero when DRC finds problems, so the CI step fails the build on violations. That's exactly how to gate a merge on clean DRC."),
]

# multi-step batch scripts
p_batch_bad = [
 ("My batch script loads the board, widens the servo nets, but that's it.",
  "Two steps are missing. After widening, refill zones and save:\n\nfor t in b.GetTracks():\n    if t.Type()==pcbnew.PCB_TRACE_T and t.GetNetname()=='/SERVO_PWR':\n        t.SetWidth(pcbnew.FromMM(1.5))\npcbnew.ZONE_FILLER(b).Fill(b.Zones())\npcbnew.SaveBoard(path, b)\n\nThen optionally run kicad-cli pcb drc to verify."),
 ("After my script edits parts, the pours and DRC report look stale.",
  "Order of operations matters: edit geometry, then refill zones with ZONE_FILLER, then SaveBoard, then run kicad-cli pcb drc on the saved file. Running DRC before refill/save reports the old state."),
 ("One script processes 3 boards but reuses the same board object across them.",
  "Sharing one board object leaks edits between files. Call pcbnew.LoadBoard(path) fresh inside the loop for each board, edit, refill, and SaveBoard that path before moving on."),
]
p_batch_ok = [
 ("My pipeline is LoadBoard, edit widths, ZONE_FILLER.Fill, SaveBoard, then kicad-cli pcb drc.",
  "That ordering is correct: modify, refill pours, persist, then validate on the saved file. It keeps zones and the DRC report consistent with the edits. No change needed."),
]

# geometry / angle fixes
p_geo_bad = [
 ("I compute pad-to-pad distance in nm and compare it to 0.2 for a clearance check.",
  "You're mixing units: distances are in nanometers but 0.2 is millimeters. Convert one side, e.g. compare to pcbnew.FromMM(0.2), or wrap the distance in pcbnew.ToMM() before comparing to 0.2."),
 ("Setting a footprint rotation to 45 but it barely rotates.",
  "In KiCad 7 orientation uses EDA_ANGLE: fp.SetOrientation(pcbnew.EDA_ANGLE(45, pcbnew.DEGREES_T)). In older APIs rotation was in tenths of a degree (450 for 45 degrees). Match your KiCad version's convention."),
]
p_geo_ok = [
 ("For clearance checks I convert both distances to mm with ToMM before comparing.",
  "Correct. Converting to a common unit (mm) before the comparison avoids the nanometer/millimeter mismatch that silently breaks threshold checks. No change needed."),
]

pools = {
 "api_units":   (p_units_bad, p_units_ok),
 "api_tracks":  (p_track_bad, p_track_ok),
 "api_fp":      (p_fp_bad,    p_fp_ok),
 "api_zones":   (p_zone_bad,  p_zone_ok),
 "api_nets":    (p_net_bad,   p_net_ok),
 "api_io":      (p_io_bad,    p_io_ok),
 "api_layers":  (p_layer_bad, p_layer_ok),
 "api_vias":    (p_via_bad,   p_via_ok),
 "cli":         (p_cli_bad,   p_cli_ok),
 "batch":       (p_batch_bad, p_batch_ok),
 "geometry":    (p_geo_bad,   p_geo_ok),
}

PER_POOL = 20          # 11 pools -> 220 new lines
CORRECT_PER_POOL = 4   # 4/20 = 20% correct-design

# ---- seed dedup set from ALL existing lines --------------------------------
seen = set()
for fn in ["train.jsonl","val.jsonl"]:
    p = os.path.join(here,fn)
    if os.path.exists(p):
        for line in open(p):
            line=line.strip()
            if line:
                seen.add(json.loads(line)["messages"][1]["content"].strip().lower())

MODES = [0,5,1,4,3,2,6,7,8,9,10,11]

def build(pool, n, correct):
    out=[]
    for m in MODES:
        for base in pool:
            if len(out)>=n: return out
            u = variant(base[0], m)
            key = u.lower().strip()
            if key in seen: continue
            seen.add(key)
            out.append((u, base[1], correct))
    return out

new_lines=[]
counts={}
for cat,(bad,ok) in pools.items():
    got  = build(ok, CORRECT_PER_POOL, True)
    got += build(bad, PER_POOL-CORRECT_PER_POOL, False)
    counts[cat]=got
    new_lines.extend(got)

def rec(u,a):
    return {"messages":[
        {"role":"system","content":SYS},
        {"role":"user","content":u},
        {"role":"assistant","content":a},
    ]}

if __name__ == "__main__":
    # append to train.jsonl
    train_path=os.path.join(here,"train.jsonl")
    before=sum(1 for _ in open(train_path))
    with open(train_path,"a") as f:
        for u,a,c in new_lines:
            f.write(json.dumps(rec(u,a))+"\n")
    after=sum(1 for _ in open(train_path))

    print(f"added {len(new_lines)} new lines")
    print(f"train.jsonl: {before} -> {after}")
    correct=sum(1 for u,a,c in new_lines if c)
    print(f"correct-design in new: {correct}/{len(new_lines)} ({correct/len(new_lines)*100:.0f}%)")
    for cat in pools:
        tot=len(counts[cat]); cor=sum(1 for _u,_a,c in counts[cat] if c)
        print(f"  {cat:11s} +{tot:2d}  (correct {cor})")
