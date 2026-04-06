import sys, os
sys.path.insert(0, '.')

code = open('upload.py', encoding='utf-8').read()
code = code.split('if __name__')[0]
exec(code)

for f in ['daily_market_20260327.html', 'daily_market_20260330.html',
          'daily_market_20260331.html', 'daily_market_20260401.html',
          'daily_market_20260402.html', 'daily_market_20260403.html']:
    m = parse_report_meta(f)
    print(f"=== {f} ===")
    print(f"  KOSPI:{m['kospi_chg']}  나스닥:{m['nasdaq_chg']}  WTI:{m['wti_chg']}  금:{m['gold_chg']}")
    print(f"  best: {m['best_name']} {m['best_val']}")
