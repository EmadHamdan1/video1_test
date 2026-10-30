import React from "react";
import { AbsoluteFill } from "remotion";
import { useGsapTimeline } from "@remotion/gsap";

export type CaseFileOverlayProps = {
  kicker: string;
  heading: string;
  note: string;
  accent: string;
};

/**
 * A transparent, restrained lower-third for documentary stills.
 * GSAP's timeline is driven by Remotion's frame clock, so every frame
 * is deterministic during scrubbing and export.
 */
export const CaseFileOverlay: React.FC<CaseFileOverlayProps> = ({
  kicker,
  heading,
  note,
  accent,
}) => {
  const scope = useGsapTimeline<HTMLDivElement>(({ timeline, selector }) => {
    timeline
      .fromTo(
        selector("[data-kicker]"),
        { opacity: 0, y: 16, letterSpacing: "0.34em" },
        {
          opacity: 1,
          y: 0,
          letterSpacing: "0.16em",
          duration: 0.55,
          ease: "power3.out",
        },
        0.12,
      )
      .fromTo(
        selector("[data-rule]"),
        { scaleX: 0, transformOrigin: "left center" },
        { scaleX: 1, duration: 0.72, ease: "power3.inOut" },
        0.32,
      )
      .fromTo(
        selector("[data-heading]"),
        { opacity: 0, y: 42, filter: "blur(8px)" },
        {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.78,
          ease: "power4.out",
        },
        0.46,
      )
      .fromTo(
        selector("[data-note]"),
        { opacity: 0, x: -12 },
        { opacity: 1, x: 0, duration: 0.46, ease: "power2.out" },
        1.02,
      )
      .to(
        selector("[data-overlay-group]"),
        { opacity: 0, y: -10, duration: 0.38, ease: "power2.in" },
        4.0,
      );
  });

  return (
    <AbsoluteFill
      ref={scope}
      style={{
        background: "transparent",
        overflow: "hidden",
        color: "#FFFFFF",
        fontFamily: "Arial, Helvetica, sans-serif",
      }}
    >
      <div
        data-overlay-group
        style={{
          position: "absolute",
          left: 104,
          bottom: 92,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 15,
          width: 1120,
          maxWidth: "calc(100% - 208px)",
          padding: "25px 34px 27px 34px",
          boxSizing: "border-box",
          borderLeft: `4px solid ${accent}`,
          background:
            "linear-gradient(90deg, rgba(8, 13, 18, 0.82) 0%, rgba(8, 13, 18, 0.58) 72%, rgba(8, 13, 18, 0) 100%)",
        }}
      >
        <div
          data-kicker
          style={{
            color: "#E8E9E7",
            fontSize: 19,
            fontWeight: 700,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
          }}
        >
          {kicker}
        </div>
        <div
          data-rule
          style={{
            width: 142,
            height: 4,
            borderRadius: 2,
            background: accent,
            transformOrigin: "left center",
          }}
        />
        <h1
          data-heading
          style={{
            margin: 0,
            color: "#FFFFFF",
            fontSize: 76,
            lineHeight: 0.98,
            fontWeight: 900,
            letterSpacing: "-0.045em",
            textTransform: "uppercase",
            textShadow: "0 4px 24px rgba(0,0,0,0.48)",
          }}
        >
          {heading}
        </h1>
        <div
          data-note
          style={{
            color: "#D0D4D6",
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
