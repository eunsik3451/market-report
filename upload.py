"""
글로벌 마켓 데일리 — GitHub Pages 자동 업로드
사용법: python upload.py daily_market_20260402.html
"""

import sys, shutil, subprocess, re, json
from datetime import datetime
from pathlib import Path

REPO_DIR   = Path(r"C:\Users\hp\Desktop\market-report")
INDEX_FILE = REPO_DIR / "index.html"
SITE_URL   = "https://eunsik3451.github.io/market-report"


# ── git 실행 ──────────────────────────────────────────────
def run(cmd):
    r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"  ✗ {r.stderr.strip()}")
        return False
    if r.stdout.strip():
        print(f"  {r.stdout.strip()}")
    return True


# ── 헬퍼 ──────────────────────────────────────────────────
def _extract(html, pattern):
    m = re.search(pattern, html)
    if m:
        return next((g for g in m.groups() if g), None)
    return None

def _pct(v):
    if v and not v.endswith('%'):
        return v + '%'
    return v

def _cls(v):
    if not v or v == "—": return "nt"
    return "up" if "+" in v else "dn"

def _trio(a, b, c, ca, cb, cc):
    return (f'🇰🇷 <span class="{ca}">{a}</span> &nbsp;'
            f'🇺🇸 <span class="{cb}">{b}</span> &nbsp;'
            f'🛢️ <span class="{cc}">{c}</span>')

def _kw_html(keywords, cls):
    if not keywords:
        return ""
    tags = "".join(f'<span class="{cls}">{k}</span>' for k in keywords)
    return f'<div class="kw-row">{tags}</div>'


# ── 리포트 메타 파싱 ───────────────────────────────────────
def parse_report_meta(filepath):
    html  = Path(filepath).read_text(encoding="utf-8")
    fname = Path(filepath).name

    m = re.search(r"(\d{4})(\d{2})(\d{2})", fname)
    if m:
        y, mo, d = m.groups()
        date_str   = f"{y}.{mo}.{d}"
        date_label = f"{y}년 {mo}월 {d}일"
    else:
        date_str   = datetime.today().strftime("%Y.%m.%d")
        date_label = datetime.today().strftime("%Y년 %m월 %d일")

    KO = {"Monday":"월","Tuesday":"화","Wednesday":"수",
          "Thursday":"목","Friday":"금","Saturday":"토","Sunday":"일"}
    try:
        weekday = KO.get(datetime.strptime(date_str, "%Y.%m.%d").strftime("%A"), "")
    except:
        weekday = ""

    is_weekly   = "weekly" in fname.lower() or "global" in fname.lower()
    rtype       = "weekly" if is_weekly else "daily"
    rtype_label = "주간 시황" if is_weekly else "일일 시황"

    # 등락률 파싱 — <tr> 단위로 종목명과 chg 수치 매핑
    def get_market_chg(names):
        for name in names:
            # tr 단위 파싱 (신버전/구버전 모두 대응)
            tr_pattern = rf'<tr[^>]*>(?:(?!<tr).)*?{re.escape(name)}(?:(?!<tr).)*?class="[^"]*chg[^"]*">([\+\-]\d+\.?\d*)%'
            v = _extract(html, tr_pattern)
            if v and ('+' in v or '-' in v):
                return v + '%'
            # 역방향 (chg가 먼저 나오는 경우)
            tr_pattern2 = rf'<tr[^>]*>(?:(?!<tr).)*?class="[^"]*chg[^"]*">([\+\-]\d+\.?\d*)%(?:(?!<tr).)*?{re.escape(name)}'
            v = _extract(html, tr_pattern2)
            if v and ('+' in v or '-' in v):
                return v + '%'
        return None

    kospi_chg  = get_market_chg(['KOSPI'])
    nasdaq_chg = get_market_chg(['나스닥'])
    sp_chg     = get_market_chg(['S&amp;P 500', 'S&P 500'])
    wti_chg    = get_market_chg(['WTI 원유', '🛢️ WTI', 'WTI'])
    gold_chg   = get_market_chg(['🥇 금', '금 (USD'])
    copper_chg = get_market_chg(['구리'])

    # 최대 변동 계산
    candidates = {"KOSPI": kospi_chg, "나스닥": nasdaq_chg,
                  "S&P": sp_chg, "WTI": wti_chg, "금": gold_chg}
    best_name, best_val, best_abs = "KOSPI", kospi_chg or "—", 0
    for name, val in candidates.items():
        if not val or val == "—":
            continue
        try:
            av = abs(float(val.replace('%', '')))
            if av > best_abs:
                best_abs, best_name, best_val = av, name, val
        except:
            pass

    best_class = "up" if best_val and "+" in best_val else "dn"

    def tc(v):
        if not v or v == "—": return "mix-bg"
        return "up-bg" if "+" in v else "dn-bg"

    thumb_class = "wk-bg" if is_weekly else tc(kospi_chg)

    # 요약
    sm = (re.search(r'class="s-bullets".*?<li[^>]*>(.*?)</li>', html, re.DOTALL) or
          re.search(r'class="summary-bullets".*?<li[^>]*>(.*?)</li>', html, re.DOTALL))
    summary = re.sub(r"<[^>]+>", "", sm.group(1)).strip()[:80] if sm else date_label + " 시황"

    # 키워드
    kw_m = re.search(r'class="kw-tags"[^>]*>(.*?)</div>', html, re.DOTALL)
    keywords = []
    if kw_m:
        keywords = re.findall(r'class="kw-tag"[^>]*>([^<]+)<', kw_m.group(1))
        keywords = [k.strip().lstrip('📌').strip() for k in keywords[:5]]

    return {
        "fname": fname, "date_str": date_str, "date_label": date_label,
        "weekday": weekday, "rtype": rtype, "rtype_label": rtype_label,
        "thumb_class": thumb_class, "best_name": best_name,
        "best_val": best_val, "best_class": best_class,
        "kospi_chg":  kospi_chg  or "—",
        "nasdaq_chg": nasdaq_chg or "—",
        "sp_chg":     sp_chg     or "—",
        "wti_chg":    wti_chg    or "—",
        "gold_chg":   gold_chg   or "—",
        "copper_chg": copper_chg or "—",
        "summary": summary, "keywords": keywords,
    }


# ── 카드 HTML 생성 ─────────────────────────────────────────
def build_card(meta, featured=False):
    kw_f = _kw_html(meta["keywords"], "fb-tag")
    kw_c = _kw_html(meta["keywords"], "cb-tag")
    kr   = meta["kospi_chg"]
    us   = meta["nasdaq_chg"]
    sp   = meta["sp_chg"]
    co   = meta["wti_chg"]
    gld  = meta["gold_chg"]
    bb   = f"{meta['best_name']} {meta['best_val']}"
    dl   = f"{meta['date_label']} {meta['weekday']}요일"

    trio_all = _trio(kr, us, co, _cls(kr), _cls(us), _cls(co))
    trio_kr  = _trio(kr, us, sp, _cls(kr), _cls(us), _cls(sp))
    trio_us  = _trio(us, sp, gld, _cls(us), _cls(sp), _cls(gld))
    trio_co  = _trio(co, gld, meta["copper_chg"], _cls(co), _cls(gld), _cls(meta["copper_chg"]))

    def tc(v):
        if not v or v == "—": return "mix-bg"
        return "up-bg" if "+" in v else "dn-bg"

    all_thumb = meta["thumb_class"]
    kr_thumb  = tc(kr)
    us_thumb  = tc(us)
    co_thumb  = tc(co)

    lbl_all = f"📅 {meta['rtype_label']} · {dl}"
    lbl_kr  = f"🇰🇷 한국 시황 · {dl}"
    lbl_us  = f"🇺🇸 미국 시황 · {dl}"
    lbl_co  = f"🪨 원자재 시황 · {dl}"

    if featured:
        return f"""
  <a href="{meta['fname']}" class="featured-card" data-type="{meta['rtype']}">
    <div class="featured-thumb {all_thumb}">
      <div class="thumb-type">{meta['rtype_label']} · {meta['date_str']}</div>
      <div class="thumb-headline">
        <span class="num {meta['best_class']}">{bb}</span>
      </div>
      <div class="thumb-metrics">
        <div class="thumb-metric">🇰🇷 KOSPI <span class="val {_cls(kr)}">{kr}</span></div>
        <div class="thumb-metric">🇺🇸 나스닥 <span class="val {_cls(us)}">{us}</span></div>
        <div class="thumb-metric">🛢️ WTI <span class="val {_cls(co)}">{co}</span></div>
      </div>
    </div>
    <div class="featured-body">
      <div class="featured-label">{lbl_all}</div>
      <div class="featured-title">{meta['summary'][:50]}</div>
      <div class="featured-summary">{meta['summary']}</div>
      {kw_f}
    </div>
  </a>"""
    else:
        return f"""
    <a href="{meta['fname']}" class="report-card" data-type="{meta['rtype']}">
      <div class="card-thumb {all_thumb}">
        <div class="thumb-type">{meta['rtype_label']} · {meta['date_str']}</div>
        <div class="thumb-headline">
          <span class="num {meta['best_class']}">{bb}</span>
        </div>
        <div class="thumb-metrics">
          <div class="thumb-metric">🇰🇷 <span class="val {_cls(kr)}">{kr}</span></div>
          <div class="thumb-metric">🇺🇸 <span class="val {_cls(us)}">{us}</span></div>
          <div class="thumb-metric">🛢️ <span class="val {_cls(co)}">{co}</span></div>
        </div>
      </div>
      <div class="card-body">
        <div class="card-date">{meta['date_label']} {meta['weekday']}요일</div>
        <div class="card-title">{meta['summary'][:45]}</div>
        {kw_c}
      </div>
    </a>"""


# ── CARD_DATA JS 객체 생성 ─────────────────────────────────
def build_card_data(meta):
    kr  = meta["kospi_chg"]
    us  = meta["nasdaq_chg"]
    sp  = meta["sp_chg"]
    co  = meta["wti_chg"]
    gld = meta["gold_chg"]
    cop = meta["copper_chg"]
    dl  = f"{meta['date_label']} {meta['weekday']}요일"

    def tc(v):
        if not v or v == "—": return "mix-bg"
        return "up-bg" if "+" in v else "dn-bg"

    return {
        "all": {
            "thumb": meta["thumb_class"],
            "big":   f"{meta['best_name']} {meta['best_val']}",
            "label": f"📅 {meta['rtype_label']} · {dl}",
            "trio":  _trio(kr, us, co, _cls(kr), _cls(us), _cls(co)),
        },
        "kr": {
            "thumb": tc(kr),
            "big":   f"KOSPI {kr}",
            "label": f"🇰🇷 한국 시황 · {dl}",
            "trio":  _trio(kr, us, sp, _cls(kr), _cls(us), _cls(sp)),
        },
        "us": {
            "thumb": tc(us),
            "big":   f"나스닥 {us}",
            "label": f"🇺🇸 미국 시황 · {dl}",
            "trio":  _trio(us, sp, gld, _cls(us), _cls(sp), _cls(gld)),
        },
        "co": {
            "thumb": tc(co),
            "big":   f"WTI {co}",
            "label": f"🪨 원자재 시황 · {dl}",
            "trio":  _trio(co, gld, cop, _cls(co), _cls(gld), _cls(cop)),
        },
    }


# ── index.html 재구성 ──────────────────────────────────────
def rebuild_index():
    def extract_date(f):
        m = re.search(r"(\d{8})", f.name)
        return m.group(1) if m else "00000000"

    reports = sorted(
        [f for f in REPO_DIR.glob("*market*.html") if f.name != "index.html"],
        key=extract_date, reverse=True
    )
    if not reports:
        print("  ℹ️  리포트 없음")
        return

    metas         = [parse_report_meta(r) for r in reports]
    featured_html = build_card(metas[0], featured=True)
    grid_html     = "\n".join(build_card(m) for m in metas[1:])
    fm            = metas[0]

    # CARD_DATA 생성
    card_data_js = "const CARD_DATA = " + json.dumps(
        {m["fname"]: build_card_data(m) for m in metas},
        ensure_ascii=False, indent=2
    ) + ";"

    idx = INDEX_FILE.read_text(encoding="utf-8")

    idx = re.sub(r'<!-- FEATURED_START -->[\s\S]*?<!-- FEATURED_END -->',
                 f'<!-- FEATURED_START -->{featured_html}\n  <!-- FEATURED_END -->',
                 idx)
    idx = re.sub(r'<!-- GRID_START -->[\s\S]*?<!-- GRID_END -->',
                 f'<!-- GRID_START -->\n{grid_html}\n  <!-- GRID_END -->',
                 idx)
    idx = re.sub(r'<!-- UPDATE_DATE -->[\s\S]*?<!-- /UPDATE_DATE -->',
                 f'<!-- UPDATE_DATE -->{fm["date_str"]} 기준<!-- /UPDATE_DATE -->',
                 idx)
    idx = re.sub(r'// <!-- CARD_DATA_START -->[\s\S]*?// <!-- CARD_DATA_END -->',
                 f'// <!-- CARD_DATA_START -->\n{card_data_js}\n// <!-- CARD_DATA_END -->',
                 idx)

    INDEX_FILE.write_text(idx, encoding="utf-8")
    print(f"  ✓ index.html 업데이트 완료 ({len(metas)}개 리포트)")


# ── 메인 ──────────────────────────────────────────────────
def upload(html_path):
    src = Path(html_path)
    if not src.exists():
        print(f"✗ 파일 없음: {html_path}")
        sys.exit(1)

    dst = REPO_DIR / src.name
    print(f"\n📤 업로드: {src.name}\n")

    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
        print("  ✓ 파일 복사 완료")
    else:
        print("  ✓ 파일 위치 확인 (복사 생략)")

    rebuild_index()
    run(["git", "add", "-A"])
    run(["git", "commit", "-m",
         f"리포트 업데이트: {src.name} ({datetime.today().strftime('%Y-%m-%d')})"])
    ok = run(["git", "push", "origin", "main"])

    if ok:
        print(f"\n🎉 업로드 완료!\n   🌐 {SITE_URL}\n")
    else:
        print("\n✗ push 실패 — git push origin main 수동 실행해보세요\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python upload.py <HTML파일>")
        sys.exit(1)
    upload(sys.argv[1])
