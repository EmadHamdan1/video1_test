import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const NuttyPuttyTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleSpring = spring({
    frame: Math.max(0, frame - 5),
    fps,
    config: { damping: 13, stiffness: 180, mass: 0.7 },
  });
  const caveProgress = interpolate(frame, [1, 36], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const dateProgress = interpolate(frame, [17, 29], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pulse = 1 + 0.018 * Math.sin((frame / fps) * Math.PI * 2 * 0.65);
  const caveDash = 1000 * (1 - caveProgress);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#FFFFFF",
        color: "#15191E",
        overflow: "hidden",
        fontFamily: "Arial, Helvetica, sans-serif",
      }}
    >
      <AbsoluteFill style={{ opacity: 0 }}>
        <svg width="100%" height="100%" viewBox="0 0 1920 1080">
          <path d="M0 760 C220 690 355 770 520 710 S820 715 970 780 L970 1080 L0 1080 Z" fill="#D9D2C6" />
          <path d="M1920 695 C1710 650 1600 755 1450 710 S1220 750 1080 820 L1080 1080 L1920 1080 Z" fill="#D9D2C6" />
          <path d="M0 0 H1920 V1080 H0 Z" fill="none" stroke="#C9C1B3" strokeWidth="3" />
        </svg>
      </AbsoluteFill>

      <svg
        width="100%"
        height="100%"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0 }}
      >
        <path
          d="M0 905 C155 890 200 820 290 830 C410 845 435 955 545 925 C660 895 650 760 760 730 C855 705 930 780 1000 735 C1090 675 1040 570 1145 535 C1250 500 1335 605 1405 555 C1480 500 1475 400 1575 395 C1690 390 1740 480 1920 438 L1920 1080 L0 1080 Z"
          fill="#FFFFFF"
          stroke="#15191E"
          strokeWidth="8"
          transform="translate(0 36)"
          opacity={0.97}
        />
        <path
          d="M0 905 C155 890 200 820 290 830 C410 845 435 955 545 925 C660 895 650 760 760 730 C855 705 930 780 1000 735 C1090 675 1040 570 1145 535 C1250 500 1335 605 1405 555 C1480 500 1475 400 1575 395 C1690 390 1740 480 1920 438"
          fill="none"
          stroke="#15191E"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray="1000"
          strokeDashoffset={caveDash}
          opacity={0.8}
        />
        <path
          d="M1445 554 C1510 500 1505 432 1578 428 C1630 425 1675 450 1705 472"
          fill="none"
          stroke="#F04444"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray="210"
          strokeDashoffset={210 * (1 - caveProgress)}
        />
        <circle
          cx="1580"
          cy="428"
          r={24 * caveProgress}
          fill="#F04444"
          stroke="#F7F3EA"
          strokeWidth="5"
        />
        <circle cx="1580" cy="428" r={8 * caveProgress} fill="#F7F3EA" />
      </svg>

      <div
        style={{
          position: "absolute",
          top: 112,
          left: 130,
          width: 290,
          height: 12,
          borderRadius: 8,
          background: "#F04444",
          transform: "scaleX(" + caveProgress + ")",
          transformOrigin: "left center",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 135,
          left: 130,
          color: "#555D66",
          fontSize: 25,
          fontWeight: 800,
          letterSpacing: 5,
          opacity: dateProgress,
        }}
      >
        TRUE CAVE RESCUE STORY
      </div>

      <div
        style={{
          position: "absolute",
          left: 120,
          top: 290,
          width: 1180,
          transform: "scale(" + (0.84 + titleSpring * 0.16) + ")",
          transformOrigin: "left center",
        }}
      >
        <div
          style={{
            fontSize: 126,
            lineHeight: 0.93,
            fontWeight: 900,
            letterSpacing: -5,
            color: "#15191E",
            textTransform: "uppercase",
          }}
        >
          NUTTY PUTTY
        </div>
        <div
          style={{
            marginTop: 18,
            fontSize: 148,
            lineHeight: 0.94,
            fontWeight: 900,
            letterSpacing: 3,
            color: "#F04444",
            textTransform: "uppercase",
          }}
        >
          CAVE
        </div>
        <div
          style={{
            marginTop: 34,
            display: "inline-flex",
            alignItems: "center",
            padding: "14px 24px",
            borderRadius: 10,
            background: "#F6CF45",
            border: "4px solid #15191E",
            color: "#15191E",
            fontSize: 30,
            fontWeight: 900,
            transform: "scale(" + dateProgress + ")",
            transformOrigin: "left center",
          }}
        >
          NOVEMBER 24, 2009
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          right: 142,
          top: 124,
          width: 116,
          height: 116,
          border: "7px solid #15191E",
          borderRadius: "50%",
          background: "#F6CF45",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 76,
          fontWeight: 900,
          transform: "scale(" + (titleSpring * pulse) + ")",
          transformOrigin: "center",
        }}
      >
        !
      </div>
    </AbsoluteFill>
  );
};
