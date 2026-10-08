# How we make videos together

This is the process the user liked on the 30 s French promo (`video/promo-fr/`, 2026-10-08). Reuse the **process**: the questions, the order and the review stops. The **look** (colours, motifs, type, motion) is decided fresh for each video from its content, audience and inspiration. The promo's light violet "Antigravity" look is one example, not a default.

## Ground rules
- Build it **together**: ask **one question per message**. Give 2–4 options (A/B/C), recommend one, and say why in one sentence.
- Write all on-screen copy in the requested language. Keep it short and client-facing.
- Every fact or number comes from the product or a cited source. Never invent statistics.
- In example screens, use neutral demo data (e.g. `exemple.fr`), never a real client.
- Product copy says "the AI agent" / "agent IA", never a model name.

## 0. Before the first question
If there's an inspiration video:
1. Download it into the session scratchpad and make a contact sheet (`ffmpeg … fps=1/2.5,tile=4x5`).
2. Show a **beat table**: time, beat, technique.
3. State the **core idea** to keep, usually the pacing and structure.
4. State the assumptions the user can correct: duration, language, look, audience.

## 1. The questions (adapt them to each video)
This is **not a fixed script**. The questions themselves depend on the video:
- Skip what the user already answered or what the brief makes obvious.
- Add questions the content needs (e.g. a tutorial needs "which steps?", an event teaser needs "date and venue?", a data story needs "which numbers and sources?").
- Reorder them when the story calls for it.

What stays the same: one question at a time, options with a recommendation, and getting the purpose, audience and format clear before any visuals.

The promo used this sequence, as one example:
1. **Where will it be watched?** This sets the format: 16:9 for a meeting or call, 9:16 for LinkedIn or a phone, or both.
2. **The hook: which problem?** Propose 3 real business problems, each with a hook line, a payoff line and why it fits this audience. Recommend one.
3. **The proof beats.** Map the inspiration's structure onto the product. Show a table: time, headline, what's on screen. Offer to drop or merge beats.
4. **Extra beats the user adds** (e.g. the solution statement, a call to action, a call with an expert). Retime the whole table so it still fits the duration.
5. **People on screen.**
   - A real person needs their consent, the photo file and a role/title. Crop to **head and shoulders**, not just the face.
   - Otherwise use initials only, or no card at all.
6. **The payoff and end-card headline.** Give 3 options with the reasoning behind each.
7. **Sound.**
   - Music bed plus soft UI ticks, no voiceover (works muted). This is the usual pick.
   - Music plus a voiceover.
   - Silent, for playing live in a meeting.
8. **How to build the screens.**
   - Rebuild them as HTML from real assets. This is the usual pick: sharp, and every part can be animated.
   - Use screenshots.
   - Use a screen recording.
9. **Design §1: look and motion.** Derive this from the content, the brand, the inspiration and any reference frames the user sends. It covers:
   - palette and type
   - one or two signature motifs that come from the story itself
   - how text and screens enter and exit
   - pacing

   Get approval before moving on.
10. **Design §2: build and review.**
    - the project folder
    - the real assets reused, and where each comes from
    - the copy rules
    - audio
    - the review loop
    - what's out of scope
    - what stays git-ignored

    Get approval.

## 2. Spec, plan, build
- Write the spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit it. The user reviews it.
- Write a lean plan in `docs/superpowers/plans/`. Then execute task by task, test-first.
- Build with HyperFrames:
  - one sub-composition per beat
  - shared tokens
  - seek-safe animation (seeded randomness, no wall-clock time)
  - vendored libraries and fonts
- `video/promo-fr/` is a working reference for the project structure and its tests.

## 3. Review stops (always pause here)
1. **Storyboard:** one frame per beat, put together as a contact sheet.
2. **Music:** the user supplies a track or picks from candidates. **Check the licence first.** Ad soundtracks or "free" YouTube uploads are usually not cleared. Personal-use tracks stay git-ignored and are marked in `CREDITS.md` as not for client use.
3. **Draft preview:** a low-res MP4. Open it for the user and tell them the exact file path.
4. **Final render.** Verify:
   - the duration and resolution
   - no black frames
   - audio levels
   - a contact sheet of the result

## 4. Hand-off
- Tell the user the full local path of the MP4.
- Personal photos, test music and renders are git-ignored. Remind the user to copy them by hand to other machines.
- Commit only the files you changed. Push when the user wants to work on another laptop.
