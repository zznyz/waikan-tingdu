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
    # 听力 — Elaine 07-15 确认 changdh-04 已发；changdh-06 07-19 两平台已发；
    #        07-26 Elaine 逐条确认完毕；05/09 于 07-30 补标已发。
    #        08-02 00:2x Elaine 原话「视频号11已经发送，bike坏了的那个，小红书没发」
    #          ⇒ changdh-11 标已发。**⚠️ 只发了视频号，小红书未发** —— 这张表是单一布尔值、
    #            不分平台，所以这条状态只活在这行注释里：要在小红书补发 ep11 是可以的，
    #            不算重复（听力线框架＝视频号发视频 · 小红书发图文，同一期两平台各发一次）。
    #        ⇒ changdh 已发 = 01–11 全部；未发 = 12 起。
    #        ⚠️ 她并不严格按期号顺序发（05、09 曾长期未发而 06/07/08/10 已发）——
    #           **绝不能从"发到第几期"推断中间某期的状态，只认她逐条确认。**
    "听力|mokao-01","听力|mokao-02","听力|mokao-03","听力|mokao-04","听力|mokao-05",
    "听力|mokao-06","听力|mokao-07","听力|mokao-08","听力|changdh-01","听力|changdh-02",
    "听力|changdh-03","听力|changdh-04","听力|changdh-05","听力|changdh-06","听力|changdh-07","听力|changdh-08","听力|changdh-09","听力|changdh-10","听力|changdh-11","听力|chuzhong-01","听力|zhenti-01","听力|jinjie-01",
    "听力|gaokao-d1","听力|gaokao-d2",
    # 高考外刊 — No.08 威尼斯 07-15 已发；No.09 睡眠 07-17 Elaine 确认已发；No.10 一人一药/基因编辑 07-20 两平台视频已发；
    #            No.11 珊瑚白化 07-31 Elaine 确认「珊瑚已发」（视频号/贴图号/公众号 + 朋友圈）
    #            No.12 棉花糖 08-02 23:4x Elaine 原话「棉花糖已经图文已发小红书」⇒ 标已发。
    #              ⚠️ **只发了小红书图文；视频号那版未发** —— 同听力那条：这张表是单一布尔值、
    #                不分平台，所以这条状态只活在这行注释里。视频号补发 No.12 是可以的、不算重复
    #                （跟读视频与视频号版文案都是现成的：day12-marshmallow/video-assets/ + wenan-marshmallow-No12.md）。
    "高考外刊|1","高考外刊|2","高考外刊|3","高考外刊|4","高考外刊|5","高考外刊|6","高考外刊|7","高考外刊|8","高考外刊|9","高考外刊|10","高考外刊|11","高考外刊|12",
    # 初中外刊 — No.09 韦布望远镜 07-23 Elaine 确认已发。
    #   🔴 No.10 二十四节气 2026-08-04 结案：Elaine 原话「**24节气翻了小红书，已经发了**」⇒ 标已发。
    #     成因值得记：这条在 07-23~08-04 之间一直是**两份真源打架** ——
    #     `chuzhong-waikan-staging/初中线-已交付进度.md` 记「✅已发布 07-25」（引她原话「24节气初中已发」），
    #     而这里的注释停在 07-23「未发」。**打架的根因是这张表漏翻，不是记录错**：
    #     07-23 的注释比她 07-25 那句话**早两天**，谁新谁对。
    #     ⇒ **规矩：这张表的注释要带日期，比对时先看谁更新**，⛔ 别拿旧注释去否定新确认。
    #     ⚠️ 她确认的是**小红书**（她翻的是小红书）。这张表是单一布尔值不分平台 ——
    #       视频号那版发没发**未确认**，所以视频号补发 No.10 不算重复。同听力 ep11 那条。
    "初中外刊|1","初中外刊|2","初中外刊|3","初中外刊|4","初中外刊|5","初中外刊|6","初中外刊|7","初中外刊|8","初中外刊|9","初中外刊|10",
}

# ─────────────────────────────────────────────────────────────────────────────
# 版本台账（Elaine 2026-08-02 02:0x 提的：「也可以放素材平台里…这样以后直接看平台记录
# 是否网盘和在售是最新款」）。
#
# **为什么要这一栏**：08-02 凌晨她连问三次「我网盘里那份是不是最新的」，每次都要现查时间戳。
# 而那晚真查出：高考外刊上篇有九篇扫码指向别的文章、下篇 12 篇一个码都没有 —— 她网盘里放的
# 正是那两个坏版本，且**已经卖了不少**。⇒ 这不是洁癖，是会伤到买家的事。
#
# 🔴 **每一行必须带一条"她自己翻一页就能查"的判据**，⛔ 别只写版本号：
#    版本号在文件名里，而文件名是可以被改掉的；页数在好几条线上**根本判不出版本**
#    （作文三本 full/v2/v3/v4 全是同样页数；高考外刊 v9→v12 全是 182 页）。
#
# 状态取值：ok=已是最新 · old=还是旧版·要换 · unknown=还没查
# 改法：换完/查完就把 pan（网盘）/ sale（在售）翻过来，跟 POSTED 一样手工维护。
#
# 🔴 **PAN_UPDATED ＝她换网盘的时间（北京时间），只有她能填**。
#    「出片时间」是我生成 PDF 的时间，**⛔ 不等于买家拿到新版的时间** —— 这两个数
#    2026-08-02 之前混在一起，她要的是后者（她原话：「最新版 bjt 时间 8.2 下午 15.25
#    最新版已发，已更新最终审核版」）。⛔ 没有她一句确认，这里不许填。
#    键＝上面 PRODUCTS 里的产品名，⚠️ 改产品名要同步改这里（下面有闸，对不上会报红）。
PAN_UPDATED = {
    "英语核心词汇手册 · 七上": "08-02 15:25 · 最终审核版",
    "高中外刊精读 · 上篇 No.01–18": "08-02 01:52",
    "高中外刊精读 · 下篇 No.19–30": "08-02 16:17 · 补挂",
}

PRODUCTS = [
    # (线, 产品, 最新文件, 页数, 出片时间(北京), pan, sale, 自查判据)
    ("外刊", "高中外刊精读 · 上篇 No.01–18", "高中外刊精读-合订本上篇-1-18-v12.pdf", "182 页", "08-02 00:29",
     "ok", "ok", "翻到 <b>第 104 页</b>（珊瑚白化）扫底下的码 → 落地页写「珊瑚白化」＝新版；写「睡眠与记忆」＝旧版"),
    # 🔴 2026-08-02 她自己去网盘查才发现：**下篇压根没挂上去过**，而这一行此前写着「网盘 ✅」。
    #    ⛔ 假的 ✅ 比空着更糟 —— 它让她和我都不再去查。
    #    ⇒ **一行只有在她亲口说"挂好了"之后才准写 ok**（跟 POSTED 同一条规矩）。
    #    ✅ 16:17 她已补挂 v3 并发截图确认（文件名 + 3.9M 与本地实测一致）。
    #    文件本身：12 个码逐个访问 12/12 通、12 个地址互不重复、每篇各扫各的（当天实测）。
    ("外刊", "高中外刊精读 · 下篇 No.19–30", "高中外刊精读-合订本下篇-19-30-v3.pdf", "134 页", "08-02 00:28",
     "ok", "ok", "翻到 <b>第 3 页</b>（深蓝篇章封面）→ 下方有<b>白色扫码卡</b>＝v3；没有＝旧版。⛔ 别看第 4 页原文页，新版那页本来就没码。<br>⚠️ <b>这一行的 ✅ 曾经是假的</b>：08-02 下午她自查才发现网盘压根没挂过下篇，当天 16:17 补挂。⇒ 这一栏只认她亲口确认，⛔ 不许推断"),
    ("词汇", "初中英语 1876 词汇手册", "zhongkao-1876-full-v5-lite.pdf（13MB 那个）", "381 页", "07-28 16:04",
     "ok", "ok", "翻到 <b>第 2 页</b>看释义列：写「人；人们；民族；种族」＝新版；写「<b>n.</b>人；人们…」＝旧版"),
    # 2026-08-02 v4：Starter 那一节的码原来只挂 U1 的音频（39 个词里 15 个扫不到），
    # 已换成合并音频，并把全册音频从 AX 的服务器迁到自己的 GitHub。排版一字未动
    # ⇒ v3/v4 同为 31 页，**页数判不出**，判据只能看码。
    ("词汇", "英语核心词汇手册 · 七上", "7shang-vocab-全册-v4-31页-Starter音频修复.pdf", "31 页", "08-02 02:07",
     "ok", "ok", "⛔ <b>页数判不出</b>（v3/v4 都是 31 页）。翻到 <b>第 3 页</b>扫「朗读」码，看下载的文件名：<b>7上-Starter-朗读.mp3</b>＝新版；<b>7上-U1-朗读.mp3</b>＝旧版（那节 15 个词没音频）。34 页＝更早的旧版。<br>✅ <b>老买家不用换</b>：在售 v3 的 16 个码 2026-08-02 逐个实测，全部 200 且下载实体与修好版 md5 一致——含 Starter 那两个（它们指向的文件名叫 <code>7上-U1-*</code>，名字是错的、内容早已换成合并好的 Starter 音频）"),
    # 2026-08-02 v4：把 16 个码从 AX 服务器迁到她自己 GitHub。排版一字未动
    # ⇒ v3/v4 同为 48 页，**页数判不出**（原来写「48 页＝新版」是错的，48 页只排除得掉 61 页那版）。
    # 🔑 实测（2026-08-02）：七上/八上/九上老码全部线上 200 且下载实体与修好版 md5 一致
    #    ⇒ **三本的老买家都不用换书**；换 v4 的目的只剩「码迁到她自己 GitHub、
    #    不再依赖别人的机器，顺带让文件名和内容对上」。
    # ⛔ **判版本别按文件名比** —— 我当天就栽在这儿：去服务器找 `7上-Starter-*` 找不到（404），
    #    就断定老买家扫不出音频要回访；其实老书那两个码指向的名字是 `7上-U1-*`，
    #    而那个文件的内容早已换成合并好的 Starter 音频。**判据要选买家实际会走的那条路。**
    ("词汇", "英语核心词汇手册 · 八上", "8shang-vocab-全册-v4-48页-音频修复.pdf", "48 页", "08-02 06:01",
     "old", "old", "⛔ <b>页数判不出</b>（v3/v4 都是 48 页；61 页＝更早的旧版）。翻到 <b>第 35 页</b>（Unit 6 默写单）扫「听默」码，看下载地址：<b>zznyz.github.io</b>＝v4；<b>opencode.ax0x.ai</b>＝v3。<br>🔑 <b>听内容判音频对不对</b>：听到 <b>Number 8</b> 念 <b>essay</b>＝音频已修；念 <b>AI</b>＝旧音频（AI 是专有名词、不在默写单上，从这里起后面全错一位）。⛔ 别拿 Unit 2 判——那单元没有专有名词，新旧一样"),
    ("词汇", "英语核心词汇手册 · 九上", "9shang-vocab-booklet-full.pdf", "38 页", "07-17 00:25",
     "unknown", "unknown", "看总页数 <b>38 页</b>。盘上只有这一版，没有旧版可混"),
    ("作文", "英语同步作文 · 七上", "7shang-essay-booklet-v4.pdf", "52 页", "07-29 09:34",
     "unknown", "unknown", "⛔ <b>页数判不出</b>（四个版本全是 52 页）。翻到 <b>第 17 页</b>：写「收尾 · <b>署名</b>」、范文结尾是「Lucy」＝新版；写「收尾 · 落款」、结尾「Yours, Lucy」＝旧版"),
    ("作文", "英语同步作文 · 八上", "8shang-essay-booklet-v3.pdf", "43 页", "07-29 09:13",
     "unknown", "unknown", "⛔ <b>页数判不出</b>（全是 43 页）。翻到 <b>第 16 页</b>：范文里有「We met on the first day of Grade 7, when he lent me his eraser…」＝新版；没这句＝旧版"),
    ("作文", "英语同步作文 · 九上", "9shang-essay-booklet-v3.pdf", "42 页", "07-29 09:13",
     "unknown", "unknown", "⛔ <b>页数判不出</b>（全是 42 页）。翻到 <b>第 29 页</b>：第 8 题是「我想那是因为向太空看去…」＝新版；是「说实话，我不知道所有的原因」＝旧版"),
    ("语法", "八下语法填空高频精练", "8xia-grammar-booklet-v6.pdf", "29 页", "07-29 14:29",
     "unknown", "unknown", "看总页数：<b>29 页</b>＝v6 新版；28 页＝v5"),
]

PSTAT = {"ok": ("✅ 最新", "posted"), "old": ("🔴 要换", "ready"), "unknown": ("⏳ 没查", "todo")}

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
        "ready": True,  # listed only if FINAL.mp4 exists → video always ready
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
        # "ready" = 跟读视频已渲 (video-assets/*.mp4 存在) → 贴图+文案+视频三件套齐
        vid = glob.glob(os.path.join(d, "video-assets", "*.mp4"))
        items[line].append({
            "id": base, "no": f"No.{int(no):02d}", "topic": topic,
            "cover": cover_rel, "xhs": xhs, "sph": sph, "dur": "",
            "posted": f"{line}|{int(no)}" in POSTED,
            "ready": bool(vid),
        })
    items[line].sort(key=lambda x: int(re.search(r'\d+', x["no"]).group()))

scan_waikan(GAOKAO, "高考外刊")
scan_waikan(CHUZHONG, "初中外刊")

# --- emit HTML ---
def esc(s): return html.escape(s or "")

def card(it):
    if it["posted"]:
        badge = '<span class="b posted">🟢 已发</span>'
    elif it.get("ready"):
        badge = '<span class="b ready">🟡 已做好·未发</span>'
    else:
        badge = '<span class="b todo">⬜ 待渲</span>'
    cov = (f'<img loading="lazy" src="{it["cover"]}" alt="">' if it["cover"]
           else f'<div class="noimg">🎧<br>{esc(it["dur"])}</div>')
    def cp(label, txt):
        if not txt: return ""
        return (f'<div class="wblk"><div class="wh">{label}'
                f'<button class="cp" onclick="cp(this)">复制</button></div>'
                f'<pre>{esc(txt)}</pre></div>')
    cls = "done" if it["posted"] else ("rdy" if it.get("ready") else "")
    return (f'<div class="card {cls}">'
            f'<div class="top">{cov}<div class="meta"><div class="no">{esc(it["no"])} {badge}</div>'
            f'<div class="tp">{esc(it["topic"])}</div></div></div>'
            f'<div class="wraps">{cp("小红书", it["xhs"])}{cp("视频号", it["sph"])}</div>'
            f'</div>')

def section(title, key, emoji):
    lst = items[key]
    done = sum(1 for x in lst if x["posted"])
    rdy = sum(1 for x in lst if x.get("ready") and not x["posted"])
    cards = "".join(card(x) for x in lst)
    return (f'<section><h2>{emoji} {title} '
            f'<span class="cnt">🟢{done} 已发 · 🟡{rdy} 待发 · 共{len(lst)}</span></h2>'
            f'<div class="grid">{cards}</div></section>')

def products_section():
    # PAN_UPDATED 的键必须对得上产品名 —— 改名字忘了同步，那个时间戳会静默消失
    # （静默消失比报错更糟：台账上看起来"她还没换网盘"）。
    unknown = set(PAN_UPDATED) - {p[1] for p in PRODUCTS}
    if unknown:
        raise SystemExit(f"[台账] PAN_UPDATED 里有对不上产品名的键: {sorted(unknown)}")
    rows = []
    for line, name, fn, pages, when, pan, sale, how in PRODUCTS:
        pt, pc = PSTAT[pan]
        st, sc = PSTAT[sale]
        upd = PAN_UPDATED.get(name, "")
        # 「怎么查」放进产品格里、不单开一列 —— 手机上第 5 列会被挤出屏幕，
        # 而那一列恰恰是全表唯一真正能判版本的东西（2026-08-02 截图实测发现）。
        rows.append(
            f'<tr><td class="pl">{esc(line)}</td>'
            f'<td><div class="pn">{esc(name)}</div>'
            f'<div class="pf">{esc(fn)} · {esc(pages)} · 出片 {esc(when)}</div>'
            f'<div class="how"><b>怎么查：</b>{how}</div></td>'
            f'<td class="c"><span class="b {pc}">{pt}</span>'
            + (f'<div class="upd">{esc(upd)}</div>' if upd else '') +
            f'</td>'
            f'<td class="c"><span class="b {sc}">{st}</span></td></tr>')
    todo = sum(1 for p in PRODUCTS if p[5] != "ok" or p[6] != "ok")
    return (f'<section><h2>🗂 版本台账 · 网盘/在售是不是最新 '
            f'<span class="cnt">共 {len(PRODUCTS)} 本 · {todo} 本待确认</span></h2>'
            f'<p class="tip">⛔ <b>别只看版本号和页数</b> —— 文件名能改，而作文三本和高考外刊的所有版本'
            f'<b>页数完全一样</b>。每一行右边那条「怎么查」才是能判的，翻一页就行。</p>'
            f'<div class="ptbl"><table><thead><tr><th>线</th><th>产品 / 最新文件 / 怎么查</th>'
            f'<th>网盘</th><th>在售</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></section>')

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
.b{{font-size:11px;padding:1px 7px;border-radius:20px;font-weight:600}}.posted{{background:#e8f5e9;color:#2e7d32}}.ready{{background:#fff8e1;color:#f9a825}}.todo{{background:#f0f0ee;color:#8a8a8a}}
.card.rdy{{border-color:#f9d777;box-shadow:0 1px 6px rgba(249,168,37,.15)}}
.wraps{{margin-top:10px;display:flex;flex-direction:column;gap:8px}}
.wblk{{background:#faf9f6;border:1px solid var(--line);border-radius:8px;overflow:hidden}}
.wh{{display:flex;justify-content:space-between;align-items:center;background:#f0ede6;padding:5px 10px;font-size:12px;font-weight:600;color:var(--navy)}}
.cp{{border:0;background:var(--navy);color:#fff;font-size:11px;padding:3px 10px;border-radius:6px;cursor:pointer}}.cp:active{{transform:scale(.95)}}
pre{{margin:0;padding:9px 10px;white-space:pre-wrap;word-break:break-word;font:13px/1.55 -apple-system,"PingFang SC",sans-serif;max-height:180px;overflow:auto}}
footer{{text-align:center;color:var(--mut);font-size:12px;padding:24px}}
.tip{{margin:0 0 10px;font-size:13px;color:#7a5b00;background:#fff8e1;border:1px solid #f3e2a9;border-radius:8px;padding:8px 10px}}
.ptbl{{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow-x:auto}}
.ptbl table{{border-collapse:collapse;width:100%}}
.ptbl th{{background:#f0ede6;color:var(--navy);font-size:12px;text-align:left;padding:8px 10px;white-space:nowrap}}
.ptbl td{{border-top:1px solid var(--line);padding:9px 10px;vertical-align:top;font-size:13px}}
.ptbl td.c{{text-align:center;white-space:nowrap}}
.pl{{color:var(--mut);font-size:12px;white-space:nowrap}}
.pn{{font-weight:600}}
.pf{{color:var(--mut);font-size:11.5px;margin-top:2px;word-break:break-all}}
.how{{color:#3d4a5c;line-height:1.5;margin-top:6px;background:#f5f8fc;border-left:3px solid #9fc0dc;border-radius:0 6px 6px 0;padding:6px 8px;font-size:12.5px}}
.upd{{color:var(--mut);font-size:11px;margin-top:4px;line-height:1.35}}
</style></head><body>
<header><h1>📚 素材总览 · 每日英语</h1><p>🟡 已做好·未发 = 随时能发｜挑一条跟 CC 说「推 No.X」拿整套 · 文案点「复制」直接用 · 发完标 🟢 · 页面随时更新</p></header>
<main>
{products_section()}
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
