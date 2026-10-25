"use strict";
const profile="zoltan.ppp";
let lastPayload="",lastSent=0;
function collect() {
  let id,value=null;
  if(location.hostname==="grok.com"&&location.pathname.replace(/\/$/,"")==="/dashboard/usage") {
    id="grok";
    const meter=document.querySelector('[aria-valuenow][aria-label="Weekly included usage"]');
    if(meter)value=MiniPiExtract.remaining(meter.getAttribute("aria-valuenow"));
  } else if(location.hostname==="www.tiktok.com"&&location.pathname.replace(/\/$/,"")===`/@${profile}`) {
    id="tiktok";
    const count=document.querySelector('[data-e2e="followers-count"]');
    if(count)value=MiniPiExtract.exactCount(count.textContent);
  } else if(location.hostname==="www.instagram.com"&&location.pathname.replace(/\/$/,"")===`/${profile}`) {
    id="instagram";
    for(const link of document.querySelectorAll('a')) {
      const text=(link.innerText||link.getAttribute("aria-label")||"").trim();
      const match=text.match(/^([\d\s\u00a0\u202f.,]+)\s*(?:követő|followers?)$/i);
      if(match){value=MiniPiExtract.exactCount(match[1]);if(value!==null)break;}
    }
  }
  if(!id||value===null)return;
  const payload=JSON.stringify({id,value});
  if(payload===lastPayload&&Date.now()-lastSent<90000)return;
  lastPayload=payload;lastSent=Date.now();
  chrome.runtime.sendMessage({type:"counter",card:{id,value}},()=>void chrome.runtime.lastError);
}
// Poll only rendered counters; no cookies, storage, network interception or account data.
setTimeout(collect,1000);
setInterval(collect,15000);
