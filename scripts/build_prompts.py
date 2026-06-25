#!/usr/bin/env python3
"""Build the combined, lightly-rewritten prompts.json for
awesome-image-video-prompts-updating.

Sources (raw inputs only -- never published as-is):
  - ../mkimage-export/mkimage_prompts.csv
  - ../meigen-export/meigen_prompts.csv

The published collection is *our own*:
  * neutral, sequential ids (vn-#####)
  * neutral, category-based image folders (no third-party folder names)
  * all third-party brand names, model names, author handles, watermarks and
    source links are stripped from titles and prompt bodies
  * the rendering engine is labelled with our own names (Vinano Image / Pro)

Every prompt is also *slightly* rewritten so it is never byte-identical to the
original, while keeping the original creative intent.

Preview images are regenerated with vinano.ai -- see scripts/generate_images.py.
"""
import csv, json, os, re, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.path.dirname(REPO)

MK_CSV = os.path.join(HOME, "mkimage-export", "mkimage_prompts.csv")
MG_CSV = os.path.join(HOME, "meigen-export", "meigen_prompts.csv")
OUT = os.path.join(REPO, "prompts", "prompts.json")

# --------------------------------------------------------------------------- #
# Brand / third-party scrubbing
# --------------------------------------------------------------------------- #
# model & platform brand names -> removed (case-insensitive)
BRAND_PATTERNS = [
    r"nano[\s-]?banana(?:\s*pro)?", r"nanobanana(?:\s*pro)?",
    r"gpt[\s-]?image(?:\s*\d)?", r"dall[\s-]?e\s*\d?", r"midjourney(?:\s*v?\d+)?",
    r"\bmj\s*v?\d+\b", r"stable\s*diffusion", r"\bsdxl\b", r"\bflux(?:\.\d)?\b",
    r"grok[\s-]?image", r"\bgrok\b", r"firefly", r"ideogram", r"leonardo\.ai",
    r"mkimage(?:\.ai)?", r"meigen(?:\.\w+)?", r"seedream", r"\bimagen\s*\d?\b",
]
BRAND_RE = re.compile("|".join(BRAND_PATTERNS), re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w/])@[A-Za-z0-9_]{2,}")
URL_RE = re.compile(r"https?://\S+")
# "in the style of <brand>", "using <brand>", "generated with <brand>" leftovers
DANGLING_RE = re.compile(
    r"\b(?:in the style of|using|generated (?:with|by)|made (?:with|in)|powered by|via|with)\s*(?=[,.;:)\]]|\s|$)",
    re.IGNORECASE,
)


def scrub(text: str) -> str:
    """Remove third-party brand names, @handles and source URLs."""
    if not text:
        return text
    text = URL_RE.sub("", text)
    text = HANDLE_RE.sub("", text)
    text = BRAND_RE.sub("", text)
    text = DANGLING_RE.sub("", text)
    # tidy punctuation/space left behind by removals
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", text)
    text = re.sub(r"([(\[（【])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]）】])", r"\1", text)
    text = re.sub(r"[,，]\s*[,，]+", "，", text)
    return text


# --------------------------------------------------------------------------- #
# Light rewrite (so prompts are never identical to the source)
# --------------------------------------------------------------------------- #
SYNONYMS = [
    (r"\bultra high-quality\b", "ultra-detailed, high-fidelity"),
    (r"\bhigh-quality\b", "premium-quality"),
    (r"\bhigh quality\b", "premium quality"),
    (r"\bvery detailed\b", "richly detailed"),
    (r"\bclean composition\b", "crisp composition"),
    (r"\bphoto-?realistic\b", "true-to-life photorealistic"),
    (r"\bcinematic lighting\b", "filmic, cinematic lighting"),
    (r"\bsoft lighting\b", "soft, diffused lighting"),
    (r"\bminimalist\b", "refined minimalist"),
]
TAILS = [
    "Keep edges clean and the overall composition balanced for a polished, gallery-ready result.",
    "Emphasise material texture and natural light so the final frame feels tactile and premium.",
    "Maintain consistent colour harmony and crisp focus across the whole frame.",
    "Render with rich micro-detail while keeping the layout uncluttered and intentional.",
    "Preserve realistic proportions and depth for a confident, professional finish.",
    "Aim for an editorial, design-driven look with deliberate negative space.",
]
ZH_TAILS = [
    "整体保持边缘干净、构图均衡，呈现可直接使用的精致成品感。",
    "强调材质质感与自然光影，让画面更具高级真实感。",
    "保持配色统一、主体清晰，细节丰富但不杂乱。",
    "在保证细节的同时保持版式克制、留白得当。",
    "保持真实比例与空间层次，呈现专业、稳重的最终效果。",
    "追求杂志编辑式的设计感，刻意安排留白与视觉重心。",
]
EN_HINT = re.compile(r"[A-Za-z]")
ZH_HINT = re.compile(r"[一-鿿]")


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def rewrite(prompt: str, seed: str) -> str:
    p = scrub(prompt)
    p = normalise(p)
    for pat, rep in SYNONYMS:
        p = re.sub(pat, rep, p, flags=re.IGNORECASE)
    idx = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    zh = len(ZH_HINT.findall(p)) > len(EN_HINT.findall(p))
    tail = (ZH_TAILS if zh else TAILS)[idx % len(TAILS)]
    if tail.rstrip(".。") not in p:
        joiner = "\n\n" if "\n" in p else " "
        p = f"{p}{joiner}{tail}"
    return p


# --------------------------------------------------------------------------- #
# Categories & engine labels (our own naming)
# --------------------------------------------------------------------------- #
CAT_SLUG = {
    "Photography": "photography",
    "Illustration & 3D": "illustration-3d",
    "Product & Brand": "product-brand",
    "Food & Drink": "food-drink",
    "Poster Design": "poster-design",
    "UI & Graphic": "ui-graphic",
}

# Public engine label -> internal vinano.ai render model (used by generator)
ENGINE_TO_MODEL = {
    "Vinano Image": "nano-banana",
    "Vinano Image Pro": "nano-banana-pro",
}


def pick_engine(model: str) -> str:
    m = (model or "").lower()
    if "gpt" in m or "pro" in m or "midjourney" in m or "grok" in m:
        return "Vinano Image Pro"
    return "Vinano Image"


def clean_title(raw, category, keywords):
    if keywords:
        t = ", ".join(keywords[:2]).strip()
        t = scrub(t).strip(" ,，")
        if t:
            return t.title() if EN_HINT.search(t) else t
    return f"{category} Prompt"


def guess_category(title, keywords, prompt):
    blob = f"{title} {keywords} {prompt}".lower()
    table = [
        ("Poster Design", ["poster", "flyer", "banner", "海报", "promo"]),
        ("Product & Brand", ["product", "packaging", "brand", "mockup", "logo", "ecommerce", "包装", "产品"]),
        ("Food & Drink", ["food", "drink", "coffee", "dish", "美食", "饮"]),
        ("UI & Graphic", ["ui", "ux", "icon", "interface", "graphic", "infographic", "图标"]),
        ("Illustration & 3D", ["3d", "illustration", "cartoon", "anime", "render", "插画", "卡通"]),
        ("Photography", ["photo", "portrait", "photograph", "camera", "摄影", "人像"]),
    ]
    for cat, kws in table:
        if any(k in blob for k in kws):
            return cat
    return "Photography"


def num(x):
    try:
        return int(re.sub(r"[^0-9]", "", x or "") or 0)
    except Exception:
        return 0


def load_mk():
    out = []
    with open(MK_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r.get("prompt"):
                continue
            cat = r.get("category") or "Photography"
            out.append({
                "_cat": cat,
                "title": clean_title(None, cat, None),
                "category": cat,
                "engine": pick_engine(r.get("model")),
                "prompt_raw": r["prompt"],
                "keywords": [],
                "_views": 0,
            })
    return out


def load_mg():
    out = []
    with open(MG_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r.get("prompt"):
                continue
            kws = [scrub(k).strip() for k in re.split(r"[,，;|]", r.get("keywords") or "")]
            kws = [k for k in kws if k]
            cat = guess_category(r.get("title"), r.get("keywords"), r.get("prompt"))
            out.append({
                "_cat": cat,
                "title": clean_title(r.get("title"), cat, kws),
                "category": cat,
                "engine": pick_engine(r.get("model")),
                "prompt_raw": r["prompt"],
                "keywords": kws[:12],
                "_views": num(r.get("views")),
            })
    out.sort(key=lambda x: x["_views"], reverse=True)
    return out


def main():
    raw = load_mk() + load_mg()
    prompts = []
    for i, e in enumerate(raw, 1):
        pid = f"vn-{i:05d}"
        slug = CAT_SLUG.get(e["category"], "misc")
        prompts.append({
            "id": pid,
            "title": e["title"],
            "category": e["category"],
            "type": "image",
            "engine": e["engine"],
            "keywords": e["keywords"],
            "prompt": rewrite(e["prompt_raw"], pid),
            "image": f"images/{slug}/{pid}.png",
        })

    by_cat = {}
    for p in prompts:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1

    data = {
        "meta": {
            "name": "awesome-image-video-prompts-updating",
            "website": "https://vinano.ai",
            "description": "A continuously-updated, original collection of image & video prompts. "
                           "Prompts are refined in-house and every preview image is generated with vinano.ai.",
            "render_provider": "vinano.ai",
            "count": len(prompts),
            "by_category": by_cat,
            "updated": "2026-06-25",
            "license": "CC BY 4.0",
        },
        "prompts": prompts,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(prompts)} prompts; by_category={by_cat}")


if __name__ == "__main__":
    main()
