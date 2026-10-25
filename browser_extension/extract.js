/* Pure parsers: never turn an absent or rounded count into an exact zero/count. */
(() => {
  function exactCount(text) {
    const value=String(text||"").trim().replace(/[\s\u00a0\u202f]/g,"");
    if(!/^(?:\d+|\d{1,3}(?:[,.]\d{3})+)$/.test(value))return null;
    const number=Number(value.replace(/[,.]/g,""));
    return Number.isSafeInteger(number)&&number>=0?number:null;
  }
  function remaining(used) {
    if(used===null||used===""||used===undefined)return null;
    const number=Number(used);
    return Number.isFinite(number)&&number>=0&&number<=100?Math.round((100-number)*100)/100:null;
  }
  const api={exactCount,remaining};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  else globalThis.MiniPiExtract=api;
})();
