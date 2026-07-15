#!/usr/bin/env python3
"""素材总览 catalog generator.

Scans the three content trees, copies cover thumbnails into suucai/covers/,
extracts 小红书/视频号 文案, and emits suucai/index.html — a single browsable
page with ✅已发 / ⬜未发 badges. Re-run to refresh. Posted status is the
hand-maintained POSTED set below (flip when Elaine says 发了X).
"""
import os, re, json, shutil, html, glob

HOME = os.path.expanduser("~")
WS = f"{HOME}/zylos/workspace"
OUT = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.join(OUT, "covers")
os.makedirs(COVERS, exist_ok=True)

TINGLI = f"{WS}/poc-animated-explainer/tingli-engine/out"
GAOKAO = f"{WS}/zhonggaokao-waikan"
CHUZHONG = f"{WS}/chuzhong-waikan-staging"

# --- posted status (flip when Elaine confirms 发了X) ---
POSTED = {
    # 听力 — Elaine 07-15 确认 changdh-04 已发（changdh-05 未发）
    "听力|mokao-01","听力|mokao-02","听力|mokao-03","听力|mokao-04","听力|mokao-05",
    "听力|mokao-06","听力|mokao-07","听力|mokao-08","听力|changdh-01","听力|changdh-02",
    "听力|changdh-03","听力|changdh-04","听力|chuzhong-01","听力|zhenti-01","听力|jinjie-01",
    "听力|gaokao-d1","听力|gaokao-d2",
    # 高考外刊 — Elaine 07-14 确认发到 No.07（No.08 威尼斯 07-14 刚交付, 未发）
    "高考外刊|1","高考外刊|2","高考外刊|3","高考外刊|4","高考外刊|5","高考外刊|6","高考外刊|7",
    # 初中外刊 — 发到 No.08（No.09 韦布 / No.10 二十四节气 07-14 刚补发, 未发）
    "初中外刊|1","初中外刊|2","初中外刊|3","初中外刊|4","初中外刊|5","初中外刊|6","初中外刊|7","初中外刊|8",
}

SKIP_TINGLI = {"demo", "gaokao-sample"}

# 听力 human labels
TINGLI_LABEL = {
    "changdh": "长对话精选", "mokao": "中考模拟·短题", "chuzhong": "中考听力",
    "zhenti": "真题听力", "jinjie": "进阶听力", "gaokao": "高考听力",
}

def read(p):
    try: return open(p, encoding="utf-8").read()
    except Exception: return ""

def split_wenan(text):
    """Return (xhs, sph) best-effort; fallback whole text in xhs."""
    if not text: return ("", "")
    # normalize markers
    parts = re.split(r'#+\s*(?:【[^】]*】\s*)?(?:第[一二]条\s*·?\s*)?(小红书|视频号)', text)
    xhs, sph = "", ""
    for i in range(1, len(parts)-1, 2):
        tag = parts[i]; body = parts[i+1]
        body = re.sub(r'^[·\s—-]*(——[^\n]*)?', '', body).strip()
        body = re.split(r'\n#+\s', body)[0].strip()
        if tag == "小红书" and not xhs: xhs = body
        elif tag == "视频号" and not sph: sph = body
    if not xhs and not sph:
        xhs = text.strip()
    return (xhs, sph)

def derive_topic(wenan, slug):
    m = re.search(r'读懂([^｜|，,\n]+)', wenan)
    if m: return m.group(1).strip()
    m = re.search(r'标题[^:：]*[:：]\s*[*"「]*([^\n*"」]{4,40})', wenan)
    if m: return m.group(1).strip()
    return slug

items = {"听力": [], "高考外刊": [], "初中外刊": []}

# --- 听力 ---
for name in sorted(os.listdir(TINGLI)):
    d = os.path.join(TINGLI, name)
    if name in SKIP_TINGLI or not os.path.isdir(d): continue
    if not os.path.exists(os.path.join(d, "FINAL.mp4")): continue
    pre = re.match(r'([a-z]+)', name).group(1)
    label = TINGLI_LABEL.get(pre, pre)
    wtext = ""
    for wf in glob.glob(os.path.join(d, "*.md")) + glob.glob(os.path.join(d, "文案.md")):
        wtext = read(wf); break
    xhs, sph = split_wenan(wtext)
    meta = read(os.path.join(d, "meta.json"))
    dur = ""
    try: dur = f"{json.load(open(os.path.join(d,'meta.json')))['dur']:.0f}s"
    except Exception: pass
    items["听力"].append({
        "id": name, "no": name, "topic": label, "dur": dur,
        "cover": None, "xhs": xhs, "sph": sph,
        "posted": f"听力|{name}" in POSTED,
    })

# --- 外刊 (高考 + 初中) ---
def scan_waikan(root, line):
    for d in sorted(glob.glob(os.path.join(root, "day*"))):
        base = os.path.basename(d)
        m = re.match(r'day(\d+)-(.+)', base)
        if not m: continue
        no, slug = m.group(1), m.group(2)
        covers = glob.glob(os.path.join(d, "tietu-*", "tietu-01-cover.png"))
        cover_rel = None
        if covers:
            dst = f"{line}-{no}.png"
            shutil.copy(covers[0], os.path.join(COVERS, dst))
            cover_rel = f"covers/{dst}"
        wtext = ""
        for wf in glob.glob(os.path.join(d, "wenan-*.md")):
            wtext = read(wf); break
        xhs, sph = split_wenan(wtext)
        topic = derive_topic(wtext, slug)
        items[line].append({
            "id": base, "no": f"No.{int(no):02d}", "topic": topic,
            "cover": cover_rel, "xhs": xhs, "sph": sph, "dur": "",
            "posted": f"{line}|{int(no)}" in POSTED,
        })
    items[line].sort(key=lambda x: int(re.search(r'\d+', x["no"]).group()))

scan_waikan(GAOKAO, "高考外刊")
scan_waikan(CHUZHONG, "初中外刊")

# --- emit HTML ---
def esc(s): return html.escape(s or "")

def card(it):
    badge = ('<span class="b posted">✅ 已发</span>' if it["posted"]
             else '<span class="b todo">⬜ 未发</span>')
    cov = (f'<img loading="lazy" src="{it["cover"]}" alt="">' if it["cover"]
           else f'<div class="noimg">🎧<br>{esc(it["dur"])}</div>')
    def cp(label, txt):
        if not txt: return ""
        return (f'<div class="wblk"><div class="wh">{label}'
                f'<button class="cp" onclick="cp(this)">复制</button></div>'
                f'<pre>{esc(txt)}</pre></div>')
    return (f'<div class="card {"done" if it["posted"] else ""}">'
            f'<div class="top">{cov}<div class="meta"><div class="no">{esc(it["no"])} {badge}</div>'
            f'<div class="tp">{esc(it["topic"])}</div></div></div>'
            f'<div class="wraps">{cp("小红书", it["xhs"])}{cp("视频号", it["sph"])}</div>'
            f'</div>')

def section(title, key, emoji):
    lst = items[key]
    done = sum(1 for x in lst if x["posted"])
    cards = "".join(card(x) for x in lst)
    return (f'<section><h2>{emoji} {title} <span class="cnt">{done}/{len(lst)} 已发</span></h2>'
            f'<div class="grid">{cards}</div></section>')

HTML = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>素材总览 · 每日英语</title>
<style>
:root{{--bg:#f7f5f0;--card:#fff;--navy:#1f3a5f;--gold:#b8860b;--ink:#2c2c2c;--mut:#8a8a8a;--line:#e8e4dc}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"PingFang SC",system-ui,sans-serif}}
header{{background:var(--navy);color:#fff;padding:18px 20px}}header h1{{margin:0;font-size:19px}}header p{{margin:6px 0 0;font-size:13px;opacity:.85}}
main{{max-width:1100px;margin:0 auto;padding:16px}}
section{{margin:22px 0}}h2{{font-size:17px;border-left:4px solid var(--gold);padding-left:10px;margin:0 0 12px}}
.cnt{{font-size:12px;color:var(--mut);font-weight:400;margin-left:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.card.done{{opacity:.62}}
.top{{display:flex;gap:10px}}.top img{{width:72px;height:96px;object-fit:cover;border-radius:8px;flex:none}}
.noimg{{width:72px;height:96px;border-radius:8px;background:#eef1f5;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--navy);font-size:12px;flex:none}}
.meta{{min-width:0}}.no{{font-size:12px;color:var(--mut);display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.tp{{font-size:15px;font-weight:600;margin-top:3px}}
.b{{font-size:11px;padding:1px 7px;border-radius:20px;font-weight:600}}.posted{{background:#e8f5e9;color:#2e7d32}}.todo{{background:#fff3e0;color:#e65100}}
.wraps{{margin-top:10px;display:flex;flex-direction:column;gap:8px}}
.wblk{{background:#faf9f6;border:1px solid var(--line);border-radius:8px;overflow:hidden}}
.wh{{display:flex;justify-content:space-between;align-items:center;background:#f0ede6;padding:5px 10px;font-size:12px;font-weight:600;color:var(--navy)}}
.cp{{border:0;background:var(--navy);color:#fff;font-size:11px;padding:3px 10px;border-radius:6px;cursor:pointer}}.cp:active{{transform:scale(.95)}}
pre{{margin:0;padding:9px 10px;white-space:pre-wrap;word-break:break-word;font:13px/1.55 -apple-system,"PingFang SC",sans-serif;max-height:180px;overflow:auto}}
footer{{text-align:center;color:var(--mut);font-size:12px;padding:24px}}
</style></head><body>
<header><h1>📚 素材总览 · 每日英语</h1><p>挑未发的发 · 文案点「复制」直接用 · 发完告诉 CC 标 ✅ · 页面随时更新</p></header>
<main>
{section("听力（中考/高考）","听力","🎧")}
{section("高考外刊精读","高考外刊","📖")}
{section("初中外刊精读","初中外刊","📖")}
</main>
<footer>CC 维护 · 视频找 CC 发（发完自动标已发）</footer>
<script>
function cp(b){{const t=b.closest('.wblk').querySelector('pre').innerText;
navigator.clipboard.writeText(t).then(()=>{{const o=b.textContent;b.textContent='✓ 已复制';setTimeout(()=>b.textContent=o,1200)}})}}
</script></body></html>"""

open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(HTML)
tot = sum(len(v) for v in items.values())
done = sum(1 for v in items.values() for x in v if x["posted"])
print(f"catalog built: {tot} items ({done} 已发) | 听力 {len(items['听力'])} · 高考 {len(items['高考外刊'])} · 初中 {len(items['初中外刊'])}")
print(f"covers copied: {len(os.listdir(COVERS))}")
