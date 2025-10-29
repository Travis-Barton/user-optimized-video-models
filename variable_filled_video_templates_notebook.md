# Variable‑Filled Video Templates (Viewer‑Side Personalization)

## Vision
Creators publish *template videos* that contain human‑readable variables (e.g., `[VAR_NAME]`, `[VAR_TEAM]`, `[VAR_PET]`). A lightweight *variable‑filler* runs near the viewer (on‑device or edge) to personalize lines, props, textures, captions, and UI overlays so every viewer experiences a story starring “them,” without exposing their real face or voice to the creator or the open internet.

---

## Cultural Context & Evidence
**HardFork podcast insight:** The hosts discussed why many women are reluctant to put their likenesses online: the downsides far outweigh the fun, and the risks are asymmetric. They highlighted how these generative models are safer and more resonant when used *inside group chats*. In those small circles, you already have trust; friends make quick, low‑stakes, personally tailored videos for one another.  

This observation validates the core insight behind this project:
- **Creators as scalable friends:** The “friend making a personalized video for you” is the emotional model that works — small, intimate, safe.
- **Automation gap:** What people actually want isn’t to *upload themselves*; they want *creators to make many such personalized videos for them* automatically.
- **Friend approximation:** In a sense, creators (and their templates) are scalable proxies for your friends — expressing your interests, humor, and context through variables instead of likenesses.

That makes variable‑filled templates the missing infrastructure: they let creators act like “many friends” at once — personal without intrusion, intimate without surveillance.

---

## Why this matters
- **Psych safety:** No face uploads. No cross‑app face scraping. Viewers still get the “I’m the main character” effect.
- **Creator leverage:** One master cut → millions of personalized renders.
- **Ops cost:** Heavy model once (template); cheap filler many times.
- **Compliance:** Reduces biometric data handling by creators.

---

## Audience value
- Feeds become a series of stories about *me* (name, interests, locales) **without** sharing my likeness.
- “Rockstar effect” delivered privately.
- Mirrors the *trusted small‑group dynamics* observed in real‑world social media behavior.

---

## Creator workflow (authoring)
1. **Script with variables:**
   ```
   INT. CASTLE YARD – DUSK
   HERO (to camera): "[VAR_NAME], we have to get to [VAR_LOCATION]!"
   ```
2. **Tag assets:** Dialog lines, 2D textures, signage, diegetic UI, wardrobe patches.
3. **Generate template:** Heavy model outputs video + *track data* (phoneme timings, masks, layers) with variable anchors.
4. **Publish:** Upload template bundle to CDN: `video.mp4` + `tracks.json` + `vars.jsonschema`.

---

## Viewer personalization pipeline
1. **Context fetch:** Local profile → `{ name, locale, team, pet, hobby }` under explicit consent.
2. **Resolver:** Map vars to values via priority (user input > on‑device profile > app defaults).
3. **Filler:** Apply micro‑edits:
   - **Speech:** TTS line synthesis → align via viseme track (no identity cloning).
   - **Text:** Replace on‑screen strings/signage.
   - **Texture:** Swap decals (jersey names, posters) using tracked masks.
   - **Audio:** Name insertions, SFX cues keyed to `[VAR_*]` events.
4. **Render:** On‑device compositor merges layers at playback; edge render if device weak.

---

## MVP & Prototyping Plan
A rapid prototype should aim to test emotional appeal, not engineering polish. 

### Phases
1. **Manual proof of concept:** Simple video + manual name overlays using CapCut or Premiere. Ask if viewers feel “seen.”
2. **Semi‑auto render:** Python + MoviePy + ElevenLabs TTS to fill in `[VAR_NAME]` placeholders.
3. **Edge personalization:** Browser overlay swapping text + audio with pre‑cached clips.
4. **Feedback loop:** Deploy small demo (Streamlit or static web) → let users input their names → survey: *“Did this feel made for you?”*

### Early validation metric
If >70% prefer the personalized clip and <20% describe it as “creepy,” proceed to automation.

---

## Conceptual summary
- Generative personalization works best when it mirrors real social dynamics — friends making something for each other.  
- Variable‑filled templates **scale the intimacy of friendship** while avoiding the creepiness of likeness modeling.
- This approach reframes generative video as *contextual mirroring* rather than *identity cloning* — which is both safer and emotionally truer.


---

## MVP implementation in this repo
- `templates/castle_run_template.json` captures the variable anchors, timing, and
display metadata for the hero clip described above.
- `scripts/personalize_video.py` acts as the viewer-side filler: it resolves
  `[VAR_*]` tokens, composites lightweight overlays locally, and exports a
  personalized `.mp4` plus captions.
- `outputs/` (git-ignored) is where demo renders land; use the CLI documented in
  `README.md` to try a name/location/team of your choice.
