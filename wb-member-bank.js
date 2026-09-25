/**
 * wb-member-bank.js
 * ─────────────────────────────────────────────────────────────────────
 * Helper bank rumus PER-MEMBER *dan* PER-APLIKASI (scan1..scan5) untuk
 * WongBagus Prediction.
 *
 * Setiap file scan punya bank sendiri-sendiri per member — bank rumus
 * di scan1 TIDAK campur dengan bank di scan2/scan3/dst, walau member
 * yang login sama. Admin di index.html tetap bisa lihat & hapus
 * total rumus (gabungan semua scan) tiap member lewat tab "Bank Member".
 *
 *   Key localStorage: wb_bank_<memberId>__<appId>
 *   Contoh: wb_bank_628123456789__scan1, wb_bank_628123456789__scan3
 *   Kalau belum login, memberId = "guest".
 *
 * Cara pakai di halaman scan (WAJIB isi appId sesuai nama filenya!):
 *   WB_BANK.get('scan1')          → ambil bank scan1 milik member yang login
 *   WB_BANK.set(data, 'scan1')    → simpan bank scan1 milik member yang login
 *   WB_BANK.add(item, 'scan1')    → tambah 1 item ke bank scan1
 *   WB_BANK.clear('scan1')        → kosongkan bank scan1 member ini
 *   WB_BANK.currentId()           → ID member yang sedang login ("guest" kalau belum login)
 * ─────────────────────────────────────────────────────────────────────
 */

(function(global){

  // ── Ambil member yang sedang login dari localStorage ─────────────
  function currentMemberId(){
    try{
      const raw = localStorage.getItem('wb_logged_member');
      if(!raw) return 'guest';
      const obj = JSON.parse(raw);
      return (obj.id || obj.phone || 'guest');
    }catch(e){ return 'guest'; }
  }

  function currentMemberName(){
    try{
      const raw = localStorage.getItem('wb_logged_member');
      if(!raw) return 'Guest';
      return JSON.parse(raw).name || 'Member';
    }catch(e){ return 'Member'; }
  }

  // ── Bangun localStorage key: wb_bank_<memberId>__<appId> ──────────
  function bankKey(appId, memberId){
    const mid = memberId || currentMemberId();
    const app = appId || 'default';
    return 'wb_bank_' + mid + '__' + app;
  }

  // ── CRUD dasar (appId WAJIB — beda file scan, beda bank) ──────────
  function bankGet(appId, memberId){
    try{ return JSON.parse(localStorage.getItem(bankKey(appId,memberId)) || '[]'); }
    catch(e){ return []; }
  }

  function bankSet(data, appId, memberId){
    try{ localStorage.setItem(bankKey(appId,memberId), JSON.stringify(data||[])); }
    catch(e){ console.warn('[WB_BANK] Gagal simpan bank:', e); }
  }

  function bankAdd(item, appId, memberId){
    const bank = bankGet(appId, memberId);
    const isDup = bank.some(b =>
      b.formula === item.formula &&
      (b.wbId||b.pasaran) === (item.wbId||item.pasaran) &&
      b.jenis === item.jenis
    );
    if(isDup) return false;
    bank.unshift({...item, savedAt: new Date().toISOString()});
    bankSet(bank, appId, memberId);
    return true;
  }

  function bankClear(appId, memberId){
    try{ localStorage.removeItem(bankKey(appId,memberId)); }catch(e){}
  }

  // ── Daftar appId (scan1, scan2, ...) yang punya data untuk member ini ─
  function bankListApps(memberId){
    const mid = memberId || currentMemberId();
    const pfx = 'wb_bank_' + mid + '__';
    const apps = [];
    for(let i=0; i<localStorage.length; i++){
      const k = localStorage.key(i);
      if(k && k.startsWith(pfx)) apps.push(k.slice(pfx.length));
    }
    return apps;
  }

  // ── Total rumus member ini digabung dari SEMUA scan (buat admin) ──
  function bankCountAll(memberId){
    return bankListApps(memberId).reduce((sum, app) => sum + bankGet(app, memberId).length, 0);
  }

  // ── Public API ──────────────────────────────────────────────────
  global.WB_BANK = {
    currentId : currentMemberId,
    currentName: currentMemberName,
    get : (appId, memberId) => bankGet(appId, memberId),
    set : (data, appId, memberId) => bankSet(data, appId, memberId),
    add : (item, appId, memberId) => bankAdd(item, appId, memberId),
    clear : (appId, memberId) => bankClear(appId, memberId),
    listApps : (memberId) => bankListApps(memberId),
    countAll : (memberId) => bankCountAll(memberId),
    key : (appId, memberId) => bankKey(appId, memberId),
  };

  // ── Indikator member aktif di pojok kanan bawah (opsional) ────────
  function showBankIndicator(appId){
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
    function update(){ div.textContent = '\u{1F4BE} Bank: ' + bankGet(appId).length + ' rumus'; }
    update();
    document.body.appendChild(div);
    setInterval(update, 3000);
  }

  // Deteksi appId dari nama file halaman ini sendiri (scan1.html -> "scan1")
  const AUTO_APP_ID = (function(){
    try{
      const m = location.pathname.match(/([a-zA-Z0-9_-]+)\.html?$/);
      return m ? m[1] : null;
    }catch(e){ return null; }
  })();

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', () => showBankIndicator(AUTO_APP_ID));
  } else {
    showBankIndicator(AUTO_APP_ID);
  }

})(window);
