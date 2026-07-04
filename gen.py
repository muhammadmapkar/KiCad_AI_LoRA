#!/usr/bin/env python3
import json, random, os
random.seed(42)

SYS = "You are KiCad AI Console, an advanced PCB engineering AI specializing in mixed-signal PCB design, EMG systems, servo power routing, grounding analysis, analog signal integrity, robotics electronics, and KiCad workflows."

data = []

# 1. Servo / motor power routing
servo_bad = [
 ("Servo power trace is 0.25mm feeding two MG996R servos.",
  "0.25mm is far too narrow for two MG996R servos. Combined stall current can approach 5A. On 1oz copper that width handles well under 1A before overheating. Widen the shared servo rail to at least 2.0-2.5mm on 1oz (or use 2oz copper), and consider separate rails per servo."),
 ("routing 6v servo rail at 0.3mm, current ~2.5A stall",
  "0.3mm on 1oz copper is undersized for a 2.5A stall current and will see significant heating and voltage drop. For a 2.5A path target roughly 1.2-1.5mm on 1oz (10C rise). Widen it, keep the run short, and add bulk capacitance near the servo connector."),
 ("Single MG996R power fed through 0.4mm trace, board is 1oz.",
  "For a single MG996R the running current is under 1A but stall reaches ~2.5A. 0.4mm on 1oz is marginal at stall and drops noticeable voltage. Increase to ~1.2mm on 1oz to keep the 10C rise margin and reduce IR drop."),
 ("servo vcc trace 8mil, powering 3 MG996R off one Teensy board",
  "8mil (0.2mm) cannot carry three servos. Three MG996R can pull 7A+ at simultaneous stall. That trace would overheat immediately. Use a dedicated power pour or a 2.5-3mm rail on 2oz copper fed directly from the battery/BEC, not through the Teensy."),
 ("I put the servo power and the Teensy 3.3V on the same 0.3mm trace.",
  "Never share a trace between servo power and the Teensy 3.3V logic. Servo current spikes will collapse the logic rail and can brown-out the Teensy 4.0. Separate them: servo 6V on a wide dedicated rail (>=1.5mm), 3.3V logic on its own trace, joined only at a single ground reference point."),
 ("Servo return current shares the 0.3mm signal ground trace.",
  "High servo return current through a thin 0.3mm ground trace creates ground bounce that corrupts analog and logic references. Give the servo return its own wide path back to the source and tie analog/digital grounds to that point only at a single star node."),
 ("Motor rail length is 120mm at 0.5mm width, 3A load.",
  "A 120mm run at 0.5mm and 3A gives excessive resistance and voltage drop (well over a few hundred mV) plus heating. Widen to ~1.8mm on 1oz, or shorten the run, or use a copper pour. Long high-current traces should always be widened or poured."),
 ("Powering MG996R directly from Teensy 4.0 5V pin.",
  "Do not power an MG996R from the Teensy 4.0 onboard regulator/5V pin. The servo's stall current will exceed what the USB/regulator path can supply and will brown out the MCU. Feed servos from a separate BEC or battery rail, sharing only ground with the Teensy."),
]
servo_ok = [
 ("Servo 6V rail routed as a 2.5mm trace on 2oz copper for two MG996R.",
  "That is appropriately sized. Two MG996R at combined stall (~5A) are comfortably handled by 2.5mm on 2oz copper with a modest temperature rise. Keep the rail short, add bulk capacitance at the servo connectors, and keep it away from EMG analog lines. No change needed."),
 ("Using a 2mm wide dedicated servo power pour, separate BEC, common ground with Teensy.",
  "This is correct practice. A 2mm pour on a separate BEC easily supports MG996R currents, and sharing only ground with the Teensy avoids brown-outs while keeping a common reference. Good design."),
]

# 2. EMG analog signal integrity
emg_bad = [
 ("EMG electrode leads are unshielded 200mm ribbon next to the servo bus.",
  "Long unshielded 200mm leads next to a switching servo bus will pick up massive EMI and 50/60Hz mains hum, swamping the microvolt-level EMG signal. Use shielded/twisted electrode cabling, keep leads short, route away from servo power, and rely on the instrumentation amp's common-mode rejection plus a right-leg drive."),
 ("No input filtering on the EMG front end before the ADC.",
  "EMG occupies roughly 20-500Hz; without band-limiting you alias out-of-band noise into the ADC and pass mains hum. Add a passive RC or active band-pass (high-pass ~20Hz, low-pass ~500Hz) and an anti-aliasing filter below Fs/2, plus a 50/60Hz notch if hum persists."),
 ("EMG signal trace runs 40mm parallel and 0.1mm away from a PWM line.",
  "That coupling will inject PWM switching noise into the microvolt EMG signal. Increase spacing to several trace-widths, cross at 90 degrees rather than running parallel, and place a grounded guard trace or ground pour between the EMG line and any PWM/servo signal."),
 ("Instrumentation amp gain set to 1000 with no high-pass before it.",
  "A gain of 1000 with no high-pass will let electrode DC offset (tens of mV) saturate the in-amp output. Add a high-pass (~0.5-20Hz) ahead of high gain, or split gain into stages, so the DC half-cell offset is removed before the large gain stage."),
 ("EMG reference electrode not connected to any driven ground.",
  "Without a driven reference (right-leg drive) the body floats and common-mode mains interference dominates. Add a right-leg drive electrode fed from the in-amp common-mode point to actively reject 50/60Hz. This is essential for clean surface EMG."),
 ("Analog EMG ground and digital ground merged under the ADC with a via stitching fence.",
  "Stitching analog and digital grounds together under the ADC with many vias defeats the point of separating them and lets digital return currents flow through the analog reference. Join AGND and DGND at a single point at the ADC, not with a stitched fence."),
 ("EMG front-end powered from the same noisy 5V that drives the servos.",
  "Sharing the servo 5V rail injects switching ripple straight into the microvolt EMG front end. Give the analog front end its own filtered/regulated supply (e.g. a dedicated LDO with an LC or RC filter) referenced to analog ground, decoupled from the servo rail."),
 ("EMG traces routed over a gap/split in the ground plane.",
  "Routing the sensitive EMG signal across a plane split forces the return current on a long detour, creating a large loop antenna that picks up noise. Keep EMG traces over a continuous ground reference; never cross plane splits with analog signals."),
]
emg_ok = [
 ("EMG front end uses an INA333 with a 20-500Hz band-pass and a right-leg drive.",
  "That is a solid surface-EMG front end. The INA333's high CMRR plus a 20-500Hz band-pass matches the EMG bandwidth, and the right-leg drive actively suppresses mains common-mode. This configuration is correct; just keep leads shielded and short."),
 ("Guard trace of analog ground placed between EMG signal and the nearest PWM line.",
  "Good practice. A grounded guard trace between the EMG signal and the PWM line shunts coupled noise to ground and reduces crosstalk into the microvolt signal. Keep the guard tied to analog ground at both ends. No change needed."),
]

# 3. Grounding
gnd_bad = [
 ("Digital and analog grounds tied together at multiple points across the board.",
  "Multiple ties create ground loops and let digital return currents flow through the analog ground, raising the noise floor. Use a single connection point (a star node or a controlled bridge at the ADC) between AGND and DGND, not multiple scattered ties."),
 ("No ground plane; grounds are thin traces daisy-chained between parts.",
  "Daisy-chained ground traces share impedance, so each part's return current shifts every other part's reference. Add a solid ground plane (at least one full layer on a 2-layer board's bottom) to give a low-impedance common return."),
 ("Star ground point placed at the far corner away from the ADC.",
  "The star/single-point ground should be at the mixed-signal reference, typically under or beside the ADC, so analog and digital returns meet where it matters. Placing it in a far corner routes return currents across the board. Relocate the star point to the ADC."),
 ("Analog ground pour is split into isolated islands with no defined return.",
  "Isolated analog islands with no return path force currents through unintended routes and can float. Keep AGND as one contiguous pour tied to the system reference at a single point; don't leave orphaned ground islands."),
 ("High-speed digital return crosses the analog ground region.",
  "A fast digital return flowing through the analog ground injects switching noise into the analog reference. Keep digital return currents over the digital ground region and route high-speed signals so their image current stays out of the analog area."),
 ("Servo power ground and EMG analog ground share one narrow trace to the battery.",
  "Servo ground currents through a shared narrow trace modulate the EMG reference (common-impedance coupling). Route servo/power ground and analog ground separately back to the source, joining only at the single star point near the supply."),
 ("Split in the ground plane runs directly beneath a crystal oscillator.",
  "A plane split under the crystal breaks its return path and radiates. Keep a solid, continuous ground reference under clocks and oscillators; do not route plane splits beneath high-frequency components."),
]
gnd_ok = [
 ("AGND and DGND joined at a single point directly under the ADC.",
  "That is the textbook mixed-signal grounding approach. Tying analog and digital ground at one point under the ADC keeps the converter's reference clean while giving a defined return. Correct as designed."),
 ("Solid unbroken ground plane on layer 2 of a 4-layer robotics board.",
  "An unbroken ground plane on an inner layer is exactly what you want. It gives every signal a continuous low-impedance return and tight image currents. Keep it solid and avoid cutting slots through it. No change needed."),
]

# 4. Decoupling capacitors
dec_bad = [
 ("Teensy 4.0 3.3V decoupling cap placed 15mm from the power pin.",
  "15mm is too far; the trace inductance defeats the capacitor at high frequency. Place a 100nF decoupling cap within ~2-3mm of each power/ground pin with short, wide connections, and add bulk 10uF nearby. Proximity matters more than value."),
 ("Only one 10uF cap for the whole MCU, no small ceramics.",
  "A single 10uF cannot supply high-frequency transient current; its ESL makes it slow. Add a 100nF (0.1uF) ceramic at each Vcc pin for high-frequency decoupling, keep the 10uF as bulk. Use both, not one large cap alone."),
 ("Decoupling caps connected to the plane through a long thin 6mil trace and single via.",
  "Long thin connections and a single via add inductance that ruins decoupling effectiveness. Connect each cap to power and ground with short, wide traces and use two vias (or via-in-pad) to minimize loop inductance."),
 ("Using a 100uF electrolytic as the only decoupling on a 3.3V logic pin.",
  "An electrolytic has high ESR/ESL and is useless at logic switching frequencies. Use a 100nF ceramic directly at the pin for high frequency, and keep a ceramic/tantalum 10uF for bulk. Electrolytics are for low-frequency bulk only."),
 ("Op-amp for EMG has no decoupling cap on its supply pins.",
  "An undecoupled op-amp supply lets noise and transients modulate the microvolt EMG signal and can oscillate. Place a 100nF ceramic right at each supply pin (and a 1-10uF bulk nearby) with short returns to analog ground."),
 ("Shared single 100nF cap serving four adjacent IC power pins.",
  "One cap for four pins leaves most pins poorly decoupled because of the shared inductive path. Give each power pin its own 100nF placed at the pin. Per-pin decoupling is the goal, not a shared cap."),
]
dec_ok = [
 ("Each Teensy 4.0 Vcc pin has a 100nF 0402 within 2mm plus a shared 10uF bulk.",
  "That is correct decoupling. A 100nF per pin close to the pin handles high-frequency transients while the 10uF provides bulk charge. Keep the connections short with vias to the planes. No change needed."),
 ("EMG op-amp has 100nF at each rail and a 10uF bulk on the analog supply.",
  "Good analog decoupling. The 100nF at each rail suppresses high-frequency noise at the pin and the 10uF supplies bulk transient current, both referenced to analog ground. This is the right setup."),
]

# 5. Connector / footprint selection
conn_bad = [
 ("Using a 0.1in header rated 3A per pin to carry 5A servo power on one pin.",
  "A single 3A-rated header pin cannot carry 5A continuously. Either split the current across multiple parallel pins or choose a higher-current connector (e.g. a 2-3mm pitch power connector rated for the load). Don't exceed the per-contact current rating."),
 ("Servo connector footprint has no polarity/keying and can be reversed.",
  "An unkeyed servo connector invites reversed insertion, which back-feeds the servo and can destroy it or the board. Use a keyed/shrouded connector (or add a silkscreen key and a series protection diode), and clearly mark pin 1."),
 ("Downloaded footprint courtyard overlaps the neighboring part by 1mm.",
  "Overlapping courtyards mean the parts physically collide or can't be placed/soldered. Fix the footprint courtyard to the datasheet body+tolerance and space parts so courtyards don't overlap. Run DRC courtyard checks."),
 ("Chose a JST-PH 2.0mm connector for a 4A motor lead.",
  "JST-PH contacts are rated only ~2A per pin, so 4A on one contact overheats it. Use a higher-current series (e.g. JST-VH/XT-style or a 2-pin power connector rated >=5A) for a 4A motor lead."),
 ("Footprint pad size copied for a 0603 but the part is actually 0805.",
  "A 0603 land pattern is too small for an 0805 part, giving poor solder joints or tombstoning. Match the footprint to the actual 0805 package per IPC land pattern. Verify package size against the BOM/datasheet."),
 ("USB connector footprint has no mounting/mechanical pads, only signal pins.",
  "Without the mechanical shield/mounting pads the USB connector will rip off under cable stress. Use the full footprint including the shell/through-hole anchor tabs soldered to ground for mechanical retention."),
]
conn_ok = [
 ("Servo power uses a keyed 2-pin connector rated 5A per contact for MG996R.",
  "Appropriate choice. A keyed connector prevents reversed insertion and a 5A-per-contact rating covers MG996R stall with margin. Good selection; just confirm the mating wire gauge matches."),
 ("Footprint pulled from the manufacturer datasheet land pattern with correct courtyard.",
  "Using the manufacturer's recommended land pattern with a proper courtyard is best practice and avoids solder and placement issues. Verify orientation/pin 1 marking and you're set."),
]

# 6. Differential / shielded routing
diff_bad = [
 ("USB D+/D- routed with 8mm length mismatch and no controlled impedance.",
  "USB needs ~90 ohm differential impedance and tight intra-pair length matching (typically under ~5 mil skew). An 8mm mismatch destroys signal integrity. Match the pair lengths, route them together over a solid reference, and set the trace geometry for 90 ohm."),
 ("Differential pair split around a via so the two traces take different paths.",
  "Splitting the pair around a via breaks coupling and adds skew. Keep the two traces of a differential pair tightly coupled and symmetric, use matched via pairs, and never route them on different paths."),
 ("Diff pair routed over a plane split, one trace loses its reference.",
  "A plane split under a differential pair breaks the return path and creates common-mode noise/EMI. Keep both traces of the pair over one continuous reference plane; stitch or reroute so neither crosses a split."),
 ("Shielded cable drain wire left unconnected at the PCB.",
  "An unterminated shield/drain provides no protection and can act as an antenna. Terminate the shield to chassis/analog ground at the appropriate single end (usually the source) to drain coupled noise."),
 ("High-speed pair has stubs from test points hanging off each trace.",
  "Stubs on a high-speed differential pair cause reflections and impedance discontinuities. Remove the test-point stubs or move them inline; keep the pair clean and continuous."),
]
diff_ok = [
 ("USB pair routed as 90 ohm differential, length-matched within 0.1mm over a solid ground.",
  "That meets USB requirements: ~90 ohm differential impedance, tight length match, and a continuous reference plane. Signal integrity should be good. No change needed."),
 ("Differential pair kept tightly coupled with symmetric vias and constant spacing.",
  "Correct. Maintaining tight coupling, symmetric via transitions, and constant intra-pair spacing preserves impedance and rejects common-mode noise. Well routed."),
]

# 7. Thermal relief / copper pours
therm_bad = [
 ("High-current servo power pad connects to the pour with 4 thin thermal-relief spokes.",
  "Thermal-relief spokes add resistance and limit current into a high-current servo pad. For power connections use a solid (flooded) connection to the pour so full current flows; reserve thermal reliefs for hand-soldered signal pins."),
 ("Ground THT pins on a big copper pour have solid connections, hard to hand-solder.",
  "A solid connection to a large pour sinks heat away during hand soldering, causing cold joints. Use thermal-relief spokes on hand-soldered through-hole ground pins so the iron can heat the joint; keep solid pours only where high current demands it."),
 ("Copper pour clearance set to 0.05mm around 12V traces.",
  "0.05mm clearance is too tight for 12V and risks shorts/arcing and fab yield issues. Increase pour-to-trace clearance to at least your fab's minimum (commonly 0.2mm) and more for higher voltage per creepage rules."),
 ("Two separate ground pours left unstitched on opposite layers.",
  "Unstitched pours on different layers don't share a low-impedance return and can differ in potential. Add ground stitching vias to tie the pours together, especially around high-speed signals and board edges."),
 ("Large pour has no thermal reliefs anywhere, including the connector solder pins.",
  "With no thermal reliefs the connector's hand-soldered pins will be nearly impossible to heat, giving cold joints. Add thermal reliefs to hand-soldered pins while keeping solid connections for the high-current pads only."),
]
therm_ok = [
 ("Servo power pad flooded solid to the pour; signal ground pins use thermal reliefs.",
  "That is the right split: solid connection for the high-current servo pad to carry full current, thermal reliefs on the hand-soldered signal pins for solderability. Correct as designed."),
 ("Ground pours on top and bottom tied with a grid of stitching vias.",
  "Good practice. Stitching the pours ties them to a common low-impedance reference and controls return paths and EMI. Keep the via spacing tight near high-speed nets. No change needed."),
]

# 8. DRC violations / clearances
drc_bad = [
 ("DRC reports 0.1mm clearance between two 12V nets.",
  "0.1mm between 12V nets is below typical creepage/clearance guidance and risks shorts. For low voltage keep at least the fab minimum (~0.15-0.2mm); for 12V a bit more is prudent. Increase the spacing to clear the DRC and creepage rules."),
 ("Trace width set to 4mil but the fab minimum is 6mil.",
  "4mil is below the 6mil fab capability, so the board will fail fabrication or yield poorly. Set your DRC minimum trace/space to the fab's 6mil (0.15mm) rules and reroute any thinner traces."),
 ("Annular ring on vias is 0.02mm, DRC flags it.",
  "A 0.02mm annular ring is too small and risks breakout/open vias. Increase the ring to at least ~0.15mm (or the fab's minimum) by using a larger pad or smaller drill. Fix before fab."),
 ("Silkscreen overlaps pads, DRC silk-to-pad errors ignored.",
  "Silk over pads can interfere with soldering and looks unprofessional. Clip or move the silkscreen off the pads to clear the silk-to-mask/pad DRC. Don't ignore these before manufacturing."),
 ("Two 0.2mm traces spaced 0.08mm on a 6mil-capable fab.",
  "0.08mm spacing is under the 6mil (0.15mm) minimum and will short or fail fab. Respace the traces to at least 0.15mm and update the DRC rule to match the fab. Reroute the congested area."),
 ("Board edge clearance is 0.1mm from copper.",
  "Copper only 0.1mm from the routed edge risks exposure/shorting after depaneling. Pull copper back to at least ~0.25-0.5mm from the board edge (per fab) and add a keepout. Fix the edge clearance."),
]
drc_ok = [
 ("DRC passes with 0.2mm trace/space matching the fab's 6mil rules.",
  "That's within capability. 0.2mm exceeds the 6mil (0.15mm) minimum, so the design manufactures cleanly. Keeping the DRC ruleset aligned to the fab is exactly right. No change needed."),
 ("Via annular ring set to 0.15mm, board-edge copper keepout at 0.3mm.",
  "Both values are within common fab limits and give good manufacturing margin. The design should pass DRC and fabricate reliably. Correct as configured."),
]

# 9. Multi-layer stackup
stack_bad = [
 ("4-layer stackup ordered Signal / Signal / Power / Ground.",
  "Stacking two signal layers together with no adjacent reference gives them a poor return path. A better 4-layer order is Signal / Ground / Power / Signal so each signal layer is adjacent to a plane. Reorder the stackup."),
 ("Routing high-speed EMG-ADC clock on a 2-layer board with no ground plane.",
  "Without a ground plane the clock has no clean return and radiates. On a 2-layer board dedicate the bottom layer to a solid ground pour and route the clock on top over it, or move to 4 layers for a proper reference."),
 ("Power and ground planes placed on the outer layers, signals inside.",
  "Planes on the outside and signals buried inside is backwards for most designs; it complicates rework and leaves signals without ideal adjacent references. Put signals on outer layers and ground/power on inner layers for a standard 4-layer stack."),
 ("4-layer board with the ground plane not adjacent to the high-speed signal layer.",
  "If the ground plane isn't adjacent to your high-speed signals, the return current can't stay tight and impedance control suffers. Arrange the stackup so every high-speed signal layer is directly next to a solid ground plane."),
 ("2-layer board splitting ground between top and bottom with big cutouts.",
  "Big cutouts fragment the ground on a 2-layer board and break return paths. Keep one continuous ground pour (ideally the whole bottom layer) and route signals to avoid crossing any unavoidable gaps."),
]
stack_ok = [
 ("4-layer stackup: Signal / Ground / Power / Signal for the robotics board.",
  "That is a solid, standard 4-layer stackup. Each signal layer sits next to a plane for a good return, and the power/ground planes are adjacent for interplane capacitance. Correct choice."),
 ("2-layer board with the entire bottom layer as a solid ground pour.",
  "Good approach for 2 layers. A full bottom ground pour gives top-layer signals a continuous return reference and lowers impedance. Keep it unbroken under high-speed nets. No change needed."),
]

# 10. BOM / part sourcing
bom_bad = [
 ("BOM lists a 6.3V rated cap on the 5V servo rail.",
  "A 6.3V cap on a 5V rail has almost no derating margin, and servo transients can exceed 6.3V. Use at least a 10V (preferably 16V) rated capacitor on the 5V servo rail for reliable derating (aim for ~50% headroom)."),
 ("BOM has no manufacturer part numbers, just generic values.",
  "Generic values without MPNs make sourcing ambiguous and risk wrong footprints/specs at assembly. Add a specific manufacturer part number (and package) for each line so the assembler orders the exact part."),
 ("Footprint in layout is 0805 but the BOM part is an 0603 MPN.",
  "A footprint/BOM package mismatch means the part won't fit the land pattern. Reconcile them: either change the footprint to 0603 or pick an 0805 MPN. Verify every BOM line's package against the layout."),
 ("BOM specifies a part marked NRND (not recommended for new designs).",
  "An NRND part risks going obsolete mid-production. Substitute a currently active, in-stock equivalent now and check lifecycle status for all critical parts before committing the BOM."),
 ("Using a 10% tolerance cap in the EMG filter timing network.",
  "10% tolerance shifts the EMG filter corner frequencies noticeably part-to-part. Use 1-5% tolerance components (C0G/NP0 for stability) in the analog filter network so the 20-500Hz band stays accurate."),
 ("Resistor power rating not checked; 0402 used on a servo current-sense shunt.",
  "An 0402 may not dissipate the shunt's power at servo currents and will drift or fail. Compute I^2*R and pick a resistor package/rating with margin (often a larger 1206/2512 sense resistor). Verify power rating for every high-current part."),
]
bom_ok = [
 ("BOM uses 16V X7R caps on the 5V rail with full MPNs and packages.",
  "Good sourcing. 16V on a 5V rail gives healthy voltage derating, X7R is stable, and full MPNs make assembly unambiguous. No change needed; just confirm stock/lifecycle."),
 ("EMG filter caps are 1% C0G with specified MPNs.",
  "Correct for an analog filter. 1% C0G/NP0 parts keep the 20-500Hz corners accurate and stable over temperature, and the MPNs remove sourcing ambiguity. Good BOM discipline."),
]

pools = {
 "servo": (servo_bad, servo_ok),
 "emg": (emg_bad, emg_ok),
 "grounding": (gnd_bad, gnd_ok),
 "decoupling": (dec_bad, dec_ok),
 "connector": (conn_bad, conn_ok),
 "diff": (diff_bad, diff_ok),
 "thermal": (therm_bad, therm_ok),
 "drc": (drc_bad, drc_ok),
 "stackup": (stack_bad, stack_ok),
 "bom": (bom_bad, bom_ok),
}

def typo(s):
    subs = [("width","widht"),("ground","grond"),("servo","srvo"),("trace","trce"),
            ("capacitor","capaciter"),("clearance","clearence"),("signal","singal"),
            ("routing","routng"),("separate","seperate"),("impedance","impedence"),
            ("decoupling","decupling"),("connector","conector")]
    for a,b in subs:
        if a in s:
            return s.replace(a,b,1)
    # guarantee a change: double the first vowel
    for i,ch in enumerate(s):
        if ch.lower() in "aeiou":
            return s[:i]+ch+s[i:]
    return s+"?"

def variant(u, mode):
    base = u.rstrip(".")
    if mode == 0:
        return u
    if mode == 1:
        return base.lower()
    if mode == 2:
        return f"Is this a problem? {base}."
    if mode == 3:
        return f"On my Teensy 4.0 robotics board: {base}. Review this."
    if mode == 4:
        return typo(u)
    if mode == 5:
        return base
    if mode == 6:
        return f"Quick check - {base.lower()}."
    if mode == 7:
        return f"Reviewing my PCB: {base}."
    if mode == 8:
        return f"{base}. Any concerns?"
    if mode == 9:
        return f"Design note: {base}."
    if mode == 10:
        return f"hey, {base.lower()}"
    if mode == 11:
        return f"{base} -- thoughts?"
    return u

per_cat = 30
correct_per_cat = 6

examples = []
seen_users = set()

def build(pool, n, cat, correct):
    out = []
    modes = [0,5,1,4,3,2,6,7,8,9,10,11]
    # sweep every (mode, base) combination so we exhaust variety
    for m in modes:
        for base in pool:
            if len(out) >= n:
                return out
            u = variant(base[0], m)
            key = u.lower().strip()
            if key not in seen_users:
                seen_users.add(key)
                out.append((cat, u, base[1], correct))
    return out

for cat,(bad,ok) in pools.items():
    picked = build(ok, correct_per_cat, cat, True)
    picked += build(bad, per_cat-correct_per_cat, cat, False)
    assert len(picked) == per_cat, (cat, len(picked))
    examples.extend(picked)

assert len(examples) == 300, len(examples)

by_cat = {}
for e in examples:
    by_cat.setdefault(e[0], []).append(e)

val = []
train_new = []
for cat, lst in by_cat.items():
    random.shuffle(lst)
    val.extend(lst[:3])
    train_new.extend(lst[3:])

random.shuffle(train_new)
random.shuffle(val)

def rec(user, asst):
    return {"messages":[
        {"role":"system","content":SYS},
        {"role":"user","content":user},
        {"role":"assistant","content":asst},
    ]}

existing = [
 rec("Servo trace width is 0.2mm for MG996R servo power.",
     "This trace width is unsafe for MG996R startup and stall current levels. A 0.2mm trace may create excessive voltage drop and thermal stress. Increase the trace width to approximately 1.2mm or larger depending on copper thickness, expected current draw, and routing length. Keep servo power routing separated from sensitive analog EMG traces."),
 rec("EMG analog traces routed parallel to servo power traces.",
     "This routing increases the risk of switching noise injection into sensitive EMG analog signals. Long parallel routing near servo power lines can introduce ADC instability and inaccurate EMG readings. Increase separation between analog and power traces, avoid parallel routing where possible, and maintain clean analog grounding practices."),
]

outdir = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    with open(os.path.join(outdir,"train.jsonl"),"w") as f:
        for r in existing:
            f.write(json.dumps(r)+"\n")
        for cat,u,a,c in train_new:
            f.write(json.dumps(rec(u,a))+"\n")

    with open(os.path.join(outdir,"val.jsonl"),"w") as f:
        for cat,u,a,c in val:
            f.write(json.dumps(rec(u,a))+"\n")

    from collections import Counter
    train_cats = Counter([e[0] for e in train_new])
    val_cats = Counter([e[0] for e in val])
    correct_train = sum(1 for e in train_new if e[3])
    correct_val = sum(1 for e in val if e[3])
    print("TRAIN new:", len(train_new), "+2 existing =", len(train_new)+2)
    print("VAL:", len(val))
    for cat in pools:
        print(f"  {cat:11s} train={train_cats[cat]:2d} val={val_cats[cat]:2d} total={train_cats[cat]+val_cats[cat]}")
    print("correct train:", correct_train, "correct val:", correct_val, "total correct:", correct_train+correct_val, f"({(correct_train+correct_val)/300*100:.0f}%)")
