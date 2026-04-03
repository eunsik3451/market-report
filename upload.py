"""
글로벌 마켓 데일리 — GitHub Pages 자동 업로드
─────────────────────────────────────────────
사용법:  python upload.py daily_market_20260402.html
─────────────────────────────────────────────
"""

import sys, shutil, subprocess, re
from datetime import datetime
from pathlib import Path

REPO_DIR   = Path(r"C:\Users\hp\Desktop\market-report")
INDEX_FILE = REPO_DIR / "index.html"
SITE_URL   = "https://eunsik3451.github.io/market-report"


def run(cmd):
    r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"  ✗ {r.stderr.strip()}")
        return False
    if r.stdout.strip():
        print(f"  {r.stdout.strip()}")
    return True


def _extract(html, pattern):
    m = re.search(pattern, html)
    if m:
        return next((g for g in m.groups() if g), None)
    return None


def parse_report_meta(filepath):
    html  = Path(filepath).read_text(encoding="utf-8")
    fname = Path(filepath).name

    # 날짜
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
        weekday = KO.get(datetime.strptime(date_str,"%Y.%m.%d").strftime("%A"),"")
    except:
        weekday = ""

    is_weekly  = "weekly" in fname.lower() or "global" in fname.lower()
    rtype      = "weekly" if is_weekly else "daily"
    rtype_label= "주간 시황" if is_weekly else "일일 시황"

    # 지표 파싱
    def pct(v):
        if v and not v.endswith('%'): return v+'%'
        return v

    kospi_chg  = pct(_extract(html, r'KOSPI[^<\d]*([\+\-]\d+\.?\d*)%') or
                     _extract(html, r'코스피[^<\d]*([\+\-]\d+\.?\d*)%'))
    nasdaq_chg = pct(_extract(html, r'나스닥[^<\d]*([\+\-]\d+\.?\d*)%') or
                     _extract(html, r'Nasdaq[^<\d]*([\+\-]\d+\.?\d*)%'))
    sp_chg     = pct(_extract(html, r'S&amp;P 500[^<\d]*([\+\-]\d+\.?\d*)%') or
                     _extract(html, r'S&P 500[^<\d]*([\+\-]\d+\.?\d*)%'))
    wti_chg    = pct(_extract(html, r'WTI[^\d<]*([\+\-]\d+\.?\d*)%'))
    gold_chg   = pct(_extract(html, r'금[^<\d]*([\+\-]\d+\.?\d*)%'))
    copper_chg = pct(_extract(html, r'구리[^<\d]*([\+\-]\d+\.?\d*)%'))

    # 최대 변동 계산 (절댓값 기준)
    candidates = {
        "KOSPI":  kospi_chg,
        "나스닥": nasdaq_chg,
        "S&P":    sp_chg,
        "WTI":    wti_chg,
        "금":     gold_chg,
    }
    best_name, best_val, best_abs = "KOSPI", kospi_chg or "—", 0
    for name, val in candidates.items():
        if not val or val == "—":
            continue
        try:
            av = abs(float(val.replace('%','')))
            if av > best_abs:
                best_abs  = av
                best_name = name
                best_val  = val
        except:
            pass

    best_class = "up" if best_val and '+' in best_val else "dn"

    # 배경 색상 — KOSPI 기준
    if kospi_chg and '+' in kospi_chg:
        thumb_class = "up-bg"
    elif kospi_chg and '-' in kospi_chg:
        thumb_class = "dn-bg"
    else:
        thumb_class = "mix-bg"
    if is_weekly:
        thumb_class = "wk-bg"

    # 핵심 요약
    sm = (re.search(r'class="s-bullets".*?<li[^>]*>(.*?)</li>', html, re.DOTALL) or
          re.search(r'class="summary-bullets".*?<li[^>]*>(.*?)</li>', html, re.DOTALL))
    summary = re.sub(r"<[^>]+>","", sm.group(1)).strip()[:80] if sm else date_label+" 시황"

    # 키워드 파싱
    kw_m = re.search(r'class="kw-tags"[^>]*>(.*?)</div>', html, re.DOTALL)
    keywords = []
    if kw_m:
        keywords = re.findall(r'class="kw-tag"[^>]*>([^<]+)<', kw_m.group(1))
        keywords = [k.strip().lstrip('📌').strip() for k in keywords[:5]]

    return {
        "fname":       fname,
        "date_str":    date_str,
        "date_label":  date_label,
        "weekday":     weekday,
        "rtype":       rtype,
        "rtype_label": rtype_label,
        "thumb_class": thumb_class,
        "best_name":   best_name,
        "best_val":    best_val,
        "best_class":  best_class,
        "kospi_chg":   kospi_chg  or "—",
        "nasdaq_chg":  nasdaq_chg or "—",
        "sp_chg":      sp_chg     or "—",
        "wti_chg":     wti_chg    or "—",
        "gold_chg":    gold_chg   or "—",
        "copper_chg":  copper_chg or "—",
        "summary":     summary,
        "keywords":    keywords,
    }


def _trio_html(kr, us, co, cls_kr, cls_us, cls_co):
    return (f'🇰🇷 <span class="{cls_kr}">{kr}</span> &nbsp;'
            f'🇺🇸 <span class="{cls_us}">{us}</span> &nbsp;'
            f'🛢️ <span class="{cls_co}">{co}</span>')


def _cls(v):
    if not v or v == "—": return "nt"
    return "up" if "+" in v else "dn"


def _kw_tags_html(keywords, cls):
    if not keywords:
        return ""
    tags = "".join(f'<span class="{cls}">{k}</span>' for k in keywords)
    return f'<div class="kw-row">{tags}</div>'


def build_card(meta, featured=False):
    kw_f = _kw_tags_html(meta["keywords"], "fb-tag")
    kw_c = _kw_tags_html(meta["keywords"], "cb-tag")

    kr, us, co = meta["kospi_chg"], meta["nasdaq_chg"], meta["wti_chg"]
    sp = meta["sp_chg"]

    # 탭별 썸네일 배경
    def thumb_for(chg):
        if not chg or chg == "—": return "mix-bg"
        return "up-bg" if "+" in chg else "dn-bg"

    all_thumb = meta["thumb_class"]
    kr_thumb  = thumb_for(kr)
    us_thumb  = thumb_for(us)
    co_thumb  = "co-up" if co and "+" in co else ("co-dn" if co and "-" in co else "mix-bg")

    # 탭별 크게 보여줄 수치
    all_big = f"{meta['best_name']} {meta['best_val']}"
    kr_big  = f"KOSPI {kr}"
    us_big  = f"나스닥 {us}"
    co_big  = f"WTI {co}"

    # 탭별 trio
    trio_all = _trio_html(kr, us, co, _cls(kr), _cls(us), _cls(co))
    trio_kr  = _trio_html(kr, meta.get("kosdaq_chg","—"), sp, _cls(kr), _cls(meta.get("kosdaq_chg","—")), _cls(sp))
    trio_us  = _trio_html(us, sp, meta.get("gold_chg","—"), _cls(us), _cls(sp), _cls(meta.get("gold_chg","—")))
    trio_co  = _trio_html(co, meta.get("gold_chg","—"), meta.get("copper_chg","—"),
                          _cls(co), _cls(meta.get("gold_chg","—")), _cls(meta.get("copper_chg","—")))

    # 탭별 레이블
    lbl_all = f"📅 {meta['rtype_label']} · {meta['date_label']} {meta['weekday']}요일"
    lbl_kr  = f"🇰🇷 한국 시황 · {meta['date_label']} {meta['weekday']}요일"
    lbl_us  = f"🇺🇸 미국 시황 · {meta['date_label']} {meta['weekday']}요일"
    lbl_co  = f"🪨 원자재 시황 · {meta['date_label']} {meta['weekday']}요일"

    if featured:
        return f"""
  <a href="{meta['fname']}" class="featured-card" data-type="{meta['rtype']}">
    <div class="ft {all_thumb}" data-base-class="ft"
         data-all-thumb="{all_thumb}" data-kr-thumb="{kr_thumb}"
         data-us-thumb="{us_thumb}"  data-co-thumb="{co_thumb}" data-thumb>
      <div class="ft-type">{meta['rtype_label']} · {meta['date_str']}</div>
      <div class="ft-big-label">최대 변동</div>
      <div class="ft-big {meta['best_class']}" data-base-class="ft-big"
           data-all-big="{all_big}" data-kr-big="{kr_big}"
           data-us-big="{us_big}"   data-co-big="{co_big}" data-big>{all_big}</div>
      <div class="ft-trio" data-all-trio='{trio_all}' data-kr-trio='{trio_kr}'
           data-us-trio='{trio_us}' data-co-trio='{trio_co}' data-trio>{trio_all}</div>
    </div>
    <div class="fb">
      <div>
        <div class="fb-label" data-base-class="fb-label"
             data-all-label="{lbl_all}" data-kr-label="{lbl_kr}"
             data-us-label="{lbl_us}"   data-co-label="{lbl_co}" data-label>{lbl_all}</div>
        <div class="fb-title" data-all-title="{meta['summary'][:50]}"
             data-kr-title="{meta['summary'][:50]}" data-us-title="{meta['summary'][:50]}"
             data-co-title="{meta['summary'][:50]}" data-title>{meta['summary'][:50]}</div>
        <div class="fb-desc" data-all-desc="{meta['summary']}" data-kr-desc="{meta['summary']}"
             data-us-desc="{meta['summary']}" data-co-desc="{meta['summary']}" data-desc>{meta['summary']}</div>
      </div>
      {kw_f}
    </div>
  </a>"""
    else:
        return f"""
    <a href="{meta['fname']}" class="report-card" data-type="{meta['rtype']}">
      <div class="ct {all_thumb}" data-base-class="ct"
           data-all-thumb="{all_thumb}" data-kr-thumb="{kr_thumb}"
           data-us-thumb="{us_thumb}"   data-co-thumb="{co_thumb}" data-thumb>
        <div class="ct-type">{meta['rtype_label']} · {meta['date_str']}</div>
        <div class="ct-big {meta['best_class']}" data-base-class="ct-big"
             data-all-big="{all_big}" data-kr-big="{kr_big}"
             data-us-big="{us_big}"   data-co-big="{co_big}" data-big>{all_big}</div>
        <div class="ct-trio" data-all-trio='{trio_all}' data-kr-trio='{trio_kr}'
             data-us-trio='{trio_us}' data-co-trio='{trio_co}' data-trio>{trio_all}</div>
      </div>
      <div class="cb">
        <div class="cb-date">{meta['date_label']} {meta['weekday']}요일</div>
        <div class="cb-title" data-all-title="{meta['summary'][:45]}"
             data-kr-title="{meta['summary'][:45]}" data-us-title="{meta['summary'][:45]}"
             data-co-title="{meta['summary'][:45]}" data-title>{meta['summary'][:45]}</div>
        {kw_c}
      </div>
    </a>"""
    if not keywords:
        return ""
    tags = "".join(f'<span class="{cls}">{k}</span>' for k in keywords)
    return f'<div class="kw-row">{tags}</div>'


def build_card(meta, featured=False):
    kw_f = _kw_tags_html(meta["keywords"], "fb-tag")
    kw_c = _kw_tags_html(meta["keywords"], "cb-tag")

    if featured:
        return f"""
  <a href="{meta['fname']}" class="featured-card" data-type="{meta['rtype']}">
    <div class="ft {meta['thumb_class']}">
      <div class="ft-type">{meta['rtype_label']} · {meta['date_str']}</div>
      <div class="ft-hero-label">최대 변동</div>
      <div class="ft-hero-val {meta['best_class']}">{meta['best_name']} {meta['best_val']}</div>
      <div class="ft-pair">
        <div class="ft-pair-item">
          <div class="ft-pair-label">🇰🇷 KOSPI</div>
          <div class="ft-pair-val {'up' if '+' in meta['kospi_chg'] else 'dn'}">{meta['kospi_chg']}</div>
        </div>
        <div class="ft-pair-item">
          <div class="ft-pair-label">🇺🇸 나스닥</div>
          <div class="ft-pair-val {'up' if '+' in meta['nasdaq_chg'] else 'dn'}">{meta['nasdaq_chg']}</div>
        </div>
      </div>
    </div>
    <div class="fb">
      <div>
        <div class="fb-label">📅 {meta['rtype_label']} · {meta['date_label']} {meta['weekday']}요일</div>
        <div class="fb-title">{meta['summary'][:50]}</div>
        <div class="fb-summary">{meta['summary']}</div>
      </div>
      {kw_f}
    </div>
  </a>"""
    else:
        return f"""
    <a href="{meta['fname']}" class="report-card" data-type="{meta['rtype']}">
      <div class="ct {meta['thumb_class']}">
        <div class="ct-type">{meta['rtype_label']} · {meta['date_str']}</div>
        <div class="ct-hero-label">최대 변동</div>
        <div class="ct-hero-val {meta['best_class']}">{meta['best_name']} {meta['best_val']}</div>
        <div class="ct-pair">
          <div class="ct-pair-item"><span class="ct-pl">🇰🇷</span><span class="ct-pv {'up' if '+' in meta['kospi_chg'] else 'dn'}">{meta['kospi_chg']}</span></div>
          <div class="ct-pair-item"><span class="ct-pl">🇺🇸</span><span class="ct-pv {'up' if '+' in meta['nasdaq_chg'] else 'dn'}">{meta['nasdaq_chg']}</span></div>
        </div>
      </div>
      <div class="cb">
        <div class="cb-date">{meta['date_label']} {meta['weekday']}요일</div>
        <div class="cb-title">{meta['summary'][:45]}</div>
        {kw_c}
      </div>
    </a>"""


def _trio(a, b, c, ca, cb, cc):
    return (f'🇰🇷 <span class="{ca}">{a}</span> &nbsp;'
            f'🇺🇸 <span class="{cb}">{b}</span> &nbsp;'
            f'🛢️ <span class="{cc}">{c}</span>')


def build_card_data(meta):
    """JS CARD_DATA 객체용 딕셔너리 생성"""
    kr  = meta["kospi_chg"]
    us  = meta["nasdaq_chg"]
    sp  = meta["sp_chg"]
    co  = meta["wti_chg"]
    gld = meta["gold_chg"]
    cop = meta["copper_chg"]
    bb  = meta["best_name"] + " " + meta["best_val"]
    dl  = meta["date_label"] + " " + meta["weekday"] + "요일"

    def tc(v): return "up-bg" if v and "+" in v else ("dn-bg" if v and "-" in v else "mix-bg")
    def sp2(v): return "up" if v and "+" in v else ("dn" if v and "-" in v else "nt")

    return {
        "all": {
            "thumb": tc(meta["kospi_chg"]) if not meta["rtype"] == "weekly" else "wk-bg",
            "big":   bb,
            "label": f"📅 {meta['rtype_label']} · {dl}",
            "trio":  _trio(kr, us, co, sp2(kr), sp2(us), sp2(co)),
        },
        "kr": {
            "thumb": tc(kr),
            "big":   f"KOSPI {kr}",
            "label": f"🇰🇷 한국 시황 · {dl}",
            "trio":  _trio(kr, us, sp, sp2(kr), sp2(us), sp2(sp)),
        },
        "us": {
            "thumb": "up-bg" if us and "+" in us else "dn-bg",
            "big":   f"나스닥 {us}",
            "label": f"🇺🇸 미국 시황 · {dl}",
            "trio":  _trio(us, sp, gld, sp2(us), sp2(sp), sp2(gld)),
        },
        "co": {
            "thumb": "up-bg" if co and "+" in co else "dn-bg",
            "big":   f"WTI {co}",
            "label": f"🪨 원자재 시황 · {dl}",
            "trio":  _trio(co, gld, cop, sp2(co), sp2(gld), sp2(cop)),
        },
    }


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

    metas = [parse_report_meta(r) for r in reports]
    featured_html = build_card(metas[0], featured=True)
    grid_html     = "\n".join(build_card(m) for m in metas[1:])
    fm = metas[0]

    # CARD_DATA JS 객체 생성
    import json
    card_data_js = "const CARD_DATA = " + json.dumps(
        {m["fname"]: build_card_data(m) for m in metas},
        ensure_ascii=False, indent=2
    ) + ";"

    idx = INDEX_FILE.read_text(encoding="utf-8")
    idx = re.sub(r'<!-- FEATURED_START -->.*?<!-- FEATURED_END -->',
                 f'<!-- FEATURED_START -->{featured_html}\n  <!-- FEATURED_END -->',
                 idx, flags=re.DOTALL)
    idx = re.sub(r'<!-- GRID_START -->.*?<!-- GRID_END -->',
                 f'<!-- GRID_START -->\n{grid_html}\n  <!-- GRID_END -->',
                 idx, flags=re.DOTALL)
    idx = re.sub(r'<!-- UPDATE_DATE -->.*?<!-- /UPDATE_DATE -->',
                 f'<!-- UPDATE_DATE -->{fm["date_str"]} 기준<!-- /UPDATE_DATE -->',
                 idx)
    # CARD_DATA 주입
    idx = re.sub(
        r'// <!-- CARD_DATA_START -->.*?// <!-- CARD_DATA_END -->',
        f'// <!-- CARD_DATA_START -->\n{card_data_js}\n// <!-- CARD_DATA_END -->',
        idx, flags=re.DOTALL
    )

    # 스트립 지표 업데이트
    for key, val in [("STRIP_KOSPI", fm["kospi_chg"]),
                     ("STRIP_NASDAQ", fm["nasdaq_chg"]),
                     ("STRIP_SP", fm["sp_chg"]),
                     ("STRIP_WTI", fm["wti_chg"])]:
        idx = re.sub(f'<!-- {key} -->.*?<!-- /{key} -->',
                     f'<!-- {key} -->{val}<!-- /{key} -->', idx)

    INDEX_FILE.write_text(idx, encoding="utf-8")
    print(f"  ✓ index.html 업데이트 완료 ({len(metas)}개 리포트)")


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
    run(["git", "commit", "-m", f"리포트 업데이트: {src.name} ({datetime.today().strftime('%Y-%m-%d')})"])
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
