// The marks, carried over from the ELLA OS site.
//
// The ELLA source files are the WHITE edition, drawn for a dark screen. On
// paper they would be invisible, so `brightness(0)` collapses every
// non-transparent pixel to solid black while keeping the alpha, giving a flat
// ink silhouette. The XiteAI mark ships as a real black edition with a proper
// alpha channel and must not be touched.
const ART = {
  mark: { src: "/logo/mark.png", w: 96, h: 102, invert: true, alt: "ELLA ZERO" },
  lockup: { src: "/logo/lockup.png", w: 256, h: 403, invert: true, alt: "ELLA ZERO" },
  xiteai: { src: "/logo/xiteai.png", w: 128, h: 143, invert: false, alt: "XiteAI Technologies" },
};

export default function Logo({ variant = "mark", size = 40, className = "" }) {
  const a = ART[variant];
  return (
    <img
      src={a.src}
      alt={a.alt}
      width={size}
      height={Math.round((size * a.h) / a.w)}
      className={className}
      style={a.invert ? { filter: "brightness(0)" } : undefined}
    />
  );
}
