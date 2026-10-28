import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { linearTiming, springTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

const PaletteScene: React.FC<{ title: string; subtitle: string; background: string; accent: string }> = ({ title, subtitle, background, accent }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 75], [0.97, 1.025], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background, justifyContent: "center", alignItems: "center", fontFamily: "Arial, Helvetica, sans-serif" }}>
      <div style={{ position: "absolute", inset: 40, border: "2px solid rgba(255,255,255,.26)", borderRadius: 32 }} />
      <div style={{ width: 1150, textAlign: "center", transform: `scale(${scale})` }}>
        <div style={{ display: "inline-block", padding: "13px 23px", borderRadius: 999, background: accent, color: "#fff", fontSize: 19, fontWeight: 800, letterSpacing: 2 }}>{subtitle}</div>
        <h1 style={{ color: "#fff", fontSize: 87, lineHeight: 1.04, margin: "34px 0", letterSpacing: -2 }}>{title}</h1>
        <div style={{ height: 7, width: 220, borderRadius: 10, background: accent, margin: "0 auto" }} />
      </div>
    </AbsoluteFill>
  );
};

export const TransitionShowcase: React.FC = () => (
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={75}>
      <PaletteScene title="One idea at a time" subtitle="WHITEBOARD" background="#132A35" accent="#159A90" />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 15 })} />
    <TransitionSeries.Sequence durationInFrames={75}>
      <PaletteScene title="Let the visual explain" subtitle="MOTION GRAPHICS" background="#24354B" accent="#E99A49" />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={springTiming({ config: { damping: 200 } })} />
    <TransitionSeries.Sequence durationInFrames={75}>
      <PaletteScene title="Keep it smooth" subtitle="FINAL BEAT" background="#2F3644" accent="#D85D78" />
    </TransitionSeries.Sequence>
  </TransitionSeries>
);
