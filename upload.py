"""
글로벌 마켓 데일리 — GitHub Pages 자동 업로드
─────────────────────────────────────────────
사용법:
  python upload.py daily_market_20260402.html

실행하면:
  1. HTML 파일을 market-report 폴더에 복사
  2. index.html 카드 목록 자동 업데이트
  3. git add / commit / push 자동 실행
  4. https://eunsik3451.github.io/market-report 반영

─────────────────────────────────────────────
"""

import sys
import os
import shutil
import subprocess
import re
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────
REPO_DIR   = Path(r"C:\Users\john\Desktop\market-report")
REPORT_DIR = REPO_DIR  # 리포트를 루트에 바로 저장
INDEX_FILE = REPO_DIR / "index.html"

SITE_URL   = "https://eunsik3451.github.io/market-report"
# ──────────────────────────────────────────────────


def run(cmd, cwd=REPO_DIR):
    """git 명령 실행"""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"  ✗ 오류: {result.stderr.strip()}")
        return False
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    return True


def parse_report_meta(filepath):
    """HTML 파일에서 날짜·제목·지표 파싱"""
    html = Path(filepath).read_text(encoding="utf-8")

    # 날짜: 파일명에서 추출 (daily_market_20260402.html)
    fname = Path(filepath).name
    m = re.search(r"(\d{4})(\d{2})(\d{2})", fname)
    if m:
        y, mo, d = m.groups()
        date_str = f"{y}.{mo}.{d}"
        date_label = f"{y}년 {mo}월 {d}일"
    else:
        date_str = datetime.today().strftime("%Y.%m.%d")
        date_label = datetime.today().strftime("%Y년 %m월 %d일")

    # 리포트 타입
    is_weekly = "weekly" in fname.lower()
    rtype = "주간 시황" if is_weekly else "일일 시황"
    weekday_map = {"Monday":"월","Tuesday":"화","Wednesday":"수",
                   "Thursday":"목","Friday":"금","Saturday":"토","Sunday":"일"}
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d")
        weekday = weekday_map.get(dt.strftime("%A"), "")
    except:
        weekday = ""

    # 핵심 지표 — 요약 카드 bullet에서 추출
    kospi_chg = _extract(html, r"KOSPI\s*([\+\-]\d+\.?\d*%)")
    sp_chg    = _extract(html, r"S&amp;P 500\s*([\+\-]\d+\.?\d*%)|S&P 500\s*([\+\-]\d+\.?\d*%)")
    wti_chg   = _extract(html, r"WTI[^\d]*([\+\-]\d+\.?\d*%)")

    # 핵심 요약 첫 bullet 텍스트
    summary_m = re.search(r'class="s-bullets"[^>]*>.*?<li[^>]*>(.*?)</li>', html, re.DOTALL)
    summary_text = ""
    if summary_m:
        raw = summary_m.group(1)
        summary_text = re.sub(r"<[^>]+>", "", raw).strip()[:80]

    # 썸네일 색상: KOSPI 기준
    if kospi_chg and kospi_chg.startswith("+"):
        thumb_class = "daily-up"
        hero_num = kospi_chg
        hero_class = "up"
    elif kospi_chg and kospi_chg.startswith("-"):
        thumb_class = "daily-dn"
        hero_num = kospi_chg
        hero_class = "dn"
    else:
        thumb_class = "daily-mix"
        hero_num = "—"
        hero_class = ""

    if is_weekly:
        thumb_class = "weekly"

    return {
        "fname":       fname,
        "date_str":    date_str,
        "date_label":  date_label,
        "weekday":     weekday,
        "rtype":       rtype,
        "thumb_class": thumb_class,
        "hero_num":    hero_num,
        "hero_class":  hero_class,
        "kospi_chg":   kospi_chg or "—",
        "sp_chg":      sp_chg or "—",
        "wti_chg":     wti_chg or "—",
        "summary":     summary_text,
    }


def _extract(html, pattern):
    m = re.search(pattern, html)
    if m:
        return next((g for g in m.groups() if g), None)
    return None


def build_card(meta, featured=False):
    """카드 HTML 생성"""
    if featured:
        return f"""
  <a href="{meta['fname']}" class="featured-card">
    <div class="featured-thumb {meta['thumb_class']}">
      <div class="thumb-type">{meta['rtype']} · {meta['date_str']}</div>
      <div class="thumb-headline">
        <span class="num {meta['hero_class']}">{meta['hero_num']}</span>
      </div>
      <div class="thumb-metrics">
        <div class="thumb-metric"><span class="flag">🇰🇷</span> KOSPI <span class="val {meta['hero_class']}">{meta['kospi_chg']}</span></div>
        <div class="thumb-metric"><span class="flag">🇺🇸</span> S&amp;P <span class="val">{meta['sp_chg']}</span></div>
        <div class="thumb-metric">🛢️ WTI <span class="val">{meta['wti_chg']}</span></div>
      </div>
    </div>
    <div class="featured-body">
      <div class="featured-label">📅 {meta['rtype']} · {meta['date_label']} {meta['weekday']}요일</div>
      <div class="featured-title">{meta['summary'][:40] if meta['summary'] else meta['date_label'] + ' 시황'}</div>
      <div class="featured-summary">{meta['summary']}</div>
    </div>
  </a>"""
    else:
        return f"""
    <a href="{meta['fname']}" class="report-card">
      <div class="card-thumb {meta['thumb_class']}">
        <div class="thumb-type">{meta['rtype']} · {meta['date_str']}</div>
        <div class="thumb-headline">
          <span class="num {meta['hero_class']}">{meta['hero_num']}</span>
        </div>
        <div class="thumb-metrics">
          <div class="thumb-metric"><span class="flag">🇰🇷</span> KOSPI <span class="val {meta['hero_class']}">{meta['kospi_chg']}</span></div>
          <div class="thumb-metric"><span class="flag">🇺🇸</span> S&amp;P <span class="val">{meta['sp_chg']}</span></div>
        </div>
      </div>
      <div class="card-body">
        <div class="card-date">{meta['date_label']} {meta['weekday']}요일</div>
        <div class="card-title">{meta['summary'][:50] if meta['summary'] else meta['date_label'] + ' 시황'}</div>
      </div>
    </a>"""


def rebuild_index():
    """index.html의 카드 목록을 저장소 내 HTML 파일 기준으로 재구성"""

    # 모든 리포트 파일 수집 (날짜 내림차순)
    reports = sorted(
        [f for f in REPO_DIR.glob("*market*.html") if f.name != "index.html"],
        key=lambda f: f.name,
        reverse=True
    )

    if not reports:
        print("  ℹ️  리포트 파일 없음 — index.html 업데이트 생략")
        return

    metas = [parse_report_meta(r) for r in reports]

    # 최신 1개 → 피처드, 나머지 → 그리드
    featured_html = build_card(metas[0], featured=True)
    grid_html = "\n".join(build_card(m, featured=False) for m in metas[1:])

    # 최신 지표 스트립 (피처드 카드 메타 기준)
    fm = metas[0]

    # index.html 읽기
    idx_text = INDEX_FILE.read_text(encoding="utf-8")

    # 피처드 카드 교체
    idx_text = re.sub(
        r'<!-- FEATURED_START -->.*?<!-- FEATURED_END -->',
        f'<!-- FEATURED_START -->{featured_html}<!-- FEATURED_END -->',
        idx_text, flags=re.DOTALL
    )
    # 그리드 교체
    idx_text = re.sub(
        r'<!-- GRID_START -->.*?<!-- GRID_END -->',
        f'<!-- GRID_START -->\n{grid_html}\n  <!-- GRID_END -->',
        idx_text, flags=re.DOTALL
    )
    # 업데이트 날짜
    idx_text = re.sub(
        r'<!-- UPDATE_DATE -->.*?<!-- /UPDATE_DATE -->',
        f'<!-- UPDATE_DATE -->{fm["date_str"]} 기준<!-- /UPDATE_DATE -->',
        idx_text
    )

    INDEX_FILE.write_text(idx_text, encoding="utf-8")
    print(f"  ✓ index.html 업데이트 완료 ({len(metas)}개 리포트)")


def upload(html_path):
    src = Path(html_path)
    if not src.exists():
        print(f"✗ 파일을 찾을 수 없어요: {html_path}")
        sys.exit(1)

    fname = src.name
    dst   = REPORT_DIR / fname

    print(f"\n📤 업로드 시작: {fname}")
    print(f"   → {REPO_DIR}\n")

    # 1. 파일 복사 (이미 같은 폴더에 있으면 생략)
    if src.resolve() == dst.resolve():
        print(f"  ✓ 파일이 이미 올바른 위치에 있음 (복사 생략)")
    else:
        shutil.copy2(src, dst)
        print(f"  ✓ 파일 복사 완료")

    # 2. index.html 재구성
    rebuild_index()

    # 3. git add
    print("\n  git add...")
    run(["git", "add", "-A"])

    # 4. git commit
    today = datetime.today().strftime("%Y-%m-%d")
    msg   = f"리포트 업데이트: {fname} ({today})"
    print(f"  git commit: {msg}")
    run(["git", "commit", "-m", msg])

    # 5. git push
    print("  git push...")
    ok = run(["git", "push", "origin", "main"])

    if ok:
        print(f"\n🎉 업로드 완료!")
        print(f"   🌐 {SITE_URL}")
        print(f"   (반영까지 1~2분 소요)\n")
    else:
        print("\n✗ push 실패 — GitHub 인증 필요할 수 있어요")
        print("  아래 명령어로 수동 push 해보세요:")
        print("  git push origin main\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python upload.py <HTML파일경로>")
        print("예시:   python upload.py daily_market_20260402.html")
        sys.exit(1)
    upload(sys.argv[1])
