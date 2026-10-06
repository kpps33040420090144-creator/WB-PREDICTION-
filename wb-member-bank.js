/**
 * wb-member-bank.js
 * ---------------------------------------------------------------
 * Bank rumus PER-MEMBER dan PER-HALAMAN (scan1..scan5), disimpan di server
 * (Cloudflare Worker). Satu data per member per halaman scan:
 *   key = bank-<halaman>-<idMember>   isi = { "<appId>": [...] }
 * Jadi member tidak berebut ruang, dan simpan satu member tidak menimpa member lain.
 *
 * WAJIB: wb-config.js (window.WB_STORE) dimuat SEBELUM file ini.
 *
 * Cara pakai di halaman scan (ASYNC, kecuali layer sinkron WB_BANK.*Sync):
 *   WB_BANK.get('scan1').then(data => ...)
 *   await WB_BANK.set(data, 'scan1')
 *   WB_BANK.currentId()   <- sinkron (baca sesi login lokal)
 * ---------------------------------------------------------------
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
    const c = global.WB_STORE;
    if(!c || !c.worker || !c.account){
      throw new Error('WB_STORE belum di-set. Cek wb-config.js sebelum wb-member-bank.js di <head>.');
    }
    return { base: c.worker.replace(/\/+$/,'') + '/' + c.account };
  }

  // appId bisa 'scan1'..'scan5', atau varian scan3 spt 'scan3_myBank' —
  // semuanya tetap satu HALAMAN yang sama ('scan3'), jadi satu bin yang sama.
  function pageOf(appId){
    const m = /^scan[1-5]/.exec(appId || '');
    return m ? m[0] : 'default';
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

  // ══════════════════════════════════════════════════════════════
  // TREK DISIMPAN LENGKAP, TAPI RINGKAS
  // Dulu trek dipotong paksa jadi 3 baris terakhir tiap kali disimpan ke
  // server, jadi setelah muat ulang "Trek 18x" cuma tampil 3 baris.
  // Sekarang semua baris trek disimpan, dalam bentuk ringkas (kunci baris
  // ditulis sekali, tiap baris jadi larik pendek; "pred" dibuang kalau bisa
  // diturunkan dari "predStr"). Ukurannya kira-kira sepertiga dari bentuk lama.
  // Bin tiap halaman dipakai BERSAMA semua member (limit 100KB), jadi kalau
  // tetap kepenuhan, baris trek milik member ini baru dipangkas bertahap
  // (12 → 8 → 5 → 3 baris terakhir) dan member diberi tahu.
  // Data lama (belum ringkas / sudah terpotong) tetap terbaca apa adanya.
  // ══════════════════════════════════════════════════════════════
  const ROW_CAPS = [Infinity, 12, 8, 5, 3];
  const MAX_BYTES = 190000;  // batas ukuran per member per scan (Worker maks 200KB)
  function predOf(predStr){ return (predStr && predStr !== '??') ? String(predStr).split('').map(Number) : []; }
  function packItem(it, cap){
    if(!it || !Array.isArray(it.trekRows) || !it.trekRows.length) return it;
    let rows = it.trekRows;
    if(rows.length > cap) rows = rows.slice(-cap);
    const first = rows[0];
    const flat = first && typeof first==='object' && !Array.isArray(first);
    let keys = flat ? Object.keys(first) : [];
    const uniform = flat && rows.every(r => r && typeof r==='object' && !Array.isArray(r) && Object.keys(r).length===keys.length && keys.every(k => k in r));
    if(!uniform) return rows===it.trekRows ? it : { ...it, trekRows: rows };   // bentuk tak dikenal: simpan apa adanya
    let predIdx = -1;
    if(keys.includes('pred') && keys.includes('predStr') && rows.every(r => Array.isArray(r.pred) && JSON.stringify(r.pred) === JSON.stringify(predOf(r.predStr)))){
      predIdx = keys.indexOf('pred');           // "pred" bisa diturunkan dari predStr → tidak disimpan
      keys = keys.filter(k => k !== 'pred');
    }
    const rest = { ...it }; delete rest.trekRows;
    rest._tk = keys; if(predIdx >= 0) rest._tp = predIdx;
    rest._tr = rows.map(r => keys.map(k => r[k]));
    return rest;
  }
  function unpackItem(it){
    if(!it || !Array.isArray(it._tr) || !Array.isArray(it._tk)) return it;   // data lama dibiarkan
    const keys = it._tk.slice(), pi = (typeof it._tp === 'number') ? it._tp : -1;
    const rest = { ...it }; delete rest._tk; delete rest._tr; delete rest._tp;
    if(pi >= 0) keys.splice(pi, 0, 'pred');       // kembalikan posisi asli "pred"
    rest.trekRows = it._tr.map(t => {
      const r = {}; let j = 0;
      keys.forEach(k => { r[k] = (k==='pred' && pi>=0) ? null : t[j++]; });
      if(pi >= 0) r.pred = predOf(r.predStr);
      return r;
    });
    return rest;
  }
  function packArr(arr, cap){ return Array.isArray(arr) ? arr.map(it => packItem(it, cap)) : arr; }
  function unpackArr(arr){ return Array.isArray(arr) ? arr.map(unpackItem) : arr; }

  // ══════════════════════════════════════════════════════════════
  // BATAS RUMUS PER MEMBER — diatur admin di Edit Akun (field bankLimit
  // di data member). Berlaku PER HALAMAN scan (scan1..scan5 dihitung
  // sendiri-sendiri; sub-bank satu halaman, mis. scan3_xxx, dijumlah).
  // Admin tanpa batas. Kosong di admin = pakai BANK_LIMIT_DEFAULT.
  // Tiap member punya data sendiri di server (maks 190KB per halaman scan).
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
  // PENYIMPANAN (Cloudflare Worker) - satu data per member per halaman scan.
  // ══════════════════════════════════════════════════════════════
  const PAGES = ['scan1','scan2','scan3','scan4','scan5'];
  const safeId = s => String(s).replace(/[^\w-]/g, '_');
  function bankKey(appId, mid){ return 'bank-' + pageOf(appId) + '-' + safeId(mid); }
  function bankUrl(appId, mid){ return cfg().base + '/' + bankKey(appId, mid); }

  // STRICT: gagal baca = LEMPAR error (jangan diam-diam balikin kosong, nanti menimpa data)
  async function fetchBank(appId, mid){
    const r = await fetch(bankUrl(appId, mid));
    if(!r.ok) throw new Error('Gagal ambil bank (HTTP '+r.status+')');
    const rec = await r.json();
    return (rec && typeof rec==='object' && !Array.isArray(rec)) ? rec : {};
  }
  async function saveBank(appId, mid, rec){
    const r = await fetch(bankUrl(appId, mid), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rec)
    });
    if(!r.ok) throw new Error('Gagal simpan bank (HTTP '+r.status+')');
  }

  const _pageCache = {};    // "halaman|member" -> record
  const _pagePromise = {};
  function loadBankCached(appId, mid){
    const ck = pageOf(appId) + '|' + mid;
    if(_pageCache[ck]) return Promise.resolve(_pageCache[ck]);
    if(!_pagePromise[ck]) _pagePromise[ck] = fetchBank(appId, mid)
      .then(d=>{ _pageCache[ck]=d; return d; })
      .catch(e=>{ delete _pagePromise[ck]; throw e; });
    return _pagePromise[ck];
  }

  async function bankGetStrict(appId, memberId){
    const mid = memberId || currentMemberId();
    const app = appId || 'default';
    const rec = await loadBankCached(app, mid);
    return unpackArr(rec[app] || []);
  }
  async function bankGet(appId, memberId){
    try{ return await bankGetStrict(appId, memberId); }
    catch(e){ console.warn('[WB_BANK] gagal ambil bank:', e); return []; }
  }

  async function bankSet(data, appId, memberId){
    const mid = memberId || currentMemberId();
    const app = appId || 'default';
    const rec = await fetchBank(app, mid); // FRESH
    let fit = false, usedCap = Infinity;
    for(const cap of ROW_CAPS){
      if(data===null) delete rec[app]; else rec[app] = packArr(data || [], cap);
      usedCap = cap;
      if(data===null || JSON.stringify(rec).length <= MAX_BYTES){ fit = true; break; }
    }
    if(!fit) throw new Error('Bank kepenuhan (batas ukuran): data scan ini terlalu besar');
    await saveBank(app, mid, rec);
    _pageCache[pageOf(app) + '|' + mid] = rec;
    if(usedCap !== Infinity) bankToast('ℹ️ Bank besar: detail trek disimpan maks '+usedCap+' putaran terakhir di server (angka Trek tetap utuh).');
  }

  async function bankAdd(item, appId, memberId){
    const bank = await bankGetStrict(appId, memberId);   // strict: gagal baca = batal, bukan menimpa
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
    // Tanya ke SEMUA halaman (scan1..scan5), supaya admin bisa lihat total rumus member lain
    for(const pid of PAGES){
      try{
        const rec = await loadBankCached(pid, mid);
        Object.keys(rec).forEach(a=>apps.add(a));
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
        const rec = await loadBankCached(appId, mid);
        Object.keys(rec).forEach(a=>{ _syncCache[a] = unpackArr(rec[a] || []); });
        st.ok = true;
      }
    }catch(e){
      console.warn('[WB_BANK] gagal muat bank:', e);
      bankToast('⚠️ Bank gagal dimuat dari server. Cek koneksi lalu refresh.');
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
        if(/kepenuhan|413|terlalu besar/i.test(msg)) bankToast('⚠️ Bank kepenuhan (batas ukuran). Hapus beberapa rumus lama lalu coba lagi.');
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
