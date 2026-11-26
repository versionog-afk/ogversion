# Cinematic intro: the owner's brief (verbatim, 2026-11-26)

Build and integrate the cinematic intro for our NA2 merch shop. A visitor opens the site above Lithuania at night, dives through clouds toward Kaunas, emerges above the rooftops of Šilainiai, descends into Naujakurių Street from our game, and lands in the live merch shop with the NA2 shirt ready to rotate and touch. Make the whole journey feel like one continuous camera move. Deliver a working local preview.

Start with the existing merch project. The previous work was on branch claude/friendly-cori-d4z8b5. Check its current state and read work3d/README.md, work3d/PLANAS.md, and work3d/spec/SPEC.md where available.

## REFERENCE FRAMES

The four original 1920×1080 Unreal screenshots are on this Mac:

/Users/macbookpro/Documents/Codex/2026-11-26/pa/outputs/NA2-Naujakuriu-referencijos/

The same files and camera notes are in this ZIP if you are working from an attachment:

/Users/macbookpro/Documents/Codex/2026-11-26/pa/outputs/NA2-Naujakuriu-referencijos.zip

Open the images before generating. They have different jobs:

01-n74-neighborhood-aerial.png — Establishes the apartment blocks around Naujakurių g. 74. Use it for the first recognizable view below the clouds. Its camera faces a different direction from 02, so conceal the change in heading while the frame is still inside the cloud.

02-naujakuriu-rooftop-approach.png — The main approach frame. The road runs into the distance, with a low pale building on the left and apartment blocks and parked cars on the right.

03-naujakuriu-street-level.png — The landing frame. It looks along the same street in almost exactly the same direction as 02. Use 02 → 03 for the most convincing part of the descent.

04-naujakuriu-street-alternate.png — An alternate curbside angle with a dark parked car close to the camera. Use this as a reference for the foreground wipe into the shop.

If you need another angle, the Unreal project is at /Users/macbookpro/Documents/og-games-unreal/OGGames.uproject. The selected frames came from /Game/Development/ClaudeLook/L_HQ_Lab. The camera positions for 02 and 03 are in READ-ME-FABLE.txt beside the images.

## PRODUCE THE INTRO IN HIGGSFIELD

Use the existing authenticated Higgsfield connection. The official generation skill and the cinematic prompt-writing skill are here:

https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/SKILL.md
https://github.com/Codebater/claude-film-skills/blob/main/seedance-prompt/SKILL.md

Render the descent in three pieces and join them into a roughly 12-second film. Choose an available image-to-video model that supports the references each shot needs. Check its current input schema. Where it supports first and last frames, use those controls for 02 → 03. For a night sequence, first relight both frames consistently in Higgsfield, keeping the architecture and framing intact. Use those matching night frames as the video inputs.

### SHOT 1 · 0–4 seconds · Satellite to cloud

Start from a satellite-style view over Lithuania at night with Kaunas correctly positioned. Use a verified geographic reference for the opening frame. Keep the landscape clean and free of map labels.

Higgsfield direction: “A high orbital view over Lithuania at blue hour. Kaunas glows faintly through the atmosphere. The camera locks onto the city and accelerates into a steep, controlled descent. City lights grow and separate beneath a broken cloud deck. A dense bank of blue-grey cloud races up until mist fills the entire frame. Carry the forward momentum through the last frame.”

### SHOT 2 · 4–7 seconds · Cloud to Šilainiai rooftops

Use 01 for the district layout and 02 for the outgoing camera direction. Begin inside the same cloud that ended Shot 1. Keep the ground hidden until the camera is aligned with Naujakurių Street.

Higgsfield direction: “Moving forward inside dense cloud. Wisps peel past the lens and the apartment blocks of Šilainiai emerge below. A few amber windows and streetlights show through the haze. The camera clears the roofline and settles onto the road axis in the supplied approach frame. Keep the pale low building to the left and the parked cars to the right. Let the last wisps drift across the gap between the buildings.”

### SHOT 3 · 7–11 seconds · Rooftops to street level

Animate the matched night versions of 02 and 03. Preserve the real street width, building positions, parked cars, and road markings.

Higgsfield direction: “Glide forward and descend from the supplied elevated view to pedestrian eye level on this exact street. The roof of the pale building slips out of view on the left. Parked cars grow larger on the right as the camera comes down beside them. Thin mist moves across the road. Warm streetlights skim damp asphalt beneath a deep blue sky. Ease out of the dive into a steady forward glide. Grounded 35 mm crime-film atmosphere, subtle grain, stable architecture, believable parallax.”

### SHOP TRANSITION · 11–12 seconds

Prepare the first live shop frame before finishing the edit. Bring a dark foreground edge close across the street camera, using the parked car in 04 as a guide. At maximum coverage, cut to a close-up of the black NA2 shirt in the live 3D scene. Carry the same screen direction and amber edge light across the cut. As the camera settles, reveal the print and enable product controls. Keep the shop interface and lettering live in the website so they stay sharp and usable.

Test the 02 → 03 street descent first. Watch for buildings changing shape, parked cars sliding, or the camera reversing. If the generator loses the street layout, capture that short move in Unreal using the recorded camera positions and retain the Higgsfield sky and cloud footage. Previous generation attempts from the connected free workspace were rejected with “Requires basic plan or higher.” Check the connection available in your session. If generation is still blocked, finish the timed edit and shop transition with the real reference frames as a clearly labelled animatic, and save the exact prompts for the pending shots.

## WEB DELIVERY

Play the intro muted and inline. Show “Praleisti intro” from the first frame. Load the shop during playback so the cut lands on a ready product. Finishing, skipping, blocked autoplay, video failure, and reduced-motion mode must all lead to the same usable shop. Check the framing on a phone, especially the street reveal and the NA2 print.

Deliver the local preview URL, the web-ready video and poster, and a screen recording showing the full path from satellite view to an actual interaction with the shirt. Save the prompts and reference filenames alongside the edit so we can revise one shot at a time. Keep the work on the development branch and wait for my review before publishing to ogversion.com.

## Added by the owner with the brief

Make the shirt material view ("inspect") show how the cheaper and the more expensive shirts differ, according to the textual information supplied (see `work3d/spec/OWNER-FACTS.md`).

## State of the inputs on 2026-11-26

- Reference frames 01 to 04 and READ-ME-FABLE.txt: on the owner's Mac only. Not available to the cloud session; to be copied into `work3d/intro/ref/` (local only).
- Generation service: the connected workspace is on the free plan with 5.25 credits. Quotes taken that day: the cheapest 4-second clip costs 8 credits (480p), a 4-second 1080p clip with first and last frame 10 credits, a 4-second 720p clip on the default model 28 credits. No clip can be generated until the plan or the credits change.
