"""
fetch_all.py — Fetch 65 pasaran togel dari angkanet.com
Simpan ke result.json, dibaca langsung oleh index.html
v3: history otomatis backfill dari semua baris di halaman pasaran
    - extract_all_rows() ambil semua baris tanpa request tambahan
    - backfill pass setelah loop utama untuk pasaran dari paito-harian
"""

import requests
import json
import re
import time
import urllib3
urllib3.disable_warnings()
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ===== TIMEZONE =====
WIB = timezone(timedelta(hours=7))
NOW = datetime.now(WIB)
TODAY = NOW.strftime('%d/%m')

BASE      = 'https://angkanet18.com'
DIRECT_IP = '159.65.133.131'

HISTORY_MAX = 150  # simpan max 150 hari per pasaran (butuh ~14 minggu untuk trek mingguan)

# ===== DAFTAR 65 PASARAN =====
PASARAN = {
    'hk':   ('/data-pengeluaran-togel-hongkong-pools/', 'Hongkong Pools'),
    'hkl':  ('/data-pengeluaran-togel-hklotto/',        'Hongkong Lotto'),
    'sgp':  ('/data-pengeluaran-togel-singapore/',      'Singapore'),
    'sdy':  ('/data-pengeluaran-togel-sydney-pools/',   'Sydney Pools'),
    'sdl':  ('/data-pengeluaran-togel-sdlotto/',        'Sydney Lotto'),
    'kam':  ('/data-pengeluaran-togel-magnum-cambodia/','Kamboja'),
    'bull': ('/data-pengeluaran-togel-bullseye/',       'Bullseye NZ'),
    'chn':  ('/data-pengeluaran-togel-chinapools/',     'China Pools'),
    'jpn':  ('/data-pengeluaran-togel-japan/',          'Japan'),
    'twn':  ('/data-pengeluaran-togel-taiwan/',         'Taiwan'),
    'pcso': ('/data-pengeluaran-togel-pcso/',           'PCSO'),
    'mac1': ('/data-pengeluaran-togel-toto-macau-1/',   'Toto Macau 13'),
    'mac2': ('/data-pengeluaran-togel-toto-macau-2/',   'Toto Macau 16'),
    'mac3': ('/data-pengeluaran-togel-toto-macau-3/',   'Toto Macau 19'),
    'mac4': ('/data-pengeluaran-togel-toto-macau-4/',   'Toto Macau 22'),
    'mac5': ('/data-pengeluaran-togel-toto-macau-5/',   'Toto Macau 00'),
    'mac6': ('/data-pengeluaran-togel-toto-macau-6/',   'Toto Macau 23'),
    'mrq3':  ('/data-pengeluaran-togel-morocco-quatro-03-00-wib/', 'Morocco 03:00'),
    'mrq18': ('/data-pengeluaran-togel-morocco-quatro-18-00-wib/', 'Morocco 18:00'),
    'mrq21': ('/data-pengeluaran-togel-morocco-quatro-21-00-wib/', 'Morocco 21:00'),
    'mrq23': ('/data-pengeluaran-togel-morocco-quatro-23-59-wib/', 'Morocco 23:59'),
    'ger':  ('/data-pengeluaran-togel-germany-plus5/', 'Germany Plus5'),
    'or4':  ('/data-pengeluaran-togel-oregon-04-00-wib/', 'Oregon 04:00'),
    'or7':  ('/data-pengeluaran-togel-oregon-07-00-wib/', 'Oregon 07:00'),
    'or10': ('/data-pengeluaran-togel-oregon-10-00-wib/', 'Oregon 10:00'),
    'or13': ('/data-pengeluaran-togel-oregon-13-00-wib/', 'Oregon 13:00'),
    'ncd':  ('/data-pengeluaran-togel-north-carolina-day/',     'NC Day'),
    'nce':  ('/data-pengeluaran-togel-north-carolina-evening/', 'NC Evening'),
    'geom': ('/data-pengeluaran-togel-georgia-midday/',  'Georgia Midday'),
    'geoe': ('/data-pengeluaran-togel-georgia-evening/', 'Georgia Evening'),
    'geon': ('/data-pengeluaran-togel-georgia-night/',   'Georgia Night'),
    'txd':  ('/data-pengeluaran-togel-texas-day/',     'Texas Day'),
    'txmr': ('/data-pengeluaran-togel-texas-morning/', 'Texas Morning'),
    'txe':  ('/data-pengeluaran-togel-texas-evening/', 'Texas Evening'),
    'txn':  ('/data-pengeluaran-togel-texas-night/',   'Texas Night'),
    'nyd':  ('/data-pengeluaran-togel-new-york-midday/',  'New York Midday'),
    'nye':  ('/data-pengeluaran-togel-new-york-evening/', 'New York Evening'),
    'njm':  ('/data-pengeluaran-togel-new-jersey-midday/',  'NJ Midday'),
    'nje':  ('/data-pengeluaran-togel-new-jersey-evening/', 'NJ Evening'),
    'flm':  ('/data-pengeluaran-togel-florida-midday/',  'Florida Midday'),
    'fle':  ('/data-pengeluaran-togel-florida-evening/', 'Florida Evening'),
    'ilm':  ('/data-pengeluaran-togel-illinois-midday/',  'Illinois Midday'),
    'ile':  ('/data-pengeluaran-togel-illinois-evening/', 'Illinois Evening'),
    'indm': ('/data-pengeluaran-togel-indiana-midday/',  'Indiana Midday'),
    'inde': ('/data-pengeluaran-togel-indiana-evening/', 'Indiana Evening'),
    'kym':  ('/data-pengeluaran-togel-kentucky-midday/',  'Kentucky Midday'),
    'kye':  ('/data-pengeluaran-togel-kentucky-evening/', 'Kentucky Evening'),
    'mdm':  ('/data-pengeluaran-togel-maryland-midday/',  'Maryland Midday'),
    'mde':  ('/data-pengeluaran-togel-maryland-evening/', 'Maryland Evening'),
    'mim':  ('/data-pengeluaran-togel-michigan-midday/',  'Michigan Midday'),
    'mie':  ('/data-pengeluaran-togel-michigan-evening/', 'Michigan Evening'),
    'mom':  ('/data-pengeluaran-togel-missouri-midday/',  'Missouri Midday'),
    'moe':  ('/data-pengeluaran-togel-missouri-evening/', 'Missouri Evening'),
    'wdm':  ('/data-pengeluaran-togel-washington-dc-midday/',  'WDC Midday'),
    'wde':  ('/data-pengeluaran-togel-washington-dc-evening/', 'WDC Evening'),
    'ctd':  ('/data-pengeluaran-togel-connecticut-day/',   'Connecticut Day'),
    'ctn':  ('/data-pengeluaran-togel-connecticut-night/', 'Connecticut Night'),
    'vad':  ('/data-pengeluaran-togel-virginia-day/',   'Virginia Day'),
    'van':  ('/data-pengeluaran-togel-virginia-night/', 'Virginia Night'),
    'tnm':  ('/data-pengeluaran-togel-tennesse-midday/',  'Tennessee Midday'),
    'tne':  ('/data-pengeluaran-togel-tennesse-evening/', 'Tennessee Evening'),
    'tnmr': ('/data-pengeluaran-togel-tennesse-morning/', 'Tennessee Morning'),
    'cal':  ('/data-pengeluaran-togel-california/',        'California'),
    'wie':  ('/data-pengeluaran-togel-wisconsin-evening/', 'Wisconsin Evening'),
}

PASARAN_MALAM = {'mrq23', 'mac6', 'txn', 'geon', 'ctn', 'van', 'tne'}

# Pasaran mingguan: result hanya keluar pada hari tertentu saja.
# Untuk pasaran ini, Strategy F (offset harian) DILARANG dipakai
# karena akan menggeser history jika ada hari yang terlewat.
# Pasaran ini WAJIB fetch individual agar tanggal akurat dari HTML.
PASARAN_MINGGUAN = {'hk', 'hkl', 'sgp', 'bull', 'pcso'}

# Hari libur per pasaran (0=Sen,1=Sel,2=Rab,3=Kam,4=Jum,5=Sab,6=Min)
PASARAN_LIBUR = {
    'sgp':  {1, 4},   # libur Selasa & Jumat
    # Pasaran libur Minggu:
    'pcso': {6}, 'mac5': {6}, 'mrq3': {6}, 'mrq23': {6},
    'ger':  {6}, 'or4':  {6}, 'or7':  {6}, 'ncd':   {6},
    'geom': {6}, 'txd':  {6}, 'txmr': {6}, 'txe':   {6},
    'nyd':  {6}, 'flm':  {6}, 'fle':  {6}, 'ilm':   {6},
    'ile':  {6}, 'indm': {6}, 'inde': {6}, 'kym':   {6},
    'kye':  {6}, 'mie':  {6}, 'mom':  {6}, 'wdm':   {6},
    'ctd':  {6}, 'ctn':  {6}, 'vad':  {6}, 'van':   {6},
    'tnm':  {6}, 'tne':  {6}, 'tnmr': {6}, 'nce':   {6},
    'ncm':  {6}, 'wim':  {6}, 'wie':  {6}, 'cal':   {6},
    'gam':  {6}, 'gae':  {6}, 'mam':  {6}, 'mae':   {6},
    'nvm':  {6}, 'nve':  {6},
    'mdm':  {6}, 'mde':  {6}, 'mim':  {6}, 'moe':  {6}, 'wde':  {6},
}

TODAY_TUPLE = (NOW.year, NOW.month, NOW.day)
TODAY_STR   = f"{TODAY_TUPLE[0]:04d}-{TODAY_TUPLE[1]:02d}-{TODAY_TUPLE[2]:02d}"

# ===== MANUAL OVERRIDE =====
MANUAL_OVERRIDE = {
    # 'sdl': '1864',
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
}

FAKE_PATTERNS = [
    r'^1234$', r'^2345$', r'^3456$', r'^4567$', r'^5678$',
    r'^6789$', r'^7890$', r'^8901$', r'^9012$', r'^0123$',
    r'^(\d)\1{3}$',
]

def is_year(result):
    # Hanya filter tahun yang sangat jelas (sekitar tahun sekarang ±5)
    # Jangan filter terlalu lebar karena 1800-2099 banyak overlap dengan result togel valid
    try:
        n = int(result)
        current_year = NOW.year
        return (current_year - 2) <= n <= (current_year + 1)
    except Exception:
        return False

def is_fake(result):
    if not result or not re.match(r'^\d{4}$', result):
        return True
    if is_year(result):
        return True
    return any(re.match(p, result) for p in FAKE_PATTERNS)


# ===== HISTORY HELPER =====
def update_history(old_data: dict, new_result: str, date_str: str) -> list:
    """
    Merge result baru ke history list.
    - Kalau tanggal sudah ada → update result di tanggal itu.
    - Kalau tanggal baru → prepend.
    - Potong max HISTORY_MAX entry.
    Kembalikan list history terbaru.
    """
    history = old_data.get('history', [])

    # Cari apakah date_str sudah ada
    existing_idx = next(
        (i for i, h in enumerate(history) if h.get('date') == date_str),
        None
    )

    if existing_idx is not None:
        history[existing_idx] = {'date': date_str, 'result': new_result}
    else:
        history = [{'date': date_str, 'result': new_result}] + history

    # Sort descending tanggal, potong 30
    history.sort(key=lambda h: h.get('date', ''), reverse=True)
    return history[:HISTORY_MAX]


# ===== EKSTRAK SEMUA BARIS HISTORIS DARI HTML =====
def detect_active_weekdays(history: list) -> set:
    """
    Dari history yang sudah punya tanggal akurat (paito-harian),
    deteksi hari-hari aktif pasaran (0=Mon...6=Sun Python weekday).
    Minimal 3 data agar pola terdeteksi.
    """
    import datetime as _dt_wd
    if len(history) < 3:
        return set()
    weekday_count = {}
    for h in history:
        try:
            d = _dt_wd.date.fromisoformat(h['date'])
            wd = d.weekday()
            weekday_count[wd] = weekday_count.get(wd, 0) + 1
        except Exception:
            continue
    if not weekday_count:
        return set()
    # Ambil hari yang muncul minimal 30% dari total entry (filter noise)
    threshold = max(1, len(history) * 0.3 / 7)
    active = {wd for wd, cnt in weekday_count.items() if cnt >= threshold}
    return active


def extract_all_rows(html, anchor_date=None, active_weekdays=None, libur_days=None):
    """
    Ambil SEMUA baris valid (tanggal + result) dari HTML satu halaman pasaran.
    Return: [{'date': 'YYYY-MM-DD', 'result': '1234'}, ...]  descending tanggal.
    Dipakai untuk backfill history tanpa request tambahan.
    """
    if not html or len(html) < 200:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    date_pat = re.compile(
        r'^(?:(\d{2})[/-](\d{2})[/-](\d{4})|(\d{4})[/-](\d{2})[/-](\d{2}))$'
    )
    ddmm_pat = re.compile(r'^(\d{1,2})[/-](\d{1,2})$')

    def parse_date(text):
        m = date_pat.match(text)
        if m:
            if m.group(1):
                return (int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return (int(m.group(4)), int(m.group(5)), int(m.group(6)))
        # Support DD/MM tanpa tahun (format umum di angkanet)
        m2 = ddmm_pat.match(text)
        if m2:
            dd, mm = int(m2.group(1)), int(m2.group(2))
            if 1 <= dd <= 31 and 1 <= mm <= 12:
                year = NOW.year
                # Kalau bulan/hari di depan hari ini → tahun lalu
                if (mm, dd) > (NOW.month, NOW.day):
                    year -= 1
                return (year, mm, dd)
        return None

    today_ord = NOW.toordinal()

    def is_recent(d_tuple, max_days=150):
        """Hanya terima tanggal max_days hari ke belakang, tolak yg jadul."""
        try:
            import datetime as _dt
            d_ord = _dt.date(d_tuple[0], d_tuple[1], d_tuple[2]).toordinal()
            return 0 <= (today_ord - d_ord) <= max_days
        except Exception:
            return False

    # ── Strategy A: paito-line sebagai row container (struktur baru) ──
    # Tanggal ada di elemen .column1 / .tampil, result di .paito-row-item
    seen_dates: set = set()
    rows_A = []
    for line in soup.find_all(class_='paito-line'):
        date_found = None
        result_found = None
        for el in line.find_all(True):
            t = el.get_text(strip=True)
            if date_found is None:
                d = parse_date(t)
                if d:
                    date_found = d
            if result_found is None and re.match(r'^\d{4}$', t) and not is_fake(t):
                result_found = t
            if date_found and result_found:
                break
        if date_found and result_found and is_recent(date_found):
            ds = f"{date_found[0]:04d}-{date_found[1]:02d}-{date_found[2]:02d}"
            if ds not in seen_dates:
                seen_dates.add(ds)
                rows_A.append({'date': ds, 'result': result_found})

    if rows_A:
        rows_A.sort(key=lambda x: x['date'], reverse=True)
        return rows_A[:HISTORY_MAX]

    # ── Strategy B: paito-row-item grouping by parent (struktur lama) ──
    all_items = soup.find_all(class_='paito-row-item')
    row_map = {}
    for item in all_items:
        row_el = item.parent
        rid = id(row_el)
        if rid not in row_map:
            row_map[rid] = {'date': None, 'result': None}
        text = item.get_text(strip=True)
        if row_map[rid]['date'] is None:
            d = parse_date(text)
            if d:
                row_map[rid]['date'] = d
        if row_map[rid]['result'] is None:
            if re.match(r'^\d{4}$', text) and not is_fake(text):
                row_map[rid]['result'] = text

    rows_B = [
        r for r in row_map.values()
        if r['date'] is not None and r['result'] is not None
    ]
    if rows_B:
        rows_B.sort(key=lambda x: x['date'], reverse=True)
        return [
            {'date': f"{r['date'][0]:04d}-{r['date'][1]:02d}-{r['date'][2]:02d}",
             'result': r['result']}
            for r in rows_B[:HISTORY_MAX]
        ]

    # ── Strategy C: scan tabel/list biasa ──
    seen_dates2: set = set()
    rows_C = []
    for tr in soup.find_all(['tr', 'li']):
        cells = tr.find_all(['td', 'span', 'div', 'b'])
        date_found = result_found = None
        for c in cells:
            t = c.get_text(strip=True)
            if date_found is None:
                date_found = parse_date(t)
            if result_found is None and re.match(r'^\d{4}$', t) and not is_fake(t):
                result_found = t
        if date_found and result_found and is_recent(date_found):
            ds = f"{date_found[0]:04d}-{date_found[1]:02d}-{date_found[2]:02d}"
            if ds not in seen_dates2:
                seen_dates2.add(ds)
                rows_C.append({'date': ds, 'result': result_found})

    if rows_C:
        rows_C.sort(key=lambda x: x['date'], reverse=True)
        return rows_C[:HISTORY_MAX]

    # ── Strategy D: pasangkan .paito-line ke tanggal terdekat di DOM ──
    # Berguna jika tanggal ada di sibling/ancestor, bukan di dalam .paito-line itu sendiri
    lines_d = soup.find_all(class_='paito-line')
    if lines_d:
        # Kumpulkan semua elemen DOM secara berurutan
        all_els    = list(soup.descendants)
        el_pos     = {id(el): i for i, el in enumerate(all_els)}

        # Kumpulkan semua posisi elemen yang berisi tanggal valid (teks pendek saja)
        # Hanya tanggal recent (max 150 hari), abaikan tanggal jadul dari meta/script
        date_pos_list = []
        for el in all_els:
            if not hasattr(el, 'get_text'):
                continue
            t = el.get_text(strip=True)
            if len(t) > 12:
                continue
            d = parse_date(t)
            if d and is_recent(d):
                date_pos_list.append((el_pos[id(el)], d))

        seen_dates3: set = set()
        rows_D = []
        for line in lines_d:
            result_found = None
            for item in line.find_all(class_='paito-row-item'):
                t = item.get_text(strip=True)
                if re.match(r'^\d{4}$', t) and not is_fake(t):
                    result_found = t
                    break
            if not result_found:
                continue

            line_pos = el_pos.get(id(line), -1)
            if line_pos < 0:
                continue

            # Cari tanggal terdekat sebelum .paito-line (dalam jarak 500 elemen DOM)
            nearest_date = None
            nearest_dist = 999999
            for pos, d in date_pos_list:
                dist = line_pos - pos
                if 0 < dist < nearest_dist and dist < 500:
                    nearest_dist = dist
                    nearest_date = d

            if nearest_date:
                ds = f"{nearest_date[0]:04d}-{nearest_date[1]:02d}-{nearest_date[2]:02d}"
                if ds not in seen_dates3:
                    seen_dates3.add(ds)
                    rows_D.append({'date': ds, 'result': result_found})

        if rows_D:
            rows_D.sort(key=lambda x: x['date'], reverse=True)
            return rows_D[:HISTORY_MAX]

    # ── Strategy F: paito warna dibaca per baris kanan→kiri, bawah→atas ──
    # Angkanet18 tampilkan paito sebagai grid 7 kolom
    # Urutan result terbaru: baris terakhir dari kanan ke kiri, lalu baris sebelumnya, dst
    import datetime as _dt

    # Kumpulkan semua paito-line sebagai list of lists
    all_lines = []
    for line in soup.find_all(class_='paito-line'):
        items_in_line = []
        for item in line.find_all(class_='paito-row-item'):
            digits = [d.get_text(strip=True) for d in item.find_all(class_='paito-digit')]
            if len(digits) == 4:
                candidate = ''.join(digits)
            else:
                candidate = item.get_text(strip=True)
            if re.match(r'^\d{4}$', candidate) and not is_fake(candidate):
                items_in_line.append(candidate)
        if items_in_line:
            all_lines.append(items_in_line)

    if all_lines:
        # ── Strategy F: paito warna, baca FLAT kiri→kanan atas→bawah ──
        # Entry terakhir (kanan bawah) = result terbaru = anchor_date
        # libur_days: set hari libur (0=Sen...6=Min)
        flat = []
        for line in all_lines:
            flat.extend(line)

        if anchor_date:
            try:
                base = _dt.date.fromisoformat(anchor_date)
            except Exception:
                base = _dt.date(NOW.year, NOW.month, NOW.day) - _dt.timedelta(days=1)
        else:
            base = _dt.date(NOW.year, NOW.month, NOW.day) - _dt.timedelta(days=1)

        skip = libur_days or set()

        def prev_active(d):
            d -= _dt.timedelta(days=1)
            while d.weekday() in skip:
                d -= _dt.timedelta(days=1)
            return d

        cur = base
        while cur.weekday() in skip:
            cur -= _dt.timedelta(days=1)

        rows_F = []
        seen_dF = set()
        for r in reversed(flat):
            ds = cur.isoformat()
            if ds not in seen_dF:
                seen_dF.add(ds)
                rows_F.append({'date': ds, 'result': r})
            cur = prev_active(cur)
            if len(rows_F) >= HISTORY_MAX:
                break

        rows_F.sort(key=lambda x: x['date'], reverse=True)
        return rows_F

    return []


def merge_rows_into_history(existing_history: list, new_rows: list) -> list:
    """
    Gabungkan history lama + baris baru.
    Prioritas: data baru dari HTML MENIMPA data lama (lebih akurat).
    Data lama hanya dipakai untuk tanggal yang tidak ada di new_rows.
    """
    # Mulai dari data lama
    combined = {h['date']: h['result'] for h in existing_history}
    # Data baru selalu timpa data lama
    for r in new_rows:
        combined[r['date']] = r['result']
    merged = [{'date': d, 'result': res} for d, res in combined.items()]
    merged.sort(key=lambda x: x['date'], reverse=True)
    return merged[:HISTORY_MAX]


# ===== EKSTRAK RESULT TERBARU DARI HTML =====
def extract_result(html):
    if not html or len(html) < 200:
        return None, None

    soup = BeautifulSoup(html, 'html.parser')

    date_pat = re.compile(
        r'^(?:(\d{2})[/-](\d{2})[/-](\d{4})|(\d{4})[/-](\d{2})[/-](\d{2}))$'
    )
    ddmm_pat2 = re.compile(r'^(\d{1,2})[/-](\d{1,2})$')

    def parse_dt(text):
        m = date_pat.match(text)
        if m:
            if m.group(1):
                return (int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return (int(m.group(4)), int(m.group(5)), int(m.group(6)))
        # Support DD/MM tanpa tahun
        m2 = ddmm_pat2.match(text)
        if m2:
            dd, mm = int(m2.group(1)), int(m2.group(2))
            if 1 <= dd <= 31 and 1 <= mm <= 12:
                year = NOW.year
                if (mm, dd) > (NOW.month, NOW.day):
                    year -= 1
                return (year, mm, dd)
        return None

    # ── Strategy A: paito-line sebagai row container (struktur baru) ──
    valid_rows = []
    for line in soup.find_all(class_='paito-line'):
        date_found = result_found = None
        for el in line.find_all(True):
            t = el.get_text(strip=True)
            if date_found is None:
                date_found = parse_dt(t)
            if result_found is None and re.match(r'^\d{4}$', t) and not is_fake(t):
                result_found = t
            if date_found and result_found:
                break
        if date_found and result_found:
            valid_rows.append((date_found, result_found))

    if valid_rows:
        valid_rows.sort(key=lambda x: x[0])
        return list(valid_rows[-1][0]), valid_rows[-1][1]

    # ── Strategy B: paito-row-item grouping (struktur lama) ──
    all_items = soup.find_all(class_='paito-row-item')
    if all_items:
        row_map = {}
        for item in all_items:
            row_el = item.parent
            row_id = id(row_el)
            if row_id not in row_map:
                row_map[row_id] = {'date': None, 'result': None}
            text = item.get_text(strip=True)
            if row_map[row_id]['date'] is None:
                row_map[row_id]['date'] = parse_dt(text)
            if row_map[row_id]['result'] is None and re.match(r'^\d{4}$', text) and not is_fake(text):
                row_map[row_id]['result'] = text

        valid_b = [(r['date'], r['result']) for r in row_map.values()
                   if r['date'] and r['result']]
        if valid_b:
            valid_b.sort(key=lambda x: x[0])
            return list(valid_b[-1][0]), valid_b[-1][1]

    # ── Fallback: ambil angka 4 digit pertama ──
    last_valid = None
    for tag in soup.find_all(['span', 'td', 'div']):
        t = tag.get_text(strip=True)
        if re.match(r'^\d{4}$', t) and not is_fake(t):
            last_valid = t
    return None, last_valid


# ===== PAITO HARIAN =====
PAITO_HARIAN_URL = f'{BASE}/paito-harian/'

KEYWORD_MAP = [
    ('hongkong pool',          'hk'),
    ('hk pools',               'hk'),
    ('hk lotto',               'hkl'),
    ('hklotto',                'hkl'),
    ('singapore',              'sgp'),
    ('sydney pools',           'sdy'),
    ('sydney pool',            'sdy'),
    ('sydney lotto',           'sdl'),
    ('sdlotto',                'sdl'),
    ('magnum cambodia',        'kam'),
    ('kamboja',                'kam'),
    ('cambodia',               'kam'),
    ('bullseye',               'bull'),
    ('china pool',             'chn'),
    ('chinapool',              'chn'),
    ('japan',                  'jpn'),
    ('taiwan',                 'twn'),
    ('pcso',                   'pcso'),
    ('toto macau 1',           'mac1'),
    ('macau 13',               'mac1'),
    ('toto macau 2',           'mac2'),
    ('macau 16',               'mac2'),
    ('toto macau 3',           'mac3'),
    ('macau 19',               'mac3'),
    ('toto macau 4',           'mac4'),
    ('macau 22',               'mac4'),
    ('toto macau 5',           'mac5'),
    ('macau 00',               'mac5'),
    ('toto macau 6',           'mac6'),
    ('macau 23',               'mac6'),
    ('morocco quatro 03',      'mrq3'),
    ('morocco 03',             'mrq3'),
    ('morocco quatro 18',      'mrq18'),
    ('morocco 18',             'mrq18'),
    ('morocco quatro 21',      'mrq21'),
    ('morocco 21',             'mrq21'),
    ('morocco quatro 23',      'mrq23'),
    ('morocco 23',             'mrq23'),
    ('germany',                'ger'),
    ('oregon 04',              'or4'),
    ('oregon 07',              'or7'),
    ('oregon 10',              'or10'),
    ('oregon 13',              'or13'),
    ('north carolina day',     'ncd'),
    ('nc day',                 'ncd'),
    ('north carolina evening', 'nce'),
    ('nc evening',             'nce'),
    ('georgia midday',         'geom'),
    ('georgia mid',            'geom'),
    ('georgia evening',        'geoe'),
    ('georgia eve',            'geoe'),
    ('georgia night',          'geon'),
    ('texas morning',          'txmr'),
    ('texas day',              'txd'),
    ('texas evening',          'txe'),
    ('texas night',            'txn'),
    ('new york midday',        'nyd'),
    ('new york evening',       'nye'),
    ('new jersey midday',      'njm'),
    ('nj midday',              'njm'),
    ('new jersey evening',     'nje'),
    ('nj evening',             'nje'),
    ('florida midday',         'flm'),
    ('florida evening',        'fle'),
    ('illinois midday',        'ilm'),
    ('illinois evening',       'ile'),
    ('indiana midday',         'indm'),
    ('indiana evening',        'inde'),
    ('kentucky midday',        'kym'),
    ('kentucky evening',       'kye'),
    ('maryland midday',        'mdm'),
    ('maryland evening',       'mde'),
    ('michigan midday',        'mim'),
    ('michigan evening',       'mie'),
    ('missouri midday',        'mom'),
    ('missouri evening',       'moe'),
    ('washington dc midday',   'wdm'),
    ('wdc midday',             'wdm'),
    ('washington dc evening',  'wde'),
    ('wdc evening',            'wde'),
    ('connecticut day',        'ctd'),
    ('connecticut night',      'ctn'),
    ('virginia day',           'vad'),
    ('virginia night',         'van'),
    ('tennesse midday',        'tnm'),
    ('tennessee midday',       'tnm'),
    ('tennesse evening',       'tne'),
    ('tennessee evening',      'tne'),
    ('tennesse morning',       'tnmr'),
    ('tennessee morning',      'tnmr'),
    ('california',             'cal'),
    ('wisconsin evening',      'wie'),
]


def match_market(text):
    tl = text.lower()
    for kw, key in KEYWORD_MAP:
        if kw in tl:
            return key
    return None


def fetch_paito_harian():
    print(f"\n{'='*60}")
    print(f"[PAITO-HARIAN] {PAITO_HARIAN_URL}")
    print(f"{'='*60}")

    html = None
    for url, hdrs in [
        (PAITO_HARIAN_URL,                       dict(HEADERS)),
        (f'https://{DIRECT_IP}/paito-harian/',   {**HEADERS, 'Host': 'angkanet18.com'}),
    ]:
        try:
            time.sleep(0.5)
            r = requests.get(url, headers=hdrs, timeout=20, verify=False, allow_redirects=True)
            if r.status_code == 525:
                print(f"  525 SSL dari {url}, coba berikutnya...")
                continue
            r.raise_for_status()
            if len(r.text) > 1000:
                html = r.text
                print(f"  OK — {len(html):,} chars dari {url}")
                break
        except Exception as e:
            print(f"  GAGAL {url}: {e}")

    if not html:
        proxy_urls = [
            f'https://api.allorigins.win/get?url={requests.utils.quote(PAITO_HARIAN_URL)}',
            f'https://corsproxy.io/?{requests.utils.quote(PAITO_HARIAN_URL)}',
        ]
        for purl in proxy_urls:
            try:
                time.sleep(1)
                rp = requests.get(purl, headers=HEADERS, timeout=25, verify=False)
                rp.raise_for_status()
                try:
                    data = rp.json()
                    candidate = data.get('contents') or data.get('data') or ''
                    if isinstance(candidate, str) and len(candidate) > 1000:
                        html = candidate
                        print(f"  OK (proxy) — {len(html):,} chars dari {purl[:60]}...")
                        break
                except Exception:
                    if len(rp.text) > 1000:
                        html = rp.text
                        print(f"  OK (proxy raw) — {len(html):,} chars dari {purl[:60]}...")
                        break
            except Exception as ep:
                print(f"  PROXY GAGAL {purl[:60]}: {ep}")

    if not html:
        print("  Semua URL gagal — skip paito-harian.")
        return {}, {}

    soup = BeautifulSoup(html, 'html.parser')
    found = {}

    containers = soup.find_all(
        ['section', 'div', 'article', 'li'],
        class_=re.compile(r'(market|pasaran|paito|result|item|card|pool)', re.I)
    )
    for sec in containers:
        heading_el = (
            sec.find(['h1','h2','h3','h4','h5','strong'],
                     class_=re.compile(r'(title|name|head|market)', re.I))
            or sec.find(['h1','h2','h3','h4','h5','strong'])
        )
        if not heading_el:
            continue
        key = match_market(heading_el.get_text(strip=True))
        if not key or key in found:
            continue
        for tag in sec.find_all(['span','td','div','b','p']):
            t = tag.get_text(strip=True)
            if re.match(r'^\d{4}$', t) and not is_fake(t):
                found[key] = t
                print(f"  [{key.upper():6s}] {t}  (strategy-1 heading)")
                break

    if len(found) < 10:
        print(f"  Strategy-1: {len(found)} → coba strategy-2 (paito-row-item)")
        row_map = {}
        for item in soup.find_all(class_='paito-row-item'):
            rid = id(item.parent)
            if rid not in row_map:
                row_map[rid] = {'texts': [], 'result': None}
            t = item.get_text(strip=True)
            row_map[rid]['texts'].append(t)
            if row_map[rid]['result'] is None and re.match(r'^\d{4}$', t) and not is_fake(t):
                row_map[rid]['result'] = t
        for info in row_map.values():
            if not info['result']:
                continue
            key = match_market(' '.join(info['texts']))
            if key and key not in found:
                found[key] = info['result']
                print(f"  [{key.upper():6s}] {info['result']}  (strategy-2 row-item)")

    if len(found) < 5:
        print(f"  Strategy-2: {len(found)} → coba strategy-3 (scan blok)")
        for block in soup.find_all(['tr','li'], limit=3000):
            t = block.get_text(strip=True)
            if not (re.match(r'^\d{4}$', t) and not is_fake(t)):
                continue
            parent_txt = block.parent.get_text(' ', strip=True) if block.parent else ''
            key = match_market(parent_txt)
            if key and key not in found:
                found[key] = t
                print(f"  [{key.upper():6s}] {t}  (strategy-3 scan)")

    if len(found) < 5:
        print(f"  Strategy-3: {len(found)} → coba strategy-4 (ancestor context)")
        # Cari semua elemen dengan angka 4 digit valid, lalu naik ke ancestor untuk cari nama pasaran
        for tag in soup.find_all(['span', 'div', 'td', 'b', 'p']):
            t = tag.get_text(strip=True)
            if not (re.match(r'^\d{4}$', t) and not is_fake(t)):
                continue
            key = None
            ancestor = tag.parent
            for _ in range(10):
                if ancestor is None or ancestor.name in ['body', 'html', '[document]']:
                    break
                ancestor_text = ancestor.get_text(' ', strip=True)
                key = match_market(ancestor_text)
                if key:
                    break
                ancestor = ancestor.parent
            if key and key not in found:
                found[key] = t
                print(f"  [{key.upper():6s}] {t}  (strategy-4 ancestor)")

    print(f"\n  [PAITO-HARIAN] Ditemukan: {len(found)}/{len(PASARAN)} pasaran")

    # ── EKSTRAK HISTORY dari paito-harian (semua hasil per pasaran) ──
    harian_hist = {}
    current_key = None

    for tag in soup.find_all(True):
        if tag.name in ['h1','h2','h3','h4','h5','strong','b','a','span','p','div']:
            raw = tag.get_text(strip=True)
            if 3 < len(raw) < 60:
                k = match_market(raw)
                if k:
                    current_key = k

        cls = tag.get('class') or []
        if 'paito-line' in cls and current_key:
            # Baca tanggal + result dari tiap paito-line (sama seperti Strategy A)
            date_found = None
            result_found = None
            for el in tag.find_all(True):
                t = el.get_text(strip=True)
                if date_found is None:
                    d = parse_date(t)
                    if d:
                        date_found = d
                if result_found is None:
                    if re.match(r'^\d{4}$', t) and not is_fake(t):
                        result_found = t
                    else:
                        digits = [d2.get_text(strip=True)
                                  for d2 in el.find_all(class_='paito-digit')]
                        if len(digits) == 4:
                            num = ''.join(digits)
                            if re.match(r'^\d{4}$', num) and not is_fake(num):
                                result_found = num
                if date_found and result_found:
                    break
            if date_found and result_found and is_recent(date_found):
                ds = f"{date_found[0]:04d}-{date_found[1]:02d}-{date_found[2]:02d}"
                if current_key not in harian_hist:
                    harian_hist[current_key] = []
                existing_dates = {r['date'] for r in harian_hist[current_key]}
                if ds not in existing_dates:
                    harian_hist[current_key].append({'date': ds, 'result': result_found})

    print(f"  [PAITO-HARIAN] History ditemukan: {len(harian_hist)} pasaran\n")
    return found, harian_hist


# ===== FETCH SATU PASARAN =====
def fetch_pasaran(key, path, name):
    urls_to_try = [
        (BASE + path,                  dict(HEADERS)),
        (f'https://{DIRECT_IP}{path}', {**HEADERS, 'Host': 'angkanet18.com'}),
    ]

    last_err = None

    for attempt_url, headers in urls_to_try:
        via = ' (via IP)' if DIRECT_IP in attempt_url else ''
        try:
            time.sleep(0.5)
            resp = requests.get(
                attempt_url, headers=headers,
                timeout=15, verify=False, allow_redirects=True,
            )

            if resp.status_code == 525:
                print(f"  [{key.upper():6s}] 525 SSL Error{via}, coba fallback...")
                last_err = '525 SSL Error'
                continue

            resp.raise_for_status()
            html_text   = resp.text
            fetch_date, result = extract_result(html_text)
            # Ambil semua baris historis sekaligus dari HTML yang sama (zero request tambahan)
            # anchor_date: tanggal result terbaru agar Strategy F tidak geser
            # Tentukan anchor untuk Strategy F:
            # - Kalau paito sudah update (entry terakhir = result hari ini): anchor = hari ini
            # - Kalau belum: anchor = hari aktif sebelumnya (skip hari libur)
            # Setelah anchor ditentukan, SELALU skip hari libur
            import datetime as _dt_anc
            _skip = PASARAN_LIBUR.get(key, set())
            if fetch_date:
                _fd = _dt_anc.date(fetch_date[0], fetch_date[1], fetch_date[2])
            else:
                _fd = _dt_anc.date(NOW.year, NOW.month, NOW.day)
            # Deteksi: cek entry terakhir paito vs result terbaru
            from bs4 import BeautifulSoup as _BS
            _soup_tmp = _BS(html_text, 'html.parser')
            _pl = _soup_tmp.find_all(class_='paito-line')
            _last_val = None
            if _pl:
                _items = [x.get_text(strip=True) for x in _pl[-1].find_all(True)
                          if len(x.get_text(strip=True))==4 and x.get_text(strip=True).isdigit()]
                if _items:
                    _last_val = _items[-1]
            if _last_val and _last_val == result:
                _anc = _fd  # paito sudah update
            else:
                _anc = _fd - _dt_anc.timedelta(days=1)  # paito belum update
            # SELALU skip hari libur dari anchor
            while _anc.weekday() in _skip:
                _anc -= _dt_anc.timedelta(days=1)
            anchor = _anc.isoformat()
            all_rows    = extract_all_rows(html_text, anchor_date=anchor, libur_days=_skip)
            # Untuk pasaran mingguan, active_weekdays akan dideteksi saat backfill
            # (saat ini belum ada history akurat, skip dulu)

            if result:
                if fetch_date is None:
                    fetch_date = list(TODAY_TUPLE)

                date_str = f"{fetch_date[0]:04d}-{fetch_date[1]:02d}-{fetch_date[2]:02d}"

                # Toleransi stale: max 2 hari ke belakang (pasaran luar negeri timezone beda)
                import datetime as _dt_stale
                today_date = _dt_stale.date(TODAY_TUPLE[0], TODAY_TUPLE[1], TODAY_TUPLE[2])
                fetch_date_obj = _dt_stale.date(fetch_date[0], fetch_date[1], fetch_date[2])
                days_old = (today_date - fetch_date_obj).days
                if days_old > 2:
                    print(f"  [{key.upper():6s}] STALE {result} dari {date_str} "
                          f"({days_old} hari lalu) → anggap belum keluar")
                    last_err = f'stale data {days_old} hari dari {date_str}'
                    continue

                print(f"  [{key.upper():6s}] OK {result}  ({name}){via}"
                      + (f"  [tgl: {date_str}]" if date_str else "")
                      + (f"  [{len(all_rows)} baris historis]" if all_rows else ""))
                return {
                    'result':        result,
                    'tgl':           TODAY,
                    'fetch_date':    list(fetch_date),
                    'status':        'sudah',
                    'updated':       NOW.strftime('%H:%M WIB'),
                    'name':          name,
                    'extra_history': all_rows,   # ← semua baris untuk backfill
                }
            else:
                print(f"  [{key.upper():6s}] WARN angka tidak ketemu{via}  ({name})")
                last_err = 'angka tidak ketemu'
                continue

        except requests.RequestException as e:
            print(f"  [{key.upper():6s}] ERR {e}{via}  ({name})")
            last_err = str(e)
            continue
        except Exception as e:
            print(f"  [{key.upper():6s}] ERR {e}{via}  ({name})")
            last_err = str(e)
            continue

    if key in PASARAN_MALAM and NOW.hour < 23:
        print(f"  [{key.upper():6s}] INFO: Pasaran malam (jam {NOW.hour:02d}:xx WIB) — wajar belum keluar")
    else:
        print(f"  [{key.upper():6s}] FINAL GAGAL: {last_err}")

    return {
        'result':  '----',
        'tgl':     TODAY,
        'status':  'belum',
        'updated': NOW.strftime('%H:%M WIB'),
        'name':    name,
    }


# ===== MAIN =====
def main():
    print(f"\n{'='*60}")
    print(f"fetch_all.py v3 — {NOW.strftime('%A, %d %B %Y %H:%M WIB')}")
    print(f"Total pasaran: {len(PASARAN)}  |  History max: {HISTORY_MAX}")
    print(f"{'='*60}\n")

    try:
        with open('result.json', 'r', encoding='utf-8') as f:
            saved = json.load(f)
        print(f"Data lama: {len([k for k in saved if not k.startswith('_')])} pasaran\n")
    except Exception:
        saved = {}
        print("Tidak ada data lama.\n")

    # Bersihkan key obsolete
    result_data = {k: v for k, v in saved.items() if k in PASARAN or k.startswith('_')}

    # ── STEP 1: Fetch paito-harian ──
    harian, harian_hist = fetch_paito_harian()

    # ── PHANTOM DETECTION ──
    # Kalau nilai yang sama muncul di >10 market sekaligus → elemen statis, bukan result asli
    if harian:
        from collections import Counter as _Ctr
        _vc = _Ctr(harian.values())
        _phantom = {v for v, c in _vc.items() if c > 10}
        if _phantom:
            for _pv in _phantom:
                _cnt = _vc[_pv]
                print(f"  [PHANTOM] Nilai '{_pv}' muncul di {_cnt} pasaran — dibuang semua")
            harian = {k: v for k, v in harian.items() if v not in _phantom}
            # Bersihkan juga harian_hist untuk market yang phantom
            harian_hist = {k: v for k, v in harian_hist.items()
                           if k in harian or not all(
                               str(r.get('result','')) in _phantom
                               for r in v[:3]
                           )}

    for key, (path, name) in PASARAN.items():
        if key in harian and re.match(r'^\d{4}$', harian[key]) and not is_fake(harian[key]):
            # Ambil tanggal akurat dari harian_hist jika ada
            # harian_hist[key] = list of {date, result} urut desc
            h_rows = harian_hist.get(key, []) if harian_hist else []
            harian_date = h_rows[0]['date'] if h_rows else TODAY_STR
            entry = {
                'result':        harian[key],
                'tgl':           TODAY,
                'fetch_date':    [int(x) for x in harian_date.split('-')],
                'status':        'sudah',
                'updated':       NOW.strftime('%H:%M WIB'),
                'name':          name,
                'extra_history': h_rows,
            }
            print(f"  [{key.upper():6s}] {harian[key]}  ({name}) [paito-harian] tgl={harian_date}")
        else:
            if key in harian:
                print(f"  [{key.upper():6s}] Tidak valid dari paito-harian, fetch individual...")
            else:
                print(f"Fetching {key.upper()} <- {BASE+path}")
            entry = fetch_pasaran(key, path, name)

        old = result_data.get(key, {})

        if entry['result'] != '----':
            old_fd  = old.get('fetch_date')
            new_fd  = entry.get('fetch_date')
            today_t = TODAY_TUPLE
            old_res = old.get('result', '')

            should_overwrite = True

            if new_fd is not None:
                new_fd_t = tuple(new_fd)
                if old_fd is not None:
                    # Tolak hanya jika data baru LEBIH LAMA dari data tersimpan
                    if new_fd_t < tuple(old_fd):
                        should_overwrite = False
                # Jika tidak ada old_fd: selalu overwrite (data baru selalu lebih baik dari kosong)
                # TIDAK cek new_fd_t < today_t karena banyak pasaran result-nya kemarin tapi valid

            if should_overwrite:
                # ── HISTORY: merge result baru + semua baris historis ──
                # FIX: gunakan tanggal dari extra_history[0] sebagai tanggal result
                # karena extract_result tidak bisa baca tanggal dari HTML angkanet
                extra = entry.pop('extra_history', [])
                if extra and extra[0].get('date'):
                    # Selalu pakai tanggal dari HTML (akurat)
                    entry_date = extra[0]['date']
                    # Kalau extra[0] adalah result yg sama, buang dari extra
                    # tapi tetap pakai entry_date-nya (sudah di-set di atas)
                    if extra[0].get('result') == entry['result']:
                        extra = extra[1:]
                elif new_fd:
                    entry_date = f"{new_fd[0]:04d}-{new_fd[1]:02d}-{new_fd[2]:02d}"
                else:
                    entry_date = TODAY_STR
                # update_history: tambahkan result dengan entry_date (tanggal akurat dari HTML)
                # TIDAK duplikasi ke TODAY_STR — entry_date sudah akurat dari HTML
                base_history = update_history(old, entry['result'], entry_date)
                # Buang entry >= entry_date (sudah dihandle update_history)
                extra = [e for e in extra if e.get('date','') < entry_date]
                # Merge extra_history dari halaman (backfill otomatis)
                if extra:
                    base_history = merge_rows_into_history(base_history, extra)
                entry['history'] = base_history
                result_data[key] = entry
                print(f"  [{key.upper():6s}] History: {len(entry['history'])} entry")
            else:
                ref = ('saved ' + str(old_fd)) if old_fd else ('TODAY ' + str(list(today_t)))
                print(f"  [{key.upper():6s}] SKIP overwrite: "
                      f"fetch {new_fd} < {ref}, "
                      f"pakai data lama: {old_res}")
                # Pastikan history lama tetap ada (tidak hilang)
                result_data[key] = old

        elif key not in result_data:
            entry['history'] = []
            result_data[key] = entry
        else:
            old_result = result_data[key].get('result', '')
            if is_fake(old_result):
                print(f"  [{key.upper():6s}] Data lama '{old_result}' INVALID, reset ke ----")
                entry['history'] = old.get('history', [])
                result_data[key] = entry
            else:
                print(f"  [{key.upper():6s}] Pakai data lama: {old_result}")
                # history lama tetap terjaga karena result_data[key] tidak diubah

    # ===== STEP 2: BACKFILL PASS =====
    # Untuk pasaran yang datang dari paito-harian (tidak lewat fetch_pasaran),
    # history-nya cuma 1 entry. Fetch individual untuk ambil baris historis.
    # Batasi 30 pasaran per run agar tidak timeout di GitHub Actions.
    BACKFILL_THRESHOLD = HISTORY_MAX   # backfill selama belum penuh
    BACKFILL_LIMIT     = 65            # max pasaran per run
    backfill_count     = 0

    needs_backfill = [
        (k, PASARAN[k])
        for k in PASARAN
        if len(result_data.get(k, {}).get('history', [])) < BACKFILL_THRESHOLD
        and result_data.get(k, {}).get('result', '----') != '----'
    ]

    if needs_backfill:
        print(f"\n{'='*60}")
        print(f"[BACKFILL] {len(needs_backfill)} pasaran history < {BACKFILL_THRESHOLD} entry")
        print(f"           Akan proses max {BACKFILL_LIMIT} pasaran sekarang.")
        print(f"{'='*60}")

    for key, (path, name) in needs_backfill[:BACKFILL_LIMIT]:
        cur_hist = result_data[key].get('history', [])
        if len(cur_hist) >= BACKFILL_THRESHOLD:
            continue
        backfill_count += 1

        # ── Prioritas 1: gunakan history dari paito-harian (tanggal akurat) ──
        if key in harian_hist and len(harian_hist[key]) > len(cur_hist):
            new_hist = merge_rows_into_history(cur_hist, harian_hist[key])
            result_data[key]['history'] = new_hist
            added = len(new_hist) - len(cur_hist)
            print(f"  [BF {key.upper():6s}] paito-harian: {len(new_hist)} entry (+{added})")
            # Update cur_hist agar Prioritas 2 bisa pakai active_weekdays yg akurat
            cur_hist = new_hist

        # Kalau sudah penuh dari paito-harian, skip fetch individual
        if len(cur_hist) >= BACKFILL_THRESHOLD:
            continue

        # ── Prioritas 2: fetch halaman individual ──
        print(f"  [BF {key.upper():6s}] Fetch {BASE+path}  (hist: {len(cur_hist)}){''}")
        for url, hdrs in [
            (BASE + path, dict(HEADERS)),
            (f'https://{DIRECT_IP}{path}', {**HEADERS, 'Host': 'angkanet18.com'}),
        ]:
            try:
                time.sleep(0.5)
                r = requests.get(url, headers=hdrs, timeout=15, verify=False, allow_redirects=True)
                if r.status_code == 525:
                    continue
                r.raise_for_status()
                if len(r.text) < 500:
                    continue
                # anchor = 1 hari sebelum entry tertua di history yang sudah ada
                # agar Strategy F sambung tepat tanpa overlap/geser
                import datetime as _dt2
                # Anchor = dari result terbaru di history (bukan entry tertua)
                # Pakai history[0] (terbaru) sebagai anchor Strategy F
                if cur_hist:
                    bf_anchor = cur_hist[0]['date']
                else:
                    bf_anchor = (_dt2.date(TODAY_TUPLE[0], TODAY_TUPLE[1], TODAY_TUPLE[2]) - _dt2.timedelta(days=1)).isoformat()
                # Deteksi pola hari aktif dari history yang sudah punya tanggal akurat
                aw = detect_active_weekdays(cur_hist) if key in PASARAN_MINGGUAN else set()
                rows = extract_all_rows(r.text, anchor_date=bf_anchor, active_weekdays=aw if aw else None, libur_days=PASARAN_LIBUR.get(key, set()))
                if rows:
                    new_hist = merge_rows_into_history(cur_hist, rows)
                    result_data[key]['history'] = new_hist
                    added = len(new_hist) - len(cur_hist)
                    print(f"  [BF {key.upper():6s}] {len(new_hist)} entry (+{added})"
                          f"  [{rows[-1]['date']} → {rows[0]['date']}]")
                else:
                    print(f"  [BF {key.upper():6s}] Tidak ada baris ditemukan")
                break
            except Exception as e:
                print(f"  [BF {key.upper():6s}] ERR {e}")

    if backfill_count:
        print(f"\n[BACKFILL] Selesai: {backfill_count} pasaran diproses.")

    # ===== TERAPKAN MANUAL OVERRIDE =====
    for ov_key, ov_result in MANUAL_OVERRIDE.items():
        if ov_key in result_data:
            old_val = result_data[ov_key].get('result', '----')
            print(f"  [{ov_key.upper():6s}] MANUAL OVERRIDE: {old_val} → {ov_result}")
            result_data[ov_key]['result']     = ov_result
            result_data[ov_key]['status']     = 'sudah'
            result_data[ov_key]['fetch_date'] = list(TODAY_TUPLE)
            result_data[ov_key]['updated']    = NOW.strftime('%H:%M WIB') + ' [MANUAL]'
            # Update history untuk override juga
            result_data[ov_key]['history'] = update_history(
                result_data[ov_key], ov_result, TODAY_STR
            )

    # ===== FINAL CLEANUP: buang entry TODAY yang dobel di semua pasaran =====
    # Jaring terakhir — backfill/merge bisa re-add entry dobel,
    # cleanup ini jalan setelah semua proses selesai, tepat sebelum simpan.
    yest_str = (
        datetime.strptime(TODAY_STR, '%Y-%m-%d') - timedelta(days=1)
    ).strftime('%Y-%m-%d')
    dobel_cleaned = 0
    for key in PASARAN:
        if key not in result_data:
            continue
        hist = result_data[key].get('history', [])
        hist_map = {h['date']: h['result'] for h in hist}
        today_res = hist_map.get(TODAY_STR)
        yest_res  = hist_map.get(yest_str)
        # DIHAPUS: cleanup "dobel" berdasarkan nilai sama berbahaya untuk pasaran mingguan
        # (angka bisa kebetulan sama di dua hari berbeda). Dedup by date sudah cukup di bawah.
        pass
    if dobel_cleaned:
        print(f"  [CLEANUP] Total dobel dibersihkan: {dobel_cleaned} pasaran\n")
    # ===== FINAL SAFETY NET: dedup + trim ketat semua history =====
    for key in PASARAN:
        if key not in result_data:
            continue
        hist = result_data[key].get('history', [])
        seen_dates = set()
        deduped = []
        for h in sorted(hist, key=lambda x: x.get('date',''), reverse=True):
            d = h.get('date')
            if d and d not in seen_dates:
                seen_dates.add(d)
                deduped.append(h)
        result_data[key]['history'] = deduped[:HISTORY_MAX]


    result_data['_meta'] = {
        'updated':     NOW.strftime('%Y-%m-%d %H:%M WIB'),
        'date':        TODAY,
        'today_str':   TODAY_STR,
        'total':       len(PASARAN),
        'history_max': HISTORY_MAX,
    }

    with open('result.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    ok = [k for k in PASARAN
          if re.match(r'^\d{4}$', result_data.get(k, {}).get('result', ''))]
    # Summary history
    hist_ok = [k for k in PASARAN if result_data.get(k, {}).get('history')]
    print(f"\n{'='*60}")
    print(f"result.json tersimpan")
    print(f"Valid hari ini : {len(ok)}/{len(PASARAN)}")
    print(f"Ada history    : {len(hist_ok)} pasaran")
    avg = (sum(len(result_data[k].get('history',[])) for k in hist_ok) / len(hist_ok)) if hist_ok else 0
    print(f"Rata-rata hist : {avg:.1f} entry per pasaran")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
