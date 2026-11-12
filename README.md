# islamic-ig-automation

Free, cloud-run Instagram posting for **@ruh_corner** (Ruh Corner: daily dhikr, duas and Quran reminders).
Runs on GitHub Actions; your laptop is not needed.

## What it posts (IST)
| Time | Format | Content |
|---|---|---|
| 08:00 | Reel | Story reel: real-life scene, own theme/characters per story, calm English male voice-over; ends with a verbatim hadith/verse |
| 19:30 | Reel | Tasbih beads falling into three jars (11 each, repeat 3 rounds = 33), calm natural sounds only (no voice) |

Backup runs 2 hours later skip automatically if the post already went out. Edit `data/config.json` -> `slots` to change times or content.

## Accuracy: no AI-written religious text
* Quran Arabic (Uthmani) and English (Saheeh International) are copied verbatim from the open dataset
  `fawazahmed0/quran-api` into `data/quran.json` (`python tools/build_data.py` rebuilds it).
* Hadith (Sahih al-Bukhari and Forty Hadith of an-Nawawi) come from the same author's `hadith-api` into `data/hadith.json`.
* Dhikr phrases are in `data/dhikr.json`. Every caption shows the source reference.
* **Story reels** (`data/stories.json`): the short story lines are original reflections; the closing verse/hadith is always verbatim from the data (the build fails if an excerpt is not an exact part of the source).
* Sound: Quran recitation by Mishary Rashid Alafasy via the Islamic Network CDN (credited on screen and in the caption); dhikr phrases use the free Microsoft neural Arabic voice (edge-tts) reading fully vowelled text. If either service is unreachable the Reel is still made with natural sounds only. No music is ever added.
* To add verses, hadith or stories, edit `tools/build_data.py` / `data/stories.json`. The pool rotates; an item repeats only after all others were used.

## Try without posting
Actions -> **Post to Instagram (Ruh Corner)** -> Run workflow -> keep **dry_run** ticked. Download the **generated-post** artifact to see the Reel/images and caption.
Untick dry_run to publish for real.

## Secret
`IG_ACCESS_TOKEN` only (Settings -> Secrets and variables -> Actions). The Instagram account ID is in `data/config.json`.

## If the token stops working
You get a GitHub issue (email). Meta dashboard -> your app -> Use cases -> Customize -> API setup with Unified login -> **Generate token** for ruh_corner,
then replace the `IG_ACCESS_TOKEN` secret.

## Notes
* Fonts: Amiri Quran and Amiri (SIL OFL), Poppins and Lora (OFL).
* Tests: `python tests/test_content.py`, `python tests/test_publish.py`.
