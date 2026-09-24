/**
 * wb-member-bank.js
 * ─────────────────────────────────────────────────────────────────────
 * Helper bank rumus PER-MEMBER untuk WongBagus Prediction.
 *
 * PENTING: key localStorage di sini SENGAJA dibuat SAMA PERSIS dengan
 * yang dipakai panel admin di index.html (wbBankKey / wbGetMemberBank /
 * wbSetMemberBank), supaya tab "💾 Bank Member" di admin bisa membaca
 * data yang disimpan dari halaman scan. Kalau skema key beda, admin
 * akan selalu lihat 0 rumus walau member sudah menyimpan banyak.
 *
 *   Bank utama (default)  → wb_bank_<memberId>
 *   Bank tambahan (opsional, dipakai fitur multi-bank di scan3)
 *                          → wb_bank_<memberId>__<bankId>
 *   Kalau belum login, memberId = "guest".
 *
 * Cara pakai di halaman scan:
 *   WB_BANK.get()          → ambil bank utama member yang sedang login
 *   WB_BANK.set(data)      → simpan bank utama member yang sedang login
 *   WB_BANK.add(item)      → tambah 1 item ke depan bank utama
 *   WB_BANK.clear()        → kosongkan bank utama member ini
 *   WB_BANK.currentId()    → ID member yang sedang login ("guest" kalau belum login)
 * ─────────────────────────────────────────────────────────────────────
 */

(function(global){

  // ── Ambil member yang sedang login dari localStorage ─────────────
  function currentMemberId(){
    try{
      const raw = localStorage.getItem('wb_logged_member');
      if(!raw) return 'guest';
      const obj = JSON.parse(raw);
      // Pakai id/phone sebagai key utama agar konsisten lintas session & lintas halaman
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

  // ── Bangun localStorage key — HARUS sama dengan wbBankKey() di index.html ──
  function bankKey(memberId, bankId){
    const mid = memberId || currentMemberId();
    if(!bankId || bankId === 'utama') return 'wb_bank_' + mid;
    return 'wb_bank_' + mid + '__' + bankId;
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

  // ── Daftar bank tambahan yang dimiliki member ini (di luar "utama") ─
  function bankListIds(memberId){
    const mid  = memberId || currentMemberId();
    const pfx  = 'wb_bank_' + mid + '__';
    const ids  = ['utama'];
    for(let i=0; i<localStorage.length; i++){
      const k = localStorage.key(i);
      if(k && k.startsWith(pfx)){
        ids.push(k.slice(pfx.length));
      }
    }
    return ids;
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

  // ── Public API (urutan parameter set/add sengaja disamakan dengan
  //    window.WB_BANK versi index.html: data dulu, baru memberId) ────
  global.WB_BANK = {
    currentId : currentMemberId,
    currentName: currentMemberName,
    get : (memberId, bankId) => bankGet(memberId, bankId),
    set : (data, memberId, bankId) => bankSet(data, memberId, bankId),
    add : (item, memberId, bankId) => bankAdd(item, memberId, bankId),
    clear : (memberId, bankId) => bankClear(memberId, bankId),
    listIds : (memberId) => bankListIds(memberId),
    countAll : (memberId) => bankCountAll(memberId),
    copyTo : (fromBankId, toBankId, memberId) => bankCopyTo(fromBankId, toBankId, memberId),
    key : (memberId, bankId) => bankKey(memberId, bankId),
  };

  // ── Indikator member aktif di pojok kanan bawah (opsional) ────────
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
    function update(){ div.textContent = '💾 Bank: ' + bankCountAll(mid) + ' rumus'; }
    update();
    document.body.appendChild(div);
    setInterval(update, 3000);
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', showBankIndicator);
  } else {
    showBankIndicator();
  }

})(window);
