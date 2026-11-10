"""Builds data/quran.json and data/hadith.json from the open-source fawazahmed0 datasets.

Run once on a computer that has the two repos checked out (not needed for daily posting):
  python tools/build_data.py <quran-api-dir> <hadith-api-dir>
Quran Arabic: ara-quranuthmanienc (Uthmani script). English: eng-ummmuhammad (Saheeh International).
Hadith: Forty Hadith of an-Nawawi (eng-nawawi).
Nothing is written or paraphrased by an AI; text is copied verbatim from the datasets.
"""
import json, os, re, sys

QURAN, HADITH = sys.argv[1], sys.argv[2]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SURAH = {2: "Al-Baqarah", 3: "Ali 'Imran", 7: "Al-A'raf", 9: "At-Tawbah", 12: "Yusuf", 13: "Ar-Ra'd", 14: "Ibrahim",
         16: "An-Nahl", 17: "Al-Isra", 18: "Al-Kahf", 20: "Ta-Ha", 21: "Al-Anbiya", 23: "Al-Mu'minun", 25: "Al-Furqan",
         29: "Al-'Ankabut", 33: "Al-Ahzab", 39: "Az-Zumar", 40: "Ghafir", 51: "Adh-Dhariyat", 55: "Ar-Rahman",
         57: "Al-Hadid", 64: "At-Taghabun", 65: "At-Talaq", 93: "Ad-Duha", 94: "Ash-Sharh", 112: "Al-Ikhlas"}

# (reference, kind, title)  kind: ayah = reminder, dua = supplication from the Quran
REFS = [
    ("94:5-6", "ayah", "With hardship comes ease"), ("2:152", "ayah", "Remember Allah, He remembers you"),
    ("13:28", "ayah", "Hearts find rest in the remembrance of Allah"), ("65:3", "ayah", "Whoever relies on Allah, He is enough for him"),
    ("3:139", "ayah", "Do not weaken or grieve"), ("29:69", "ayah", "Those who strive for Us, We guide them"),
    ("93:3-5", "ayah", "Your Lord has not abandoned you"), ("94:7-8", "ayah", "When you are free, strive on"),
    ("14:7", "ayah", "If you are grateful, I will increase you"), ("2:186", "ayah", ""), ("2:153", "ayah", "Seek help through patience and prayer"),
    ("51:56", "ayah", "Why we were created"), ("12:87", "ayah", "Never give up hope in Allah's mercy"),
    ("16:128", "ayah", "Allah is with those who fear Him and do good"), 
    ("64:11", "ayah", "No calamity strikes except by Allah's permission"),
    ("55:13", "ayah", "Which of your Lord's favours will you deny?"),
    
    ("2:201", "dua", "Dua for the best of this world and the next"), ("3:8", "dua", "Dua for a steadfast heart"),
    ("14:40", "dua", "Dua to keep up the prayer"), ("21:87", "dua", "Dua of Prophet Yunus (peace be upon him)"),
    ("25:74", "dua", "Dua for a righteous family"), ("17:24", "dua", "Dua for parents"),
    ("7:23", "dua", "Dua for forgiveness"), ("18:10", "dua", "Dua for mercy and guidance"),
    ("20:25-28", "dua", "Dua of Prophet Musa (peace be upon him) for ease"), ("14:41", "dua", "Dua for forgiveness for parents and believers"),
    ("23:118", "dua", "Dua for forgiveness and mercy"), ("2:250", "dua", "Dua for patience and steadfastness"),
    ("3:147", "dua", "Dua for forgiveness and firm feet"), 
]

def load(path):
    return {(v["chapter"], v["verse"]): v["text"] for v in json.load(open(path, encoding="utf-8"))["quran"]}


GLOBAL = {(v["chapter"], v["verse"]): i + 1 for i, v in enumerate(json.load(open(os.path.join(QURAN, "editions", "ara-quranuthmanienc.json"), encoding="utf-8"))["quran"])}
assert GLOBAL[(1, 1)] == 1 and GLOBAL[(2, 255)] == 262 and len(GLOBAL) == 6236

ar = load(os.path.join(QURAN, "editions", "ara-quranuthmanienc.json"))
en = load(os.path.join(QURAN, "editions", "eng-ummmuhammad.json"))

def fix_ar(t):
    return t.replace("ی", "ي")      # Farsi yeh -> Arabic yeh so the dots render correctly

items = []
for ref, kind, title in REFS:
    s, v = ref.split(":")
    a, _, b = v.partition("-")
    verses = list(range(int(a), int(b or a) + 1))
    arabic = " ".join(fix_ar(ar[(int(s), n)]) for n in verses)
    parts = [en[(int(s), n)].strip() for n in verses]
    english = " ".join(x if x[-1] in '.?!"\u201d' else x + "." for x in parts) if len(parts) > 1 else parts[0]
    if len(arabic) > 190 or len(english) > 260:
        continue
    items.append({"ref": ref, "kind": kind, "title": title if kind == "dua" else "", "surah": int(s), "surah_name": SURAH[int(s)],
                  "arabic": arabic, "english": english, "numbers": [GLOBAL[(int(s), n)] for n in verses]})
json.dump({"source": "Arabic: Uthmani (fawazahmed0/quran-api ara-quranuthmanienc). English: Saheeh International (eng-ummmuhammad).",
           "items": items}, open(os.path.join(OUT, "quran.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def split_sources(t):
    m = re.search(r"((?:\[[^\]]+\]\s*)+)$", t)
    sources = re.findall(r"\[([^\]]+)\]", m.group(1)) if m else []
    return (t[: m.start()].strip() if m else t.strip()), sources


heb = {h["hadithnumber"]: h["text"] for h in json.load(open(os.path.join(HADITH, "editions", "eng-nawawi.json"), encoding="utf-8"))["hadiths"]}
KEEP = [1, 3, 7, 12, 13, 15, 16, 17, 18, 20, 21, 26, 31, 32, 40]
hs = []
for n in KEEP:
    body, sources = split_sources(heb[n].strip())
    if len(body) <= 560:
        hs.append({"key": f"nawawi-{n}", "collection": "Forty Hadith of Imam an-Nawawi", "number": n, "text": body, "sources": sources})

bk = {h["hadithnumber"]: h["text"] for h in json.load(open(os.path.join(HADITH, "editions", "eng-bukhari.json"), encoding="utf-8"))["hadiths"]}
BUKHARI = [10, 13, 6005, 6012, 6013, 6021, 6029, 6038, 6114, 6125, 6168, 6309, 6412, 6446, 6462, 6464, 6405, 6133, 173, 6474, 6479, 6014, 6116, 5984, 7405]
for n in BUKHARI:
    t = bk[n].replace("\n", " ").strip()
    hs.append({"key": f"bukhari-{n}", "collection": "Sahih al-Bukhari", "number": n, "text": t, "sources": []})
json.dump({"source": "Forty Hadith of an-Nawawi (eng-nawawi) and Sahih al-Bukhari (eng-bukhari) from fawazahmed0/hadith-api; verbatim.",
           "items": hs}, open(os.path.join(OUT, "hadith.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(items), "quran items;", len(hs), "hadith")
