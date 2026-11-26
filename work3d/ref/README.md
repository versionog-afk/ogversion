# Reference material (local only)

This folder holds the owner's original material. Only `print-closeup.jpg` and `mockup-sheet.jpg` are in git. Everything else here is ignored on purpose: the repository is public and the other files show a person.

Copy these files here on the working computer (the owner has them):

| file | what |
|---|---|
| `worn-back.jpg` | the shirt worn, from behind (source for the page photo `back`) |
| `worn-front.jpg` | the shirt worn, from the front, face cropped out (source for `front`) |
| `print-closeup.jpg` | close-up of the front lettering (already here) |
| `mockup-sheet.jpg` | the designer's flat mockup of both sides (already here) |
| `originals/na2.webp` | the front lettering artwork with a transparent background |
| `originals/map-black.png` | the back artwork, print-ready version 2 (29.7 × 35.4 cm page), rendered from `originals/pdf/map-black.pdf` at 300 ppi with `pdftocairo -png -r 300 -singlefile`; `art/make_textures.py` builds both textures from these two files |
| `originals/pdf/` | the owner's print-ready PDFs (front lettering, back map in white ink and in black ink) |
| `blank-*.png` | the supplier's pictures of the blank shirt, front and back, white and black: cut reference only, never published |
| `video.mov` | 9 s phone video of the person turning round; fit and drape reference |

Rules:

- The person is a fit reference only. Never reproduce her face or likeness without her consent, and never publish the video.
- Never commit raw photos or frames that show a person. The page uses tight crops written by the build to `merch/v/ph/`.
- The original print files are not committed either: the page ships only the reduced textures.
