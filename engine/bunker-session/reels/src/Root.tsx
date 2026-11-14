import React from "react";
import { Composition, staticFile } from "remotion";
import { Reel, outroOf } from "./Reel";
import { loadSession } from "./data";
import { Gfx, GfxProps } from "./Gfx";
import { Fx, FxProps } from "./Fx";
import { Lux, LuxP } from "./lux";
import { NameGlass, NameGlassP } from "./NameGlass";

// Fixed composition ids r1…r12; each one finds its plan in the session's plans.json (publicDir = <session>/רילס/remotion/public).
const IDS = Array.from({ length: 20 }, (_, i) => `r${i + 1}`);

export const Root: React.FC = () => (
  <>
    {IDS.map((id) => (
      <Composition key={id} id={id} component={Reel} defaultProps={{ id, music: true }} fps={30} width={1080} height={1920} durationInFrames={1}
        calculateMetadata={async () => {
          const { plans } = await loadSession();
          if (!plans[id]) return { durationInFrames: 1 };
          const cut = await fetch(staticFile(plans[id].file)).then((r) => r.json());
          return { durationInFrames: Math.ceil((cut.duration + outroOf(plans)) * 30) };
        }} />
    ))}
    <Composition id="Gfx" component={Gfx as React.FC<any>} defaultProps={{ kind: "pill", text: "", dur: 2 } as GfxProps} fps={30} width={1080} height={1920}
      durationInFrames={60} calculateMetadata={async ({ props }) => ({ durationInFrames: Math.ceil((props as GfxProps).dur * 30) })} />
    <Composition id="Fx" component={Fx as React.FC<any>} defaultProps={{ kind: "bignum", w: 1920, h: 1080, dur: 2, x: 0.5, y: 0.5, s: 400, text: "1" } as FxProps}
      fps={30} width={1920} height={1080} durationInFrames={60}
      calculateMetadata={async ({ props }) => { const p = props as FxProps; return { width: p.w, height: p.h, durationInFrames: Math.ceil(p.dur * 30) }; }} />
    <Composition id="Lux" component={Lux as React.FC<any>} defaultProps={{ kind: "containers", from: 0, to: 3, count: 2, label: "2 קונטיינרים", sub: "0 נמכרו" } as LuxP}
      fps={30} width={1080} height={1920} durationInFrames={90}
      calculateMetadata={async ({ props }) => ({ durationInFrames: Math.ceil(((props as LuxP).to + 0.1) * 30) })} />
    <Composition id="NameGlass" component={NameGlass as React.FC<any>} defaultProps={{ name: "אלון גבאי", dur: 5.5 } as NameGlassP}
      fps={30} width={1920} height={1080} durationInFrames={165}
      calculateMetadata={async ({ props }) => ({ durationInFrames: Math.ceil((props as NameGlassP).dur * 30) })} />
  </>
);
