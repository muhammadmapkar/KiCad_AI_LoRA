# KiCad AI LoRA

Training data for a LoRA fine-tune of an LLM assistant ("KiCad AI Console") specialized
in PCB design review — mixed-signal layout, EMG signal-chain wiring, servo power routing,
grounding, and analog signal integrity. Built from real review feedback originating on the
ExoHand project (EMG-controlled robotic hand, Teensy 4.0 + custom KiCad PCB).

## Status

Early-stage. Currently just a seed dataset — no training/inference code yet.

## Repo layout

```
KiCad_AI_LoRA/
├── datasets/
│   ├── train.jsonl    chat-format fine-tuning examples (system/user/assistant turns)
│   └── val.jsonl      held-out chat-format examples for evaluation
└── requirements.txt   training stack dependencies (unsloth, transformers, trl, peft,
                       accelerate, bitsandbytes, datasets, torch)
```

## Dataset format

`datasets/train.jsonl` and `datasets/val.jsonl` are JSONL, one fine-tuning example per
line, OpenAI chat fine-tuning format (`{"messages": [{"role": ..., "content": ...}, ...]}`).
Each example currently has the same system prompt:

> You are KiCad AI Console, an advanced PCB engineering AI specializing in mixed-signal
> PCB design, EMG systems, servo power routing, grounding analysis, analog signal
> integrity, robotics electronics, and KiCad workflows.

followed by a one-line PCB design statement (e.g. "Servo trace width is 0.2mm for MG996R
servo power") and an assistant turn diagnosing the issue and recommending a fix.

**Current size: 356 examples** (178 train / 178 val).

## How to make it better / how to complete it

1. **[Done] Scale the dataset.** Dataset scaled to 356 examples (178 train / 178 val),
   mined from real review comments from the ExoHand KiCad project and generalized into
   user-statement/assistant-diagnosis pairs.
2. **Diversify the topics and phrasing.** Add coverage for other PCB review categories
   implied by the system prompt but not yet represented: power plane / ground plane
   splits, decoupling capacitor placement, connector/footprint selection, differential
   or shielded routing, thermal relief, DRC violations, BOM sourcing issues, multi-layer
   stackup choices. Vary user phrasing (terse vs. detailed, with/without units, with
   mistakes) so the model generalizes instead of memorizing.
3. **Add negative/neutral examples.** Include cases where a design choice is fine, so
   the model doesn't learn to always flag a problem.
4. **[Done] Decide and document base model + training method.** Base model: **Llama 3.1
   8B**, fine-tuned with **Unsloth** + **QLoRA**.
5. **Add the missing pieces for an actual trainable project:**
   - [Done] a training/eval split (`datasets/train.jsonl` + `datasets/val.jsonl`)
   - a training script or config (e.g. Axolotl YAML, or a PEFT/`transformers` script)
     with LoRA rank/alpha/target-modules specified
   - a short eval set of held-out PCB statements to sanity-check the fine-tuned model's
     outputs against the un-tuned base model
   - [Done] requirements.txt pinning the training stack
6. **Validate JSONL quality** as the set grows — dedup and check for label consistency
   before each training run.

## Credit

Sourced from PCB design review knowledge developed during the ExoHand project (Team
Orvyn, ECTE351).
