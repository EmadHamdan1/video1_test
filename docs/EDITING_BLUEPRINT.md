# Editing blueprint

## Goal

Keep the narration as the spine of the edit and make the visuals support the spoken idea rather than compete with it. The first generated pass is deliberately conservative: the footage is still images, so visual interest comes from framing, pacing, cut timing, presenter appearances, readable captions, and a few deliberate sound accents.

## Timing and image choice

- If Whisper is installed, the builder uses its subtitle boundaries as candidate edit points near the target shot intervals. Without Whisper, boundaries are paced from the MP3 duration.
- The images are distributed across the narration in the supplied order. This version does not inspect image pixels with a vision model; matching an image to the exact sentence is a review task, and the CSV shows the cue text for each shot when available.
- Avoid assuming that every available image must appear. When the voiceover is short, fewer readable shots are preferable to flickering through dozens of images too quickly.
- Inspect the first 30 seconds carefully. YouTube's audience-retention guidance says the intro should fulfil the expectation created by the title and thumbnail, and recommends studying top moments, spikes, and dips once analytics are available: https://support.google.com/youtube/answer/9314415

## Motion

- Scene images receive a slow, low-amplitude zoom and a small alternating horizontal drift. This is a Ken Burns treatment for still images; it should not look like every photo is being aggressively pushed into the viewer's face.
- The smooth easing is intentional: CapCut explains that keyframes control values such as position, scale, rotation, opacity, and color, and that easing or speed curves can make movement feel more natural: https://www.capcut.com/resource/how-to-add-keyframes-in-capcut
- The movement values are starting points, not a universal formula. Review in the actual desktop build and reduce the scale delta if the original images already contain close framing.
- Use transitions sparingly. The current build uses a short Mix transition as a neutral default. A horror-comedy moment may benefit from a brief flash or hit, but those should be placed manually only where the narration earns the emphasis.

## Presenter overlay

The presenter stills are on their own video track, alternate left/right, and appear in short intervals. The script attempts the capcut-cli smart-matting command on each presenter segment. These supplied files are JPEGs, so background removal is not guaranteed; check the first cutout and correct its scale or position in CapCut before rendering. If the backgrounds remain visible, use CapCut's manual Cutout / Remove background controls or supply transparent PNGs.

## Audio and sound effects

- The narration stays on a dedicated audio track and gets a very short fade-in and a short tail fade.
- Local effect audio can be added through the sound_effects array in config.json. If no local effects were supplied, the program does not pretend that it inserted CapCut's private sound-library assets.
- The generated SFX_Cue_Sheet.csv lists suggested search terms and times. Use only a few: a soft whoosh for an important visual transition, a restrained low hit for a real reveal, and a light pop for a genuinely comic beat. Keep these lower than the speech and listen on headphones and speakers.
- Avoid adding a sound to every cut; repetitive whooshes quickly become tiring and can obscure words.

## Quality pass

1. Open the draft and check the beginning, the first presenter overlay, the midpoint, and the ending.
2. Compare the narration with build/scene_timing.csv. Move any image whose meaning conflicts with the words being spoken.
3. Confirm the presenter cutout doesn't cover key action or any captions.
4. Listen to the voiceover with the optional sound effects enabled. Remove anything that masks consonants or makes the mix harsh.
5. Export from CapCut, watch the exported file all the way through, then use audience-retention analytics to inform the next edit.

## Tool reference

- capcut-cli is a community-made project, not an official CapCut product. It supports local draft creation, keyframes, transitions, audio fades, captions, and other edits: https://github.com/renezander030/capcut-cli
- Its Ken Burns example discusses restrained zoom in/out values and warns against using visible zoom moves on very short shots: https://github.com/renezander030/capcut-cli/blob/master/examples/keyframe-zoom.md
