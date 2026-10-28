import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type CaptionProps = { text: string; accent: string; mode: "phrase" | "punch" | "lower-third" };

export const KineticCaption: React.FC<CaptionProps> = ({ text, accent, mode }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const words = text.trim().split(/\\s+/).filter(Boolean);
  const allOpacity = interpolate(frame, [0, 7, durationInFrames - 8, durationInFrames - 1], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad),
  });
  const isLowerThird = mode === "lower-third";
  const fontSize = mode === "punch" ? 57 : isLowerThird ? 39 : 47;
  const positionY = interpolate(frame, [0, 12], [32, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });

  return (
    <AbsoluteFill style={{ background: "transparent", justifyContent: "flex-end", alignItems: isLowerThird ? "flex-start" : "center", padding: isLowerThird ? "0 0 105px 125px" : "0 150px 88px", boxSizing: "border-box", opacity: allOpacity, fontFamily: "Arial, Helvetica, sans-serif" }}>
      <div style={{ maxWidth: 1500, background: "rgba(23,33,43,0.92)", borderRadius: mode === "punch" ? 18 : 22, padding: mode === "punch" ? "22px 38px" : "18px 33px", boxShadow: "0 12px 38px rgba(0,0,0,0.20)", transform: `translateY(${positionY}px)`, borderLeft: `7px solid ${accent}` }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: isLowerThird ? "flex-start" : "center", gap: "0.23em", color: "#FFFFFF", fontWeight: 800, fontSize, lineHeight: 1.15, letterSpacing: mode === "punch" ? -1.5 : -0.6 }}>
          {words.map((word, index) => {
            const localFrame = frame - (mode === "punch" ? index * 2 : index * 1.5);
            const reveal = spring({ frame: Math.max(0, localFrame), fps, config: { damping: 17, stiffness: 145, mass: 0.65 } });
            const wordOpacity = interpolate(localFrame, [0, 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return <span key={index} style={{ opacity: wordOpacity, transform: `translateY(${interpolate(reveal, [0, 1], [14, 0])}px) scale(${interpolate(reveal, [0, 1], [0.94, 1])})`, transformOrigin: "bottom center", color: mode === "punch" && index === words.length - 1 ? accent : "#FFFFFF" }}>{word}</span>;
          })}
        </div>
        <div style={{ height: 4, width: interpolate(frame, [6, 24], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) + "%", background: accent, borderRadius: 6, marginTop: 15 }} />
      </div>
    </AbsoluteFill>
  );
};
