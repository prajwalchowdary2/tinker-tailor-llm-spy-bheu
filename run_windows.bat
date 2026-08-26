@echo off
title Tinker Tailor — LLM Chat Recovery
echo ============================================
echo   Tinker Tailor LLM Spy - Windows Scanner
echo ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ and add to PATH.
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create results folder
if not exist "results_windows" mkdir results_windows

echo [1/3] Running full scan across all Chrome + Edge profiles...
echo.
python -m tinker_tailor.cli --scan --dlp --sign --output results_windows\evidence.json
echo.

echo [2/3] Capturing timing benchmarks...
echo.
python -c "import time,json,os;from tinker_tailor.carver.browser_paths import get_forensic_paths;from tinker_tailor.carver.engine import carve_leveldb_directory;paths=get_forensic_paths();idb={k:v for k,v in paths.get('indexeddb',{}).items() if os.path.exists(v)};print(f'Found {len(idb)} active IndexedDB directories');start=time.perf_counter();tp=0;rows=[];[((p_,c_):=(carve_leveldb_directory(v,k.split('_')[0],[])),tp:=tp+len(p_),print(f'  {k}: {len(p_)} prompts, {len(c_)} convs'),rows.append(f'{k},{len(p_)},{len(c_)}')) for k,v in idb.items()];elapsed=(time.perf_counter()-start)*1000;print(f'\nTotal: {tp} prompts in {elapsed:.1f}ms across {len(idb)} directories');open('results_windows/timing.txt','w').write(f'prompts={tp}\ndirectories={len(idb)}\ntime_ms={elapsed:.1f}\n')" 2>nul

:: Simpler fallback if the one-liner fails
if errorlevel 1 (
    echo Running timing with fallback script...
    python -c "import time,json,os;from tinker_tailor.carver.browser_paths import get_forensic_paths;from tinker_tailor.carver.engine import carve_leveldb_directory;paths=get_forensic_paths();idb={k:v for k,v in paths.get('indexeddb',{}).items() if os.path.exists(v)};print(f'Found {len(idb)} dirs');start=time.perf_counter();tp=0;[exec('p,c=carve_leveldb_directory(v,k.split(chr(95))[0],[]);tp+=len(p);print(f\"  {k}: {len(p)} prompts\")') for k,v in idb.items()];elapsed=(time.perf_counter()-start)*1000;print(f'Total: {tp} prompts in {elapsed:.1f}ms')"
)

echo.
echo [3/3] Generating summary...
echo.
python -c "import json,os,platform;e=json.load(open('results_windows/evidence.json'));s=e.get('stats',{});d=e.get('dlp',{});print(f'OS:        {platform.platform()}');print(f'Chrome:    (check chrome://version)');print(f'Prompts:   {s.get(\"total_prompts\",0)}');print(f'Convos:    {s.get(\"total_conversations\",0)}');print(f'DLP creds: {d.get(\"credentials\",\"N/A\")}');print(f'DLP PII:   {d.get(\"pii\",\"N/A\")}');bots={};[bots.update({p.get('bot','?'):bots.get(p.get('bot','?'),0)+1}) for p in e.get('prompts',[])];print(f'By bot:    {bots}');t=open('results_windows/timing.txt').read() if os.path.exists('results_windows/timing.txt') else 'no timing';print(f'Timing:    {t.strip()}')"

echo.
echo ============================================
echo   Done! Results saved to results_windows\
echo     - evidence.json   (full recovery data)
echo     - timing.txt      (benchmark numbers)
echo ============================================
echo.
echo Copy the results_windows folder back to your
echo Mac to use with the paper evaluation scripts.
echo.
pause
