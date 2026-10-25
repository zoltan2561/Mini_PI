"use strict";
const pages={grok:"https://grok.com/dashboard/usage",instagram:"https://www.instagram.com/zoltan.ppp/",tiktok:"https://www.tiktok.com/@zoltan.ppp"};
const defaultConfig={url:"http://192.168.50.246:8080",token:"",enabled:true};
async function config() { return {...defaultConfig,...(await chrome.storage.local.get("config")).config}; }
async function status(id,result) {
  await chrome.storage.local.set({["status_"+id]:{...result,checkedAt:new Date().toISOString()}});
}
async function initialize() {
  if(!(await chrome.storage.local.get("config")).config) {
    try {
      const response=await fetch(chrome.runtime.getURL("bootstrap.json"));
      if(response.ok)await chrome.storage.local.set({config:{...defaultConfig,...await response.json()}});
    } catch(_) {}
  }
  await chrome.alarms.create("mini-pi-refresh",{periodInMinutes:2});
  await refresh();
}
async function refresh() {
  const cfg=await config();if(!cfg.enabled||!cfg.token)return;
  const saved=(await chrome.storage.local.get("tabs")).tabs||{};
  for(const [id,url] of Object.entries(pages)) {
    let tab;
    try {if(saved[id])tab=await chrome.tabs.get(saved[id]);}catch(_){}
    if(!tab||!tab.url?.startsWith(url)) {
      tab=await chrome.tabs.create({url,active:false});saved[id]=tab.id;
    } else if(!tab.active) {
      await chrome.tabs.reload(tab.id);
    }
  }
  await chrome.storage.local.set({tabs:saved});
}
chrome.runtime.onInstalled.addListener(()=>initialize());
chrome.runtime.onStartup.addListener(()=>initialize());
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name==="mini-pi-refresh")refresh().catch(()=>{});});
chrome.action.onClicked.addListener(()=>chrome.runtime.openOptionsPage());
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{
  if(message.type==="refresh"&&sender.url?.startsWith(chrome.runtime.getURL(""))) {
    refresh().then(()=>sendResponse({ok:true}));return true;
  }
  const card=message.card;
  if(message.type!=="counter"||sender.id!==chrome.runtime.id||!card||!Object.hasOwn(pages,card.id))return;
  const actual=new URL(sender.url||"about:blank"),expected=new URL(pages[card.id]);
  if(actual.origin!==expected.origin||actual.pathname.replace(/\/$/,"")!==expected.pathname.replace(/\/$/,""))return;
  if(typeof card.value!=="number"||!Number.isFinite(card.value)||card.value<0||card.value>(card.id==="grok"?100:1e15))return;
  (async()=>{
    const cfg=await config();if(!cfg.enabled||!cfg.token)return;
    if(!/^http:\/\/(?:192\.168\.50\.246|zolitft\.local):8080$/.test(cfg.url))throw new Error("address");
    const response=await fetch(cfg.url+"/api/ingest/browser",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+cfg.token},body:JSON.stringify({cards:[{id:card.id,value:card.value}]}),signal:AbortSignal.timeout(10000)});
    if(!response.ok)throw new Error("http "+response.status);
    await status(card.id,{ok:true,value:card.value});sendResponse({ok:true});
  })().catch(async()=>{await status(card.id,{ok:false,error:"A Pi nem fogadta az adatot. Ellenőrizd a címet, a kulcsot és a hálózatot."});sendResponse({ok:false});});
  return true;
});
