/**
 * wb-member-bank.js
 * ─────────────────────────────────────────────────────────────────────
 * Bank rumus PER-MEMBER *dan* PER-HALAMAN (scan1..scan5), disimpan di
 * SERVER (JSONBin). Mulai versi ini, TIAP HALAMAN SCAN PUNYA BIN SENDIRI
 * (bukan gabung satu bin besar lagi) — biar gak gampang kepenuhan limit
 * 100kb/bin punya akun gratis, dan simpan di satu scan gak ikut gagal
 * gara-gara scan lain sudah penuh.
 *
 * WAJIB: taruh <script> kecil SEBELUM file ini yang isinya:
 *   window.WB_JSONBIN_CONFIG = {
 *     key: 'ACCESS_KEY_SITUS_INI',
 *     bin: 'BIN_MEMBERS_SITUS_INI',   // bin akun/login lama — TETAP dipakai utk data akun
 *     bankBins: {                      // bin BARU, satu per halaman scan
 *       scan1: 'BIN_ID_SCAN1', scan2: 'BIN_ID_SCAN2', scan3: 'BIN_ID_SCAN3',
 *       scan4: 'BIN_ID_SCAN4', scan5: 'BIN_ID_SCAN5'
 *     }
 *   };
 * Kalau bankBins[scanN] belum diisi, halaman itu OTOMATIS jalan seperti
 * sebelumnya (baca/tulis ke bin member lama) — jadi aman diisi bertahap,
 * gak perlu 5 bin langsung jadi semua di hari yang sama.
 *
 * Begitu bankBins[scanN] diisi, rumus lama scan itu (yang masih nyangkut
 * di bin member lama) OTOMATIS dipindah ke bin barunya sekali jalan
 * (dan dihapus dari bin lama, biar bin lama ikut mengecil).
 *
 * Cara pakai di halaman scan (ASYNC — pakai .then()/await, KECUALI layer
 * sinkron WB_BANK.*Sync di bawah yang memang didesain buat kode sinkron):
 *   WB_BANK.get('scan1').then(data => ...)
 *   await WB_BANK.set(data, 'scan1')
 *   WB_BANK.currentId()   ← ini masih sinkron (baca sesi login lokal)
 * ─────────────────────────────────────────────────────────────────────
 */

(function(global){

  // Sama persis dengan skema di index.html: sesi login di-scope per-situs
  // (domain + folder repo), biar gak ketuker walau ada beberapa situs
  // WongBagus di akun GitHub yang sama.
  const WB_SITE_ID   = location.hostname + '/' + (location.pathname.split('/')[1] || '');
  const WB_LOGIN_KEY = 'wb_logged_member__' + WB_SITE_ID;

  function currentMemberId(){
    try{
      const raw = localStorage.getItem(WB_LOGIN_KEY);
      if(!raw) return 'guest';
      const obj = JSON.parse(raw);
      return (obj.id || obj.phone || 'guest');
    }catch(e){ return 'guest'; }
  }

  function currentMemberName(){
    try{
      const raw = localStorage.getItem(WB_LOGIN_KEY);
      if(!raw) return 'Guest';
      return JSON.parse(raw).name || 'Member';
    }catch(e){ return 'Member'; }
  }

  function cfg(){
    const c = global.WB_JSONBIN_CONFIG;
    if(!c || !c.key || !c.bin){
      throw new Error('WB_JSONBIN_CONFIG belum di-set. Cek <script> config sebelum wb-member-bank.js di <head>.');
    }
    return { key: c.key, bin: c.bin, bankBins: c.bankBins || {}, base: c.base || 'https://api.jsonbin.io/v3/b' };
  }

  // appId bisa 'scan1'..'scan5', atau varian scan3 spt 'scan3_myBank' —
  // semuanya tetap satu HALAMAN yang sama ('scan3'), jadi satu bin yang sama.
  function pageOf(appId){
    const m = /^scan[1-5]/.exec(appId || '');
    return m ? m[0] : 'default';
  }
  function pageBinId(appId){
    try{ return cfg().bankBins[pageOf(appId)] || null; }catch(e){ return null; }
  }

  function bankToast(msg){
    try{
      let el = document.getElementById('wb-bank-toast');
      if(!el){
        el = document.createElement('div');
        el.id = 'wb-bank-toast';
        el.style.cssText = 'position:fixed;left:50%;bottom:56px;transform:translateX(-50%);z-index:100000;background:#7f1d1d;color:#fff;padding:8px 14px;border-radius:8px;font-size:12px;font-weight:700;max-width:90%;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.4)';
        document.body.appendChild(el);
      }
      el.textContent = msg; el.style.display = 'block';
      clearTimeout(el._t); el._t = setTimeout(()=>{ el.style.display='none'; }, 4500);
    }catch(e){}
  }

  // Trek lama dipangkas sebelum dikirim ke server — status/streak tetap
  // akurat (angka tersendiri, bukan dihitung dari panjang trekRows),
  // yang dibuang cuma histori lama buat tampilan.
  const TREK_ROWS_CAP = 3;
  function trimItem(item){
    if(!item || !Array.isArray(item.trekRows) || item.trekRows.length<=TREK_ROWS_CAP) return item;
    return { ...item, trekRows: item.trekRows.slice(-TREK_ROWS_CAP) };
  }
  function trimArr(arr){ return Array.isArray(arr) ? arr.map(trimItem) : arr; }

  // ══════════════════════════════════════════════════════════════
  // BATAS RUMUS PER MEMBER — diatur admin di Edit Akun (field bankLimit
  // di data member). Berlaku PER HALAMAN scan (scan1..scan5 dihitung
  // sendiri-sendiri; sub-bank satu halaman, mis. scan3_xxx, dijumlah).
  // Admin tanpa batas. Kosong di admin = pakai BANK_LIMIT_DEFAULT.
  // Bin tiap scan dipakai BERSAMA semua member (limit 100KB), jadi
  // bawaannya sengaja kecil.
  // ══════════════════════════════════════════════════════════════
  const _syncCache = {};       // appId -> array
  const BANK_LIMIT_DEFAULT = 20;
  function memberBankLimit(){
    try{
      const raw = localStorage.getItem(WB_LOGIN_KEY);
      if(!raw) return 0;
      const o = JSON.parse(raw);
      if(o.isAdmin || o.id==='ADMIN') return 0;
      const n = parseInt(o.bankLimit, 10);
      return n > 0 ? n : BANK_LIMIT_DEFAULT;
    }catch(e){ return 0; }
  }
  function pageCount(appId, exceptApp){
    const pid = pageOf(appId); let n = 0;
    Object.keys(_syncCache).forEach(a=>{ if(pageOf(a)===pid && a!==exceptApp) n += (_syncCache[a]||[]).length; });
    return n;
  }
  function bankRoom(appId, n){
    const lim = memberBankLimit();
    if(!lim) return n;
    return Math.max(0, Math.min(n, lim - pageCount(appId)));
  }

  // ══════════════════════════════════════════════════════════════
  // BIN LAMA (member) — sumber data akun/login, dan fallback/sumber
  // migrasi selama bankBins[halaman] belum diisi di wb-config.js.
  // ══════════════════════════════════════════════════════════════
  async function fetchMembers(){
    const c = cfg();
    const r = await fetch(`${c.base}/${c.bin}/latest`, { headers: { 'X-Access-Key': c.key } });
    if(!r.ok) throw new Error('Gagal ambil data member (HTTP '+r.status+')');
    const d = await r.json();
    if(!d || !d.record) return [];
    return Array.isArray(d.record) ? d.record : (d.record.data || []);
  }
  async function saveMembers(list){
    const c = cfg();
    const r = await fetch(`${c.base}/${c.bin}`, {
      method: 'PUT',
      headers: { 'X-Access-Key': c.key, 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: list })
    });
    if(!r.ok) throw new Error('Gagal simpan bank ke server (HTTP '+r.status+')');
  }
  let _legacyCache = null, _legacyPromise = null;
  async function loadLegacy(){
    if(_legacyCache) return _legacyCache;
    if(!_legacyPromise) _legacyPromise = fetchMembers().then(list => { _legacyCache = list; return list; });
    return _legacyPromise;
  }
  function invalidateLegacy(){ _legacyCache = null; _legacyPromise = null; }
  function findMember(list, memberId){
    const mid = memberId || currentMemberId();
    return list.find(m => m.id===mid || m.phone===mid);
  }
  async function legacyGet(appId, memberId){
    try{
      const list = await loadLegacy();
      const m = findMember(list, memberId);
      return (m && m.banks && m.banks[appId]) || [];
    }catch(e){ return []; }
  }
  async function legacySet(data, appId, memberId){
    const list = await fetchMembers(); // FRESH biar gak nimpa perubahan lain yang barusan terjadi
    const mid = memberId || currentMemberId();
    let idx = list.findIndex(m => m.id===mid || m.phone===mid);
    if(idx===-1){
      if(mid==='ADMIN'){ list.push({ id:'ADMIN', name:'Admin', banks:{} }); idx = list.length-1; }
      else throw new Error('Member tidak ditemukan di server (mungkin belum login / akun beda situs)');
    }
    list[idx].banks = list[idx].banks || {};
    if(data===null) delete list[idx].banks[appId]; else list[idx].banks[appId] = trimArr(data || []);
    list.forEach(m=>{ if(m&&m.banks) Object.keys(m.banks).forEach(a=>{ m.banks[a]=trimArr(m.banks[a]); }); });
    await saveMembers(list);
    invalidateLegacy();
  }

  // ══════════════════════════════════════════════════════════════
  // BIN BARU — satu per halaman scan. Isi bin: { "<memberId>": { "<appId>": [...] } }
  // ══════════════════════════════════════════════════════════════
  const _pageCache = {};    // pageId -> record
  const _pagePromise = {};
  async function fetchPage(binId){
    const c = cfg();
    const r = await fetch(`${c.base}/${binId}/latest`, { headers: { 'X-Access-Key': c.key } });
    if(!r.ok) throw new Error('Gagal ambil bank (HTTP '+r.status+')');
    const d = await r.json();
    const rec = d && d.record;
    return (rec && typeof rec==='object' && !Array.isArray(rec)) ? rec : {};
  }
  async function savePage(binId, data){
    const c = cfg();
    const r = await fetch(`${c.base}/${binId}`, {
      method: 'PUT',
      headers: { 'X-Access-Key': c.key, 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if(!r.ok){
      let msg = 'HTTP '+r.status;
      try{ const j = await r.json(); if(j && j.message) msg += ' - ' + j.message; }catch(e){}
      throw new Error('Gagal simpan bank ('+msg+')');
    }
  }
  async function loadPageCached(appId){
    const binId = pageBinId(appId);
    if(!binId) return null; // belum dikonfig di wb-config.js -> null artinya "pakai bin lama"
    const pid = pageOf(appId);
    if(_pageCache[pid]) return _pageCache[pid];
    if(!_pagePromise[pid]) _pagePromise[pid] = fetchPage(binId).then(d=>{ _pageCache[pid]=d; return d; });
    return _pagePromise[pid];
  }

  // Migrasi 1x per (halaman, member): kalau data appId ini belum ada di
  // bin baru tapi ADA di bin lama, pindahkan ke bin baru lalu hapus dari
  // bin lama (biar bin lama ikut mengecil).
  const _migratedMark = {};
  async function migrateIfNeeded(appId, mid, page){
    const mk = pageOf(appId) + '|' + mid;
    if(_migratedMark[mk]) return page;
    _migratedMark[mk] = true;
    const binId = pageBinId(appId);
    if(!binId) return page;
    try{
      const list = await loadLegacy();
      const m = findMember(list, mid);
      const oldBanks = (m && m.banks) || {};
      const appsToMove = Object.keys(oldBanks).filter(a => pageOf(a)===pageOf(appId) && oldBanks[a] && oldBanks[a].length);
      if(!appsToMove.length) return page;
      page[mid] = page[mid] || {};
      let moved = false;
      appsToMove.forEach(a=>{
        if(!page[mid][a] || !page[mid][a].length){ page[mid][a] = oldBanks[a]; moved = true; }
      });
      if(moved){
        await savePage(binId, page);
        _pageCache[pageOf(appId)] = page;
        for(const a of appsToMove){ await legacySet(null, a, mid); }
        bankToast('✅ Bank lama dipindah ke penyimpanan baru.');
      }
    }catch(e){ console.warn('[WB_BANK] migrasi gagal:', e); }
    return page;
  }

  async function bankGet(appId, memberId){
    const mid = memberId || currentMemberId();
    const app = appId || 'default';
    try{
      let page = await loadPageCached(app);
      if(page){
        page = await migrateIfNeeded(app, mid, page);
        return (page[mid] && page[mid][app]) || [];
      }
    }catch(e){ console.warn('[WB_BANK] gagal ambil bank:', e); }
    return legacyGet(app, mid); // bin halaman ini belum dikonfig -> pakai bin lama
  }

  async function bankSet(data, appId, memberId){
    const mid = memberId || currentMemberId();
    const app = appId || 'default';
    const binId = pageBinId(app);
    if(!binId) return legacySet(data, app, mid);
    const page = await fetchPage(binId); // FRESH
    page[mid] = page[mid] || {};
    if(data===null) delete page[mid][app]; else page[mid][app] = trimArr(data || []);
    await savePage(binId, page);
    _pageCache[pageOf(app)] = page;
  }

  async function bankAdd(item, appId, memberId){
    const bank = await bankGet(appId, memberId);
    const isDup = bank.some(b =>
      b.formula === item.formula &&
      (b.wbId||b.pasaran) === (item.wbId||item.pasaran) &&
      b.jenis === item.jenis
    );
    if(isDup) return false;
    bank.unshift({...item, savedAt: new Date().toISOString()});
    await bankSet(bank, appId, memberId);
    return true;
  }

  async function bankClear(appId, memberId){ await bankSet([], appId, memberId); }

  async function bankListApps(memberId){
    const mid = memberId || currentMemberId();
    const apps = new Set();
    try{ const list = await loadLegacy(); const m=findMember(list, mid); if(m&&m.banks) Object.keys(m.banks).forEach(a=>apps.add(a)); }catch(e){}
    // Aktif nanya ke SEMUA bin halaman yang dikonfigurasi (scan1..scan5), bukan cuma
    // yang kebetulan udah kebuka di sesi browser ini — biar admin bisa lihat total
    // rumus member lain walau admin sendiri belum pernah buka scan itu di tab ini.
    let pageIds = [];
    try{ pageIds = Object.keys(cfg().bankBins); }catch(e){}
    for(const pid of pageIds){
      try{
        const page = await loadPageCached(pid); // pid = appId representatif ('scan1'..'scan5')
        if(page && page[mid]) Object.keys(page[mid]).forEach(a=>apps.add(a));
      }catch(e){ console.warn('[WB_BANK] gagal cek bank', pid, e); }
    }
    return [...apps];
  }

  async function bankCountAll(memberId){
    const apps = await bankListApps(memberId);
    let sum = 0;
    for(const a of apps) sum += (await bankGet(a, memberId)).length;
    return sum;
  }

  // ══════════════════════════════════════════════════════════════
  // LAYER SINKRON — buat halaman scan yang kodenya sinkron.
  // Dimuat per-HALAMAN (bukan per-appId): sekali fetch, semua sub-bank
  // milik halaman itu (mis. scan3_utama, scan3_bank2, dst) ikut kebawa.
  //   WB_BANK.onReady(cb, appId)  → cb dipanggil setelah bank halaman termuat
  //   WB_BANK.getSync(appId)      → ambil bank dari cache
  //   WB_BANK.setSync(data,appId) → simpan (cache + server, antre per-halaman)
  //   WB_BANK.clearSync(appId)    → hapus bank appId sepenuhnya
  //   WB_BANK.listAppsSync()      → daftar appId yang sudah termuat di cache
  // ══════════════════════════════════════════════════════════════
  const _pageSyncState = {};   // pageId -> {ready,ok,cbs}
  const _queueByPage = {};

  function ensurePageSync(appId){
    const pid = pageOf(appId);
    if(!_pageSyncState[pid]){
      const st = { ready:false, ok:false, cbs:[] };
      _pageSyncState[pid] = st;
      loadPageSync(appId, pid, st);
    }
    return _pageSyncState[pid];
  }

  async function loadPageSync(appId, pid, st){
    const mid = currentMemberId();
    try{
      if(mid !== 'guest'){
        let page = await loadPageCached(appId);
        if(page){
          page = await migrateIfNeeded(appId, mid, page);
          const mine = page[mid] || {};
          Object.keys(mine).forEach(a=>{ _syncCache[a] = mine[a] || []; });
        } else {
          const list = await loadLegacy();
          const m = findMember(list, mid);
          const banks = (m && m.banks) || {};
          Object.keys(banks).forEach(a=>{ if(pageOf(a)===pid) _syncCache[a] = banks[a] || []; });
        }
        st.ok = true;
      }
    }catch(e){
      console.warn('[WB_BANK] gagal muat bank:', e);
      bankToast('⚠️ Bank gagal dimuat dari server. Cek koneksi & wb-config.js, lalu refresh.');
    }
    st.ready = true;
    st.cbs.splice(0).forEach(cb=>{ try{ cb(); }catch(e){ console.error(e); } });
  }

  function persist(data, appId){
    const app = appId || 'default';
    const pid = pageOf(app);
    const st = _pageSyncState[pid];
    if(!st || !st.ok){
      bankToast(currentMemberId()==='guest' ? '⚠️ Login dulu untuk menyimpan ke Bank.' : '⚠️ Bank belum termuat dari server, simpan dibatalkan.');
      return false;
    }
    const lim = memberBankLimit();
    if(lim && data!==null){
      const prevLen = (_syncCache[app]||[]).length;
      if(data.length > prevLen && pageCount(app, app) + data.length > lim){
        bankToast('⚠️ Bank penuh (batas '+lim+' rumus per scan). Hapus rumus lama dulu.');
        return false;
      }
    }
    if(data===null) delete _syncCache[app];
    else _syncCache[app] = JSON.parse(JSON.stringify(data));
    _queueByPage[pid] = (_queueByPage[pid] || Promise.resolve())
      .then(()=>bankSet(data===null?null:data, app))
      .catch(e=>{
        console.error('[WB_BANK] simpan gagal:', e);
        const msg = (e.message||String(e));
        if(/100kb|413|too large/i.test(msg)) bankToast('⚠️ Bank kepenuhan (limit akun gratis 100kb). Hapus beberapa rumus lama lalu coba lagi.');
        else bankToast('⚠️ Gagal simpan bank ke server: '+msg);
      });
    return true;
  }

  global.WB_BANK = {
    currentId : currentMemberId,
    currentName: currentMemberName,
    get : (appId, memberId) => bankGet(appId, memberId),
    set : (data, appId, memberId) => bankSet(data, appId, memberId),
    add : (item, appId, memberId) => bankAdd(item, appId, memberId),
    clear : (appId, memberId) => bankClear(appId, memberId),
    listApps : (memberId) => bankListApps(memberId),
    countAll : (memberId) => bankCountAll(memberId),
    ready : (appId) => new Promise(res=>{ const st=ensurePageSync(appId); if(st.ready) res(); else st.cbs.push(res); }),
    isReady : (appId) => { const st=_pageSyncState[pageOf(appId||'default')]; return !!(st && st.ready && st.ok); },
    onReady : (cb, appId) => { const st=ensurePageSync(appId); if(st.ready) cb(); else st.cbs.push(cb); },
    getSync : (appId) => JSON.parse(JSON.stringify(_syncCache[appId||'default'] || [])),
    setSync : (data, appId) => persist(data || [], appId),
    clearSync : (appId) => persist(null, appId),
    listAppsSync : () => Object.keys(_syncCache),
    limit : memberBankLimit,                       // 0 = tanpa batas
    room  : (appId, n) => bankRoom(appId, n),      // berapa dari n item yang masih muat
    pageCount : (appId) => pageCount(appId),       // jumlah rumus member di halaman ini
  };

  // ── Indikator member aktif di pojok kanan bawah ─
  function showBankIndicator(){
    const mid = currentMemberId();
    if(mid==='guest') return;
    const div = document.createElement('div');
    div.id = 'wb-bank-indicator';
    div.style.cssText = [
      'position:fixed','bottom:10px','right:10px','z-index:9999',
      'background:rgba(22,29,53,.92)','border:1px solid #243154',
      'border-radius:8px','padding:5px 10px','font-size:11px',
      'color:#22e8ff','font-weight:700','pointer-events:none',
      'box-shadow:0 2px 8px rgba(0,0,0,.3)'
    ].join(';');
    div.textContent = '💾 Bank: ...';
    document.body.appendChild(div);
    function update(){
      const lim = memberBankLimit();
      const tot = Object.values(_syncCache).reduce((n,a)=>n+(a?a.length:0),0);
      div.textContent = '💾 Bank: ' + tot + (lim ? '/' + lim : '') + ' rumus';
    }
    update();
    setInterval(update, 2000);
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', showBankIndicator);
  } else {
    showBankIndicator();
  }

})(window);
