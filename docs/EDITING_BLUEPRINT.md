# Editing blueprint — Whiteboard Explainer PRO

## Visual direction

Use a whiteboard explainer / motion-graphics hybrid: a quiet paper canvas, one framed scene illustration on the left, and the presenter character on the right. The goal is not maximum motion on every frame; it is a clear visual hierarchy where the character explains and the illustration supports the point.

The builder generates the paper, scene frames, shadows, small accent marks, and presenter backplates locally under `build/visuals`. They are normal media assets in the editable CapCut project. The source images and narration remain local and are never uploaded to this repository.

## Composition and timing

- The main illustration is reduced to roughly half-frame scale and held inside a framed card, leaving open space for the presenter. The frame and illustration are separate editable layers.
- The presenter track covers the narration with the supplied pose photos changing at a slower cadence than the scene images. This makes the presenter a constant guide instead of a sporadic pop-in.
- The image list is still distributed in configured order. Without local Whisper timing, scene boundaries are evenly spaced from duration. With Whisper, subtitle ends can be used as candidate boundaries.
- The system cannot inspect local image semantics or infer what each illustration depicts from filenames. The editor must review `build/scene_timing.csv` and adjust image order/timing where a scene conflicts with the spoken phrase.

## Motion language

- Scene illustrations alternate between a restrained scale-in and scale-out, with a small position drift. The keyframes start without easing and their paired endpoint carries `ease-in-out`, avoiding a warning on a lone eased keyframe.
- The character gets a light scale pulse and a tiny vertical float during each pose interval, then a short dissolve to the next pose.
- Cuts use short dissolves by default. Occasional `horizontal-blur` and `radial-blur` transitions mark selected changes; stronger transition presets should not be used on every shot.
- The opening scene uses a short zoom-out reveal. The presenter fades in at the opening and fades out at the end.
- CapCut documents the workflow for keyframing Position, Scale, Rotation, and Opacity here: https://www.capcut.com/resource/how-to-add-keyframes-in-capcut
- Easing is meaningful because it controls acceleration and deceleration; use the curve to guide attention rather than adding motion for its own sake: https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing
- Motion staging and hierarchy are more important than decorative movement: https://www.ibm.com/design/language/animation/classic-principles/

## Presenter limitations

The script asks capcut-cli to apply smart matting to each JPEG presenter image. JPEG has no alpha channel, so success depends on CapCut's matting result and image background. A remaining rectangular background must be corrected using CapCut's Remove background/Cutout controls or replaced by a clean transparent PNG. Still pose images cannot animate lip movement or actual arm articulation; the current effect is timed pose changes and gentle whole-image motion.

## Audio, captions, and effects

- Narration remains on its own editable track and receives a short lead/tail fade.
- Visual transition and keyframe effects are built into the project. Audio effects are not invented or inserted from CapCut's private library.
- `build/SFX_Cue_Sheet.csv` lists candidate time/search terms for a few restrained whooshes or cartoon pops. Add only effects that fit the spoken beat, and keep them below the voice.
- Local Whisper is optional. Without it, automatic subtitles are not present and timing remains duration-based. The build reports that limitation instead of claiming captions were created.

## Quality pass

1. Open the **Whiteboard Explainer PRO** draft in CapCut.
2. Review the first 10 seconds, the first presenter pose change, the midpoint, and the ending.
3. Confirm that the presenter image background is removed, and that the scene image stays inside its card during movement.
4. Check that only occasional transitions use blur, and that most cuts remain quiet.
5. Compare `build/scene_timing.csv` with the narration and adjust scenes where semantic alignment is wrong.
6. Add only a few sound cues from CapCut's own library if they support the beat.
7. Export from CapCut and inspect the rendered MP4 end-to-end before publishing.

## References

- CapCut official: https://www.capcut.com/resource/how-to-add-keyframes-in-capcut
- Figma motion/easing: https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing
- IBM motion principles: https://www.ibm.com/design/language/animation/classic-principles/
- capcut-cli commands and editable project API: https://github.com/renezander030/capcut-cli
- capcut-cli keyframe example: https://github.com/renezander030/capcut-cli/blob/master/examples/keyframe-zoom.md
- YouTube audience retention: https://support.google.com/youtube/answer/9314415
