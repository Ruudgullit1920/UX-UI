# Video style: "Light Antigravity" product film

The house style for short product videos, first used in `video/promo-fr/` (30 s, FR, 2026-10-08).
Reuse the style, not the content: new script, new screens, new illustrations every time.

## Look
- **Light only:** white `#FFFFFF` / canvas `#F7F8FC` backgrounds, with no dark scenes and no fades to black.
- **Palette:** ink `#1F2430`, ink-2 `#3D4456`, muted `#5B6275`, line `#E4E7EF`, violet accent `#5B3FD9` (with soft `#EFEBFF`), and EY yellow `#FFE600` used sparingly for highlights only.
- **Type:** Inter, tight tracking (−0.035 to −0.05 em).
  - Headlines are 64–104 px, semibold.
  - One "giant word" moment per film: ≥ 220 px at weight 200, with a small bold subtitle under it that reveals letter by letter.
  - The key words of a headline are coloured violet.
- **Signature motifs:**
  - A **dot field**: concentric rings of small violet, grey and yellow dots around an empty centre, drifting slowly. It can react to the story (dots fall away, or gather into a logo).
  - A **light horizon arc**: a pale planet curve at the bottom of the frame, with a violet→yellow rim glow. It's used for brand moments (the solution and the end card).
- **UI screens:** clean HTML re-creations of the real product (white cards, 18–26 px radius, a soft shadow, a 1 px `#E4E7EF` border). They are never screen recordings.

## Motion
- Ease `cubic-bezier(.2,.8,.2,1)` (GSAP `power3.out`).
- **Text:** a staggered word reveal, blur-to-sharp (blur 14 px → 0, y +22 → 0, 0.07 s stagger).
- **Screens:** they rise in with a 3D tilt (rotationX 16–22°, y +120) and settle flat.
- **Exits:** a quick blur-zoom (scale 1.1–1.6, blur 8 px, 0.3 s).
- **Proof moments:**
  - findings draw in as yellow framed boxes, each with a label card
  - counters tick up to a number
  - chips orbit around a stat
  - a cursor clicks the call to action, with a press and a ripple
- **Pacing:** a new visual idea every 2–5 s, and every text beat stays on screen for at least 2 s.

## Structure (≈ 30 s, 16:9 1920×1080, 30 fps)
1. **Hook** (0–4.5 s): the client's pain in 2–3 short lines, over the dot field.
2. **Brand reveal** (2 s): the dots gather into the logo.
3. **Solution** (2.5 s): the giant word over the horizon arc.
4. **2–3 proof beats** (3–5 s each): the headline on the left, the live UI on the right.
5. **One stat beat** (3 s): a big thin number with orbiting chips.
6. **Human / next step** (≈ 6 s): a deliverable, then the expert card and the CTA click.
7. **Payoff + end card** (4 s): a two-line payoff, then the logo and tagline over the horizon.

## Sound
A music bed (licensed; ≤ 0.6 volume, fades, −16 LUFS), plus soft UI ticks on each proof moment. There's no voiceover, and the film must work muted.

## Copy rules
- Short, client-facing and factual. Every number comes from the product.
- Say "agent IA" / "AI agent", never a model name.
- In example screens, use neutral demo data (e.g. `exemple.fr`), never a real client.

## How it's built
HyperFrames (HTML + GSAP, a seekable timeline), with one sub-composition per beat, a shared `tokens.css`, and a seeded dot field. Copy `video/promo-fr/lib/` (`dotfield.js`, `reveal.js`, `horizon.css`) as the starting kit.
