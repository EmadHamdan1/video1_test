import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type WhiteboardProps = {
  title: string;
  subtitle: string;
  imageUrl: string;
  accent: string;
  sceneNumber: string;
};

export const WhiteboardExplainer: React.FC<WhiteboardProps> = ({ title, subtitle, imageUrl, accent, sceneNumber }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const entrance = spring({ frame, fps, config: { damping: 22, stiffness: 115, mass: 0.8 } });
  const opacity = interpolate(frame, [0, 8, durationInFrames - 8, durationInFrames - 1], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad),
  });
  const cardScale = interpolate(frame, [0, 20, durationInFrames - 18, durationInFrames - 1], [0.92, 1, 1.025, 1.01], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad),
  });
  const driftY = interpolate(frame, [0, durationInFrames - 1], [10, -7], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad),
  });
  const titleOpacity = interpolate(frame, [5, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#FAF9F5",
        opacity,
        fontFamily: "Arial, Helvetica, sans-serif",
        overflow: "hidden"
      }}
    >
      <AbsoluteFill style={{ opacity: 0.45, backgroundImage: "radial-gradient(#DCD9D0 1.15px, transparent 1.15px)", backgroundSize: "28px 28px" }} />
      <div style={{ position: "absolute", left: 76, top: 62, padding: "14px 23px", borderRadius: 20, background: "#FFFFFF", border: "1px solid #E6E2D8", color: "#36414C", fontSize: 21, fontWeight: 800, letterSpacing: 2 }}>VISUAL EXPLAINER</div>
      <div style={{ position: "absolute", right: 80, top: 73, color: "#8B8D8A", fontSize: 17, letterSpacing: 2 }}>WHITEBOARD / MOTION</div>
      <div style={{ position: "absolute", left: 78, top: 138, width: 155, height: 6, background: accent, borderRadius: 9 }} />
      <div style={{ position: "absolute", left: 245, top: 138, width: 45, height: 6, background: "#E99A49", borderRadius: 9 }} />

      <div style={{ position: "absolute", left: 145, top: 205, width: 1015, height: 690, opacity: entrance, transform: `translateY(${driftY}px) scale(${cardScale})`, transformOrigin: "center center" }}>
        <div style={{ position: "absolute", inset: "12px -2px -12px 14px", borderRadius: 32, background: "rgba(35,42,52,0.14)", filter: "blur(20px)" }} />
        <div style={{ position: "absolute", inset: 0, borderRadius: 28, border: "3px solid #DEDAD0", background: "#FFFEFB", boxSizing: "border-box", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 34, top: 29, width: 128, height: 8, borderRadius: 10, background: accent }} />
          <div style={{ position: "absolute", right: 24, top: 19, background: accent + "18", border: `1px solid ${accent}55`, color: accent, borderRadius: 14, padding: "11px 17px", fontSize: 17, fontWeight: 800 }}>{sceneNumber}</div>
          {imageUrl ? (
            <img src={imageUrl} alt="" style={{ position: "absolute", left: 30, top: 78, width: 949, height: 505, objectFit: "contain" }} />
          ) : (
            <div style={{ position: "absolute", left: 30, top: 78, width: 949, height: 505, background: "linear-gradient(135deg, #E7F4F0 0%, #F6F1E8 55%, #E9ECF8 100%)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ width: 330, height: 250, borderRadius: "50% 50% 44% 44%", background: accent + "28", border: `7px solid ${accent}88`, display: "flex", alignItems: "center", justifyContent: "center", color: accent, fontSize: 30, fontWeight: 800 }}>SCENE ART</div>
            </div>
          )}
          <div style={{ position: "absolute", bottom: 30, left: 38, right: 38, display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ width: 8, height: 55, borderRadius: 9, background: accent }} />
            <div style={{ color: "#27333E", fontSize: 29, fontWeight: 800, lineHeight: 1.16 }}>{title}</div>
          </div>
        </div>
      </div>

      <div style={{ position: "absolute", right: 92, top: 208, width: 500, height: 650, transform: `translateY(${interpolate(frame, [0, durationInFrames - 1], [16, -9])}px)`, opacity: titleOpacity }}>
        <div style={{ position: "absolute", inset: "18px 4px -12px 18px", borderRadius: 220, background: accent + "18", border: `3px solid ${accent}55` }} />
        <div style={{ position: "absolute", top: 130, left: -12, width: 35, height: 35, background: "#E99A49", borderRadius: "50%", boxShadow: "0 5px 0 #C77B2D" }} />
        <div style={{ position: "absolute", top: 210, left: 26, width: 15, height: 85, background: accent, borderRadius: 20, transform: "rotate(-12deg)" }} />
        <div style={{ position: "absolute", bottom: 42, right: 4, padding: "17px 24px", borderRadius: 18, background: "#FFFFFF", border: "1px solid #DADFD8", color: "#48545C", fontSize: 19, fontWeight: 700, boxShadow: "0 8px 28px rgba(20,40,50,.08)" }}>{subtitle}</div>
      </div>
    </AbsoluteFill>
  );
};
