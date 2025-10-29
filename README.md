# Variable-Filled Video Templates MVP

This repository contains a minimal prototype that demonstrates how a creator can
publish a video template with viewer-facing variables that get filled on the
viewer side. The goal is to show the emotional impact of lightweight
personalization without requiring the viewer to upload their likeness.

The prototype focuses on three ideas:

1. **Template bundle** – a JSON description of the video layers, caption timing,
   and required variables (`templates/castle_run_template.json`).
2. **On-device resolver** – a small Python script that swaps in the viewer's
   context (name, location, team) at runtime.
3. **Micro-renderer** – local code that composites a background, variable-aware
   text, captions, and a toy audio cue, producing a personalized `.mp4` and
   `.srt` pair.

## Quickstart

1. Install the Python dependencies (MoviePy + Pillow):

   ```bash
   pip install -r requirements.txt
   ```

2. Generate a personalized clip by passing the variables you want to fill:

   ```bash
   python scripts/personalize_video.py templates/castle_run_template.json \
       --var VAR_NAME=Jordan --var VAR_LOCATION="the Moon" --var VAR_TEAM=Wolves \
       --output outputs/jordan_castle_run.mp4
   ```

   This command emits:

   - `outputs/jordan_castle_run.mp4`: a short clip with the updated on-screen
     text and tone-cue derived from the viewer's name.
   - `outputs/jordan_castle_run.srt`: captions that mirror the personalized
     dialogue.

## Template anatomy

The template file is intentionally simple so it can be hand-authored or edited
in a spreadsheet-like interface:

- `variables`: Lists every `[VAR_*]` token the template expects. Defaults or
  examples provide fallback values.
- `text_layers`: Defines when and where lines appear in-frame. The script wraps
  text automatically and centers it based on the `position` field.
- `caption_tracks`: Generates localized subtitle files so accessibility keeps up
  with personalization.
- `audio_segments`: Points to lightweight generators. For the MVP we synthesize a
  friendly sine-wave motif from the viewer's name so we can ship without third-party
  TTS APIs.

## Extending the MVP

- Swap the tone generator with a TTS service (ElevenLabs, Azure TTS, etc.) to
  speak the viewer's name. The script isolates this logic in
  `synthesize_tone_from_text` so you can plug in an API call.
- Replace the solid background with keyed footage by referencing pre-rendered
  assets (MoviePy can composite `VideoFileClip`s or tracked masks).
- Run the resolver inside a lightweight UI (Streamlit, Electron, or a browser
  worker) and gate variables behind explicit consent prompts.
- Export additional metadata (`tracks.json`) containing mask coordinates for
  texture swaps — the current template structure already has room to store
  per-layer IDs and start/end times.

## Why this is enough for emotional validation

Even with a solid-color background, the script delivers the "someone made this
for me" moment: the hero calls you by name, references your destination, and
rallies your team. That is sufficient for hallway tests before investing in
heavier ML-driven renders. From here you can iterate on polish while keeping the
viewer-owned personalization loop intact.
