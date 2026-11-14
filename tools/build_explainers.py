"""Builds data/explainers.json: topic explainers whose quotes are copied verbatim from the open datasets.

  python tools/build_explainers.py <quran-api-dir> <hadith-api-dir>
The short headings / spoken lines are original wording; every ayah and hadith quote is taken from the data
(Saheeh International for the Quran, Sahih al-Bukhari in English) and checked to be an exact substring.
"""
import json, os, sys

QURAN, HADITH = sys.argv[1], sys.argv[2]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "explainers.json")
en = {(v["chapter"], v["verse"]): v["text"].strip() for v in json.load(open(f"{QURAN}/editions/eng-ummmuhammad.json", encoding="utf-8"))["quran"]}
ar = {(v["chapter"], v["verse"]): v["text"].strip().replace("ی", "ي") for v in json.load(open(f"{QURAN}/editions/ara-quranuthmanienc.json", encoding="utf-8"))["quran"]}
bk = {h["hadithnumber"]: h["text"] for h in json.load(open(f"{HADITH}/editions/eng-bukhari.json", encoding="utf-8"))["hadiths"]}


def punct(t):
    t = t.strip()
    return t if t[-1] in '.?!"”' else t + "."


def ayah(ref, clip=None):
    s, v = ref.split(":")
    a, _, b = v.partition("-")
    ns = list(range(int(a), int(b or a) + 1))
    text = " ".join(punct(en[(int(s), n)]) for n in ns)
    arabic = " ".join(ar[(int(s), n)] for n in ns)
    if clip:                                   # a clause of the verse(s); Arabic omitted when clipped
        assert all(c in " ".join(en[(int(s), n)] for n in ns) for c in clip), clip
        text, arabic = " ".join(punct(c) for c in clip), ""
    return {"ref": f"Quran {ref}", "english": punct(text), "arabic": arabic if len(arabic) <= 190 else ""}


def hadith(num, clip):
    assert clip in bk[num], (num, clip)
    return {"ref": f"Sahih al-Bukhari {num}", "english": "“" + clip + "”", "arabic": ""}


def ch(label, heading, line, icon, tint, quote=None):
    return dict(label=label, heading=heading, line=line, icon=icon, tint=tint, quote=quote)


RIZQ = dict(id="rizq", theme="gold", title="Rizq, explained slowly", hook="Rizq is not just money", chapters=[
    ch("Rizq", "Rizq, explained slowly", "Let us talk about rizq.", "intro", "gold"),
    ch("What it is", "Rizq is not just money", "Health. Family. Peace of mind. Even your next breath.", "four", "rose"),
    ch("A promise", "Every creature is provided for", "Not one is left out.", "creature", "jade", ayah("11:6")),
    ch("Key one", "Ask forgiveness", "The first key. Turn back, and ask.", "rain", "violet", ayah("71:10-11")),
    ch("Key two", "Be grateful", "The second key. Say thank you, and mean it.", "lamp", "gold", ayah("14:7")),
    ch("Key three", "Stay mindful", "The third key. Stay mindful of Him.", "door", "jade", ayah("65:2-3", ["And whoever fears Allah - He will make for him a way out", "And will provide for him from where he does not expect."])),
    ch("Remember", "Do your part", "Do your part. Then let your heart rest.", "walk", "amber"),
])

SABR = dict(id="sabr", theme="plum", title="Sabr, explained slowly", hook="What patience really means", chapters=[
    ch("Sabr", "Sabr, explained slowly", "Everyone says, be patient. Few explain what it means.", "intro_s", "violet"),
    ch("What it is", "Not silence. Not giving up.", "It still hurts. Patience is staying steady anyway.", "four_s", "rose"),
    ch("You are not alone", "Help comes with patience", "While you wait, you are not waiting alone.", "ties", "gold", ayah("2:153")),
    ch("A test", "Tests are part of the road", "Hard days do not mean you were forgotten.", "rain", "jade", ayah("2:155")),
    ch("The first moment", "Real patience is early", "The first moment is where it counts.", "walk", "amber", hadith(1302, "The real patience is at the first stroke of a calamity")),
    ch("Ease", "Ease is promised", "And after the hardship, listen.", "beam", "gold", ayah("94:5-6")),
    ch("Remember", "Keep walking", "Take the next small step.", "walk", "violet"),
])
json.dump({"topics": [RIZQ, SABR]}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", OUT)
