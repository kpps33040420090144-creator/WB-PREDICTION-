"""
fetch_paito_teks.py — Convert result.json → paito-data.json
TANPA scraping. Ambil data dari result.json (output fetch_all.py).

Format paito-data.json:
{
  "slug": {
    "name": "Singapore",
    "start_date": "2026-01-01",   ← tanggal result[0] (paling lama)
    "results": ["1234", "5678"],  ← urut LAMA→BARU
    "skip_weekdays": [1, 4],
    "count": 150,
    "updated": "2026-06-06 17:00 WIB"
  }
}
"""

import json
import os
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
NOW = datetime.now(WIB)

INPUT_FILE  = 'result.json'
OUTPUT_FILE = 'paito-data.json'

# ===== MAP: slug rumusangkanet → key result.json =====
# (slug paito-data.json → key fetch_all.py PASARAN)
SLUG_MAP = {
    'hongkong-pools':              'hk',
    'hklotto':                     'hkl',
    'singapore':                   'sgp',
    'sydney-pools':                'sdy',
    'sdlotto':                     'sdl',
    'magnum-cambodia':             'kam',
    'bullseye':                    'bull',
    'chinapools':                  'chn',
    'japan':                       'jpn',
    'taiwan':                      'twn',
    'pcso':                        'pcso',
    'toto-macau-1':                'mac1',
    'toto-macau-2':                'mac2',
    'toto-macau-3':                'mac3',
    'toto-macau-4':                'mac4',
    'toto-macau-5':                'mac5',
    'toto-macau-6':                'mac6',
    'morocco-quatro-03-00-wib':    'mrq3',
    'morocco-quatro-18-00-wib':    'mrq18',
    'morocco-quatro-21-00-wib':    'mrq21',
    'morocco-quatro-23-59-wib':    'mrq23',
    'germany-plus5':               'ger',
    'oregon-04-00-wib':            'or4',
    'oregon-07-00-wib':            'or7',
    'oregon-10-00-wib':            'or10',
    'oregon-13-00-wib':            'or13',
    'north-carolina-day':          'ncd',
    'north-carolina-evening':      'nce',
    'georgia-midday':              'geom',
    'georgia-evening':             'geoe',
    'georgia-night':               'geon',
    'texas-day':                   'txd',
    'texas-morning':               'txmr',
    'texas-evening':               'txe',
    'texas-night':                 'txn',
    'new-york-midday':             'nyd',
    'new-york-evening':            'nye',
    'new-jersey-midday':           'njm',
    'new-jersey-evening':          'nje',
    'florida-midday':              'flm',
    'florida-evening':             'fle',
    'illinois-midday':             'ilm',
    'illinois-evening':            'ile',
    'indiana-midday':              'indm',
    'indiana-evening':             'inde',
    'kentucky-midday':             'kym',
    'kentucky-evening':            'kye',
    'maryland-midday':             'mdm',
    'maryland-evening':            'mde',
    'michigan-midday':             'mim',
    'michigan-evening':            'mie',
    'missouri-midday':             'mom',
    'missouri-evening':            'moe',
    'washington-dc-midday':        'wdm',
    'washington-dc-evening':       'wde',
    'connecticut-day':             'ctd',
    'connecticut-night':           'ctn',
    'virginia-day':                'vad',
    'virginia-night':              'van',
    'tennesse-midday':             'tnm',
    'tennesse-evening':            'tne',
    'tennesse-morning':            'tnmr',
    'california':                  'cal',
    'wisconsin-evening':           'wie',
}

# Nama display per slug
SLUG_NAMES = {
    'hongkong-pools':           'Hongkong Pools',
    'hklotto':                  'Hongkong Lotto',
    'singapore':                'Singapore',
    'sydney-pools':             'Sydney Pools',
    'sdlotto':                  'Sydney Lotto',
    'magnum-cambodia':          'Kamboja',
    'bullseye':                 'Bullseye NZ',
    'chinapools':               'China Pools',
    'japan':                    'Japan',
    'taiwan':                   'Taiwan',
    'pcso':                     'PCSO',
    'toto-macau-1':             'Toto Macau 13',
    'toto-macau-2':             'Toto Macau 16',
    'toto-macau-3':             'Toto Macau 19',
    'toto-macau-4':             'Toto Macau 22',
    'toto-macau-5':             'Toto Macau 00',
    'toto-macau-6':             'Toto Macau 23',
    'morocco-quatro-03-00-wib': 'Morocco 03:00',
    'morocco-quatro-18-00-wib': 'Morocco 18:00',
    'morocco-quatro-21-00-wib': 'Morocco 21:00',
    'morocco-quatro-23-59-wib': 'Morocco 23:59',
    'germany-plus5':            'Germany Plus5',
    'oregon-04-00-wib':         'Oregon 04:00',
    'oregon-07-00-wib':         'Oregon 07:00',
    'oregon-10-00-wib':         'Oregon 10:00',
    'oregon-13-00-wib':         'Oregon 13:00',
    'north-carolina-day':       'NC Day',
    'north-carolina-evening':   'NC Evening',
    'georgia-midday':           'Georgia Midday',
    'georgia-evening':          'Georgia Evening',
    'georgia-night':            'Georgia Night',
    'texas-day':                'Texas Day',
    'texas-morning':            'Texas Morning',
    'texas-evening':            'Texas Evening',
    'texas-night':              'Texas Night',
    'new-york-midday':          'New York Midday',
    'new-york-evening':         'New York Evening',
    'new-jersey-midday':        'NJ Midday',
    'new-jersey-evening':       'NJ Evening',
    'florida-midday':           'Florida Midday',
    'florida-evening':          'Florida Evening',
    'illinois-midday':          'Illinois Midday',
    'illinois-evening':         'Illinois Evening',
    'indiana-midday':           'Indiana Midday',
    'indiana-evening':          'Indiana Evening',
    'kentucky-midday':          'Kentucky Midday',
    'kentucky-evening':         'Kentucky Evening',
    'maryland-midday':          'Maryland Midday',
    'maryland-evening':         'Maryland Evening',
    'michigan-midday':          'Michigan Midday',
    'michigan-evening':         'Michigan Evening',
    'missouri-midday':          'Missouri Midday',
    'missouri-evening':         'Missouri Evening',
    'washington-dc-midday':     'WDC Midday',
    'washington-dc-evening':    'WDC Evening',
    'connecticut-day':          'Connecticut Day',
    'connecticut-night':        'Connecticut Night',
    'virginia-day':             'Virginia Day',
    'virginia-night':           'Virginia Night',
    'tennesse-midday':          'Tennessee Midday',
    'tennesse-evening':         'Tennessee Evening',
    'tennesse-morning':         'Tennessee Morning',
    'california':               'California',
    'wisconsin-evening':        'Wisconsin Evening',
}

# Hari libur per slug (Python weekday: 0=Sen,1=Sel,2=Rab,3=Kam,4=Jum,5=Sab,6=Min)
SKIP_WEEKDAYS = {
    'singapore':      [1, 4],
    'hongkong-pools': [0],
    'hklotto':        [0],
    'bullseye':       [0, 1, 2, 3, 4],
    'pcso':           [0, 3],
}


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  [WARN] Gagal baca {path}: {e}")
    return {}


def history_to_results(history):
    """
    Ubah list history result.json → list angka urut LAMA→BARU.
    history format: [{"date":"2026-06-06","result":"1234"}, ...]  (urut BARU→LAMA)
    Output: ["xxxx", "xxxx", ...]  urut LAMA→BARU
    """
    # Filter valid 4 digit saja
    valid = [
        h for h in history
        if h.get('result') and len(str(h['result'])) == 4
        and str(h['result']).isdigit()
    ]
    # Sort ascending (LAMA→BARU)
    valid.sort(key=lambda h: h.get('date', ''), reverse=False)
    return [h['result'] for h in valid]


def main():
    SEP = '=' * 60
    print(f"\n{SEP}")
    print(f"fetch_paito_teks.py — {NOW.strftime('%A, %d %B %Y %H:%M WIB')}")
    print(f"Mode: CONVERTER result.json → paito-data.json")
    print(f"{SEP}\n")

    # Load input
    result_json = load_json(INPUT_FILE)
    if not result_json:
        print(f"ERROR: {INPUT_FILE} tidak ditemukan atau kosong!")
        print("Pastikan fetch_all.py sudah jalan duluan.")
        return

    # Load paito-data.json lama (untuk pertahankan start_date)
    old_db = load_json(OUTPUT_FILE)
    print(f"result.json   : {len([k for k in result_json if not k.startswith('_')])} pasaran")
    print(f"paito-data lama: {len([k for k in old_db if not k.startswith('_')])} pasaran\n")

    new_db = {}
    ok_count   = 0
    skip_count = 0

    for slug, rkey in SLUG_MAP.items():
        entry = result_json.get(rkey)
        if not entry:
            print(f"  [{slug[:25]:25s}] SKIP — key '{rkey}' tidak ada di result.json")
            skip_count += 1
            continue

        history = entry.get('history', [])
        if not history:
            print(f"  [{slug[:25]:25s}] SKIP — history kosong")
            skip_count += 1
            continue

        results = history_to_results(history)
        if not results:
            print(f"  [{slug[:25]:25s}] SKIP — tidak ada angka valid di history")
            skip_count += 1
            continue

        # start_date: pakai dari old_db kalau sudah ada (jangan ubah!)
        old_entry  = old_db.get(slug, {})
        start_date = old_entry.get('start_date') or results[0]  # fallback: angka pertama

        # Ambil start_date dari history yang sudah di-sort
        valid_hist = [
            h for h in history
            if h.get('result') and len(str(h['result'])) == 4
            and str(h['result']).isdigit()
        ]
        valid_hist.sort(key=lambda h: h.get('date', ''))
        if valid_hist and not old_entry.get('start_date'):
            start_date = valid_hist[0].get('date', '')

        # Merge dengan old results — pertahankan historis lama
        old_results = old_entry.get('results', [])
        if old_results:
            # Gabung: old sebagai base, new sebagai update terbaru
            old_set = set(old_results[-300:])
            extra   = [r for r in results if r not in old_set]
            merged  = old_results + extra
        else:
            merged = results

        new_db[slug] = {
            'name':          SLUG_NAMES.get(slug, slug),
            'start_date':    start_date,
            'skip_weekdays': SKIP_WEEKDAYS.get(slug, []),
            'results':       merged,
            'count':         len(merged),
            'updated':       NOW.strftime('%Y-%m-%d %H:%M WIB'),
        }
        ok_count += 1
        added = len(merged) - len(old_results)
        print(f"  [{slug[:25]:25s}] {len(merged):3d} hasil (+{added})")

    new_db['_meta'] = {
        'updated':     NOW.strftime('%Y-%m-%d %H:%M WIB'),
        'total_slugs': len(SLUG_MAP),
        'ok':          ok_count,
        'skip':        skip_count,
        'source':      'result.json (fetch_all.py)',
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_db, f, separators=(',', ':'), ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\n{SEP}")
    print(f"paito-data.json tersimpan  ({size_kb:.1f} KB)")
    print(f"OK: {ok_count}  |  SKIP: {skip_count}  |  Total: {len(SLUG_MAP)}")
    print(f"{SEP}\n")


if __name__ == '__main__':
    main()
