import React from "react";
import { Composition } from "remotion";
import { WhiteboardExplainer, type WhiteboardProps } from "./WhiteboardExplainer";
import { KineticCaption, type CaptionProps } from "./KineticCaption";
import { TransitionShowcase } from "./TransitionShowcase";
import { NuttyPuttyTitle } from "./NuttyPuttyTitle";

export const Root: React.FC = () => (
  <>
    <Composition<any, WhiteboardProps>
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
    <Composition<any, CaptionProps>
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
    <Composition
      id="NuttyPuttyTitle"
      component={NuttyPuttyTitle}
      // Keep the rendered source longer than the ~2.14s intro segment and overlap tail.
      // This prevents CapCut CLI from reading past the end of the rendered title media.
      durationInFrames={75}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
