#!/usr/bin/env python3
"""Generate README.md (English) and README.zh-CN.md (Chinese) gallery files
from prompts/prompts.json.

Only entries whose preview image has actually been generated are rendered, so
the gallery always displays correctly. Re-run after generating more images.
"""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "prompts", "prompts.json")

CATEGORY_ORDER = [
    "Photography", "Illustration & 3D", "Product & Brand",
    "Food & Drink", "Poster Design", "UI & Graphic",
]
CAT_ANCHOR = {c: c.lower().replace(" & ", "--").replace(" ", "-") for c in CATEGORY_ORDER}
CAT_ZH = {
    "Photography": "摄影",
    "Illustration & 3D": "插画 & 3D",
    "Product & Brand": "产品 & 品牌",
    "Food & Drink": "美食 & 饮品",
    "Poster Design": "海报设计",
    "UI & Graphic": "UI & 图形",
}


def load():
    d = json.load(open(DATA, encoding="utf-8"))
    rendered = [p for p in d["prompts"] if os.path.exists(os.path.join(REPO, p["image"]))]
    return d["meta"], d["prompts"], rendered


def entry_block(p, rank, lang):
    title = html.escape(p["title"])
    kw = ", ".join(p["keywords"][:6])
    img = p["image"]
    prompt = p["prompt"]
    if lang == "en":
        summary = f"#{rank} · {title} · <code>{p['engine']}</code>"
        details_label = "Show prompt"
        kw_line = f"\n\n> Keywords: {html.escape(kw)}" if kw else ""
    else:
        summary = f"#{rank} · {title} · <code>{p['engine']}</code>"
        details_label = "查看提示词"
        kw_line = f"\n\n> 关键词：{html.escape(kw)}" if kw else ""
    return (
        f'<img src="{img}" width="400" alt="{title}" />\n\n'
        f"**{summary}**{kw_line}\n\n"
        f"<details>\n<summary>{details_label}</summary>\n\n"
        f"```\n{prompt}\n```\n\n"
        f"</details>\n"
    )


def build(lang):
    meta, allp, rendered = load()
    cat_to_items = {c: [] for c in CATEGORY_ORDER}
    for p in rendered:
        cat_to_items.setdefault(p["category"], []).append(p)

    L = lang == "en"
    out = []
    if L:
        out.append("# Awesome Image & Video Prompts — Updating\n")
        out.append(
            f"[![Website](https://img.shields.io/badge/website-vinano.ai-6d28d9)](https://vinano.ai) "
            f"![Prompts](https://img.shields.io/badge/prompts-{meta['count']}-brightgreen) "
            f"![Format](https://img.shields.io/badge/format-JSON-blue) "
            f"![License](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey)\n"
        )
        out.append(
            "\nA continuously-updated, **original** collection of image & video prompts.\n\n"
            "- Every prompt is refined in-house — not a verbatim copy of any third-party list.\n"
            "- Every preview image is **regenerated with [vinano.ai](https://vinano.ai)**.\n"
            "- Machine-readable data lives in [`prompts/prompts.json`](prompts/prompts.json).\n"
            "- System prompts for building your own generator: "
            "[EN](prompts/system-prompt-en.md) · [中文](prompts/system-prompt-zh.md).\n\n"
            "> 中文版本见 [README.zh-CN.md](README.zh-CN.md)。\n"
        )
        out.append(f"\n**{meta['count']} prompts** across {len(CATEGORY_ORDER)} categories. "
                   f"Last updated: {meta['updated']}.\n")
        out.append("\n## Categories\n")
    else:
        out.append("# 图片 & 视频提示词精选 — 持续更新\n")
        out.append(
            f"[![官网](https://img.shields.io/badge/官网-vinano.ai-6d28d9)](https://vinano.ai) "
            f"![提示词](https://img.shields.io/badge/提示词-{meta['count']}-brightgreen) "
            f"![格式](https://img.shields.io/badge/格式-JSON-blue) "
            f"![许可](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey)\n"
        )
        out.append(
            "\n一个持续更新的**原创**图片 & 视频提示词合集。\n\n"
            "- 所有提示词均经过自有改写，并非第三方清单的逐字复制。\n"
            "- 所有预览图片均由 **[vinano.ai](https://vinano.ai)** 重新生成。\n"
            "- 结构化数据见 [`prompts/prompts.json`](prompts/prompts.json)。\n"
            "- 自建生成器可用的系统提示词："
            "[English](prompts/system-prompt-en.md) · [中文](prompts/system-prompt-zh.md)。\n\n"
            "> English version: [README.md](README.md)。\n"
        )
        out.append(f"\n**共 {meta['count']} 条提示词**，覆盖 {len(CATEGORY_ORDER)} 个分类。"
                   f"最近更新：{meta['updated']}。\n")
        out.append("\n## 分类目录\n")

    total_all = meta.get("by_category", {})
    for c in CATEGORY_ORDER:
        name = c if L else CAT_ZH[c]
        shown = len(cat_to_items.get(c, []))
        tot = total_all.get(c, shown)
        out.append(f"- [{name}](#{CAT_ANCHOR[c]}) — {tot}\n")

    note = ("\n> Note: the gallery below shows previews already regenerated with vinano.ai. "
            "The full set of prompts is in `prompts/prompts.json`; run "
            "`python3 scripts/generate_images.py` to render the rest.\n"
            if L else
            "\n> 说明：下方画廊展示的是已用 vinano.ai 重新生成的预览图。"
            "全部提示词见 `prompts/prompts.json`，运行 "
            "`python3 scripts/generate_images.py` 可生成其余图片。\n")
    out.append(note)

    for c in CATEGORY_ORDER:
        name = c if L else CAT_ZH[c]
        items = cat_to_items.get(c, [])
        out.append(f'\n## {name}\n')
        if not items:
            out.append(("\n_Previews coming soon._\n" if L else "\n_预览图即将上线。_\n"))
            continue
        for i, p in enumerate(items, 1):
            out.append("\n" + entry_block(p, i, lang) + "\n---\n")

    footer = ("\n## License\n\nPrompts and metadata are released under "
              "[CC BY 4.0](LICENSE). Images are generated with [vinano.ai](https://vinano.ai).\n"
              if L else
              "\n## 许可\n\n提示词与元数据以 [CC BY 4.0](LICENSE) 授权发布。"
              "图片由 [vinano.ai](https://vinano.ai) 生成。\n")
    out.append(footer)

    path = os.path.join(REPO, "README.md" if L else "README.zh-CN.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))
    print(f"wrote {path} ({len(rendered)} preview entries)")


if __name__ == "__main__":
    build("en")
    build("zh")
