# KiCad AI Co-Pilot (LoRA)

Fine-tuned LLM that turns natural-language prompts into valid KiCad Python scripts. Ships as a KiCad plugin. Engineer stays in the loop — it drafts, you review and run.

## What it does

You type plain English ("add a ground plane", "widen servo power traces"). The model generates KiCad scripting API Python. You approve, KiCad runs it.

Co-pilot, not autopilot. Every script is reviewed before execution.

## What it solves

KiCad's Python API is clunky and most PCB engineers don't script. This bridges the gap: natural language in, working board edits out. Faster design, lower skill barrier.

Domain focus: grounding, decoupling, stackup, DRC, thermal relief, signal integrity, mixed-signal layout, connector routing, BOM sourcing.

## Stack

- Base model: Llama 3.1 8B
- Method: LoRA / QLoRA via Unsloth
- Training: Google Colab (T4 GPU)
- Data format: JSONL, chat format (system/user/assistant turns)

## Repo layout
