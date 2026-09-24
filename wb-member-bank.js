/**
 * wb-member-bank.js
 * ─────────────────────────────────────────────────────────────────────
 * Helper bank rumus PER-MEMBER untuk WongBagus Prediction.
 *
 * Cara pakai di setiap halaman scan (scan1.html … scan5.html):
 *   1. Tambahkan tag di <head>:
 *      <script src="wb-member-bank.js"></script>
 *
 *   2. Ganti semua getBankData() / setBankData() pakai:
 *      WB_BANK.get()          → ambil bank member yg sedang login
 *      WB_BANK.set(data)      → simpan bank member yg sedang login
 *      WB_BANK.add(item)      → tambah 1 item ke depan bank member
 *      WB_BANK.clear()        → kosongkan bank member ini
 *
 *   3. Untuk multi-bank (Bank Utama / Bank 2 / dst.) gunakan:
 *      WB_BANK.get(null, 'utama')     → bank "utama" milik member ini
 *      WB_BANK.set(data, null, 'utama')
 *
 * Key localStorage yang dipakai:
 *   wb_bank_<memberId>_<bankId>
 *   Kalau belum login, pakai memberId = "guest".
 * ─────────────────────────────────────────────────────────────────────
 */

(function(global){

  // ── Ambil member yang sedang login dari localStorage ─────────────
  function currentMemberId(){
    try{
      const raw = localStorage.getItem('wb_logged_member');
      if(!raw) return 'guest';
      const obj = JSON.parse(raw);
      // Pakai phone sebagai key utama agar konsisten lintas session
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

  // ── Bangun localStorage key ───────────────────────────────────────
  // format: wb_bank_<memberId>_<bankId>
  function bankKey(memberId, bankId){
    const mid = memberId || currentMemberId();
    const bid = bankId  || 'utama';
    // Sanitasi key: hilangkan karakter aneh
    return 'wb_bank_' + mid.replace(/[^a-z0-9_-]/gi,'_') + '_' + bid;
  }

  // ── CRUD dasar ────────────────────────────────────────────────────
  function bankGet(memberId, bankId){
    try{ return JSON.parse(localStorage.getItem(bankKey(memberId,bankId)) || '[]'); }
    catch(e){ return []; }
  }

  function bankSet(data, memberId, bankId){
    try{ localStorage.setItem(bankKey(memberId,bankId), JSON.stringify(data||[])); }
    catch(e){ console.warn('[WB_BANK] Gagal simpan bank:', e); }
  }

  function bankAdd(item, memberId, bankId){
    const bank = bankGet(memberId, bankId);
    // Hindari duplikat berdasarkan formula + pasaran + jenis
    const isDup = bank.some(b =>
      b.formula === item.formula &&
      (b.wbId||b.pasaran) === (item.wbId||item.pasaran) &&
      b.jenis === item.jenis
    );
    if(isDup) return false;
    bank.unshift({...item, savedAt: new Date().toISOString()});
    bankSet(bank, memberId, bankId);
    return true;
  }

  function bankClear(memberId, bankId){
    try{ localStorage.removeItem(bankKey(memberId,bankId)); }catch(e){}
  }

  // ── Ambil daftar bank yang dimiliki member ini ─────────────────────
  // (semua key yang diawali wb_bank_<memberId>_)
  function bankListIds(memberId){
    const mid  = memberId || currentMemberId();
    const pfx  = 'wb_bank_' + mid.replace(/[^a-z0-9_-]/gi,'_') + '_';
    const ids  = [];
    for(let i=0; i<localStorage.length; i++){
      const k = localStorage.key(i);
      if(k && k.startsWith(pfx)){
        ids.push(k.slice(pfx.length));
      }
    }
    return ids.length ? ids : ['utama'];
  }

  // ── Hitung total rumus semua bank member ini ───────────────────────
  function bankCountAll(memberId){
    return bankListIds(memberId).reduce((sum, bid)=> sum + bankGet(memberId,bid).length, 0);
  }

  // ── Copy bank ke bank lain ─────────────────────────────────────────
  function bankCopyTo(fromBankId, toBankId, memberId){
    const src = bankGet(memberId, fromBankId);
    const dst = bankGet(memberId, toBankId);
    let added = 0;
    src.forEach(item=>{
      const isDup = dst.some(b=>
        b.formula===(item.formula) &&
        (b.wbId||b.pasaran)===(item.wbId||item.pasaran) &&
        b.jenis===item.jenis
      );
      if(!isDup){ dst.push({...item}); added++; }
    });
    bankSet(dst, memberId, toBankId);
    return added;
  }

  // ── Public API ────────────────────────────────────────────────────
  global.WB_BANK = {
    /** Siapa yang login sekarang */
    currentId : currentMemberId,
    currentName: currentMemberName,

    /** Ambil bank (default: utama, member yg login) */
    get : (memberId, bankId) => bankGet(memberId, bankId),

    /** Simpan bank */
    set : (data, memberId, bankId) => bankSet(data, memberId, bankId),

    /** Tambah 1 item, return false kalau duplikat */
    add : (item, memberId, bankId) => bankAdd(item, memberId, bankId),

    /** Kosongkan bank */
    clear : (memberId, bankId) => bankClear(memberId, bankId),

    /** Daftar semua bankId member ini */
    listIds : (memberId) => bankListIds(memberId),

    /** Total rumus semua bank member ini */
    countAll : (memberId) => bankCountAll(memberId),

    /** Copy isi satu bank ke bank lain */
    copyTo : (fromBankId, toBankId, memberId) => bankCopyTo(fromBankId, toBankId, memberId),

    /** Key lengkap localStorage (untuk debug / integrasi lanjut) */
    key : (memberId, bankId) => bankKey(memberId, bankId),
  };

  // ── Patch otomatis fungsi umum yang sering dipakai halaman scan ───
  // Kalau halaman scan sudah punya getBankData / setBankData lama
  // (memakai key tanpa member ID), patch ini override ke versi per-member.
  // Patch ini AMAN — hanya override kalau fungsi tersebut sudah ada.
  function patchLegacyFunctions(){
    if(typeof global.getBankData === 'function'){
      global.getBankData = function(bankId){
        return bankGet(null, bankId || 'utama');
      };
    }
    if(typeof global.setBankData === 'function'){
      global.setBankData = function(bankId, data){
        bankSet(data, null, bankId || 'utama');
      };
    }
    // Juga patch saveToBankObj kalau ada (dari scan utama)
    if(typeof global.saveToBankObj === 'function'){
      const _orig = global.saveToBankObj;
      global.saveToBankObj = function(c){
        // Redirect ke bank member yang login
        const bank = bankGet(null, 'utama');
        const isDup = bank.some(b=>b.formula===c.formula&&(b.wbId||b.pasaran)===(c.wbId||c.pasaran)&&b.jenis===c.jenis);
        if(isDup){ if(typeof toast==='function') toast('⚡ Rumus ini sudah ada di bank!','warn'); return; }
        bank.unshift({
          id:'rms_'+Date.now(),
          formula:c.formula, cols:Array.isArray(c.cols)?c.cols:null,
          e1:c.e1,o1:c.o1,e2:c.e2,
          e3:c.e3||'-',o2:c.o2||'none',
          e4:c.e4||'-',o3:c.o3||'none',
          e5:c.e5||'-',o4:c.o4||'none',
          e6:c.e6||'-',o5:c.o5||'none',
          mod:c.mod, wbId:c.wbId, jenis:c.jenis,
          nDigit:c.nDigit, limit:c.limit,
          acc:c.acc!=null?c.acc:(c.hitPct!=null?c.hitPct/100:0),
          predNow:c.predNow, maxPatah:c.maxP||0, hari:'',
          savedAt:new Date().toISOString()
        });
        bankSet(bank, null, 'utama');
        if(typeof toast==='function') toast('✅ Disimpan ke Bank Rumus!');
      };
    }
  }

  // Jalankan patch setelah halaman selesai load
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', patchLegacyFunctions);
  } else {
    patchLegacyFunctions();
  }

  // ── Indikator member aktif di pojok kanan bawah (opsional) ────────
  // Tampilkan "💾 Bank: X rumus" agar member tahu bank mereka aktif.
  function showBankIndicator(){
    const mid = currentMemberId();
    if(mid==='guest') return;
    const total = bankCountAll(mid);
    const div = document.createElement('div');
    div.id = 'wb-bank-indicator';
    div.style.cssText = [
      'position:fixed','bottom:10px','right:10px','z-index:9999',
      'background:rgba(22,29,53,.92)','border:1px solid #243154',
      'border-radius:8px','padding:5px 10px','font-size:11px',
      'color:#22e8ff','font-weight:700','pointer-events:none',
      'box-shadow:0 2px 8px rgba(0,0,0,.3)'
    ].join(';');
    div.textContent = '💾 Bank: ' + total + ' rumus';
    document.body.appendChild(div);
    // Update otomatis setiap 3 detik
    setInterval(()=>{
      const t = bankCountAll(mid);
      div.textContent = '💾 Bank: ' + t + ' rumus';
    }, 3000);
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', showBankIndicator);
  } else {
    showBankIndicator();
  }

})(window);
