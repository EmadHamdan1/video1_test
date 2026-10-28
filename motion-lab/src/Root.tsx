import React from "react";
import { Composition } from "remotion";
import { WhiteboardExplainer, type WhiteboardProps } from "./WhiteboardExplainer";
import { KineticCaption, type CaptionProps } from "./KineticCaption";
import { TransitionShowcase } from "./TransitionShowcase";

export const Root: React.FC = () => (
  <>
    <Composition<WhiteboardProps>
      id="WhiteboardExplainer"
      component={WhiteboardExplainer}
      durationInFrames={180}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{
        title: "One clear idea at a time",
        subtitle: "Visuals support the explanation",
        imageUrl: "",
        accent: "#159A90",
        sceneNumber: "01",
      }}
    />
    <Composition<CaptionProps>
      id="KineticCaption"
      component={KineticCaption}
      durationInFrames={90}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{
        text: "The detail that changes everything",
        accent: "#15A89C",
        mode: "phrase",
      }}
    />
    <Composition
      id="TransitionShowcase"
      component={TransitionShowcase}
      durationInFrames={195}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
