const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=name=>fs.readFileSync(path.join(__dirname,'../browser_extension',name),'utf8');

async function main(){
  const stored={config:{url:'http://192.168.50.246:8080',token:'test-only-token',enabled:true}};
  let display={cards:[{id:'grok',enabled:1}]},offline=false,posts=0,reads=0;
  const created=[],reloaded=[],tabs=new Map(),listeners={};
  const storage={
    get:async keys=>Object.fromEntries((typeof keys==='string'?[keys]:keys).map(k=>[k,stored[k]])),
    set:async data=>Object.assign(stored,data)
  };
  const context=vm.createContext({URL,AbortSignal,chrome:{
    storage:{local:storage},alarms:{create:async()=>{},onAlarm:{addListener:()=>{}}},
    tabs:{get:async id=>tabs.get(id),create:async data=>{created.push(data.url);const tab={id:tabs.size+1,url:data.url,active:false};tabs.set(tab.id,tab);return tab;},reload:async id=>reloaded.push(id)},
    action:{onClicked:{addListener:()=>{}}},
    runtime:{id:'test-extension',getURL:p=>'chrome-extension://test-extension/'+p,
      onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},
      onMessage:{addListener:fn=>listeners.message=fn},openOptionsPage:()=>{}}
  },fetch:async(url,options)=>{
    if(url.endsWith('/api/display')){reads++;if(offline)throw Error('offline');return {ok:true,json:async()=>display};}
    assert.ok(url.endsWith('/api/ingest/browser'));
    assert.equal(options.method,'POST');posts++;return {ok:true};
  }});
  vm.runInContext(source('background.js'),context);
  const refresh=()=>vm.runInContext('refresh()',context);
  await refresh();
  assert.deepEqual(created,['https://grok.com/dashboard/usage']);
  assert.equal(stored.status_instagram.paused,true);
  assert.equal(stored.status_tiktok.paused,true);
  await refresh();
  assert.deepEqual(reloaded,[1]);
  display.cards.push({id:'instagram',enabled:1});
  await refresh();
  assert.equal(created.length,2);
  assert.ok(created[1].includes('instagram.com'));
  display.cards=[{id:'grok',enabled:1},{id:'instagram',enabled:0}];
  const before=reloaded.length;
  await refresh();
  assert.deepEqual(reloaded.slice(before),[1]);
  const counter=(id,url)=>new Promise(resolve=>{
    const result=listeners.message({type:'counter',card:{id,value:12}},
      {id:'test-extension',url},resolve);
    assert.equal(result,true);
  });
  assert.equal((await counter('instagram','https://www.instagram.com/zoltan.ppp/')).paused,true);
  assert.equal(posts,0);
  assert.equal((await counter('grok','https://grok.com/dashboard/usage')).ok,true);
  assert.equal(posts,1);
  offline=true;
  const counts=[created.length,reloaded.length];
  await refresh();
  assert.deepEqual([created.length,reloaded.length],counts);
  assert.equal(stored.enabledCards.length,0);
  assert.equal((await counter('grok','https://grok.com/dashboard/usage')).ok,false);
  assert.equal(posts,1);
  offline=false;display={};
  await refresh();
  assert.deepEqual([created.length,reloaded.length],counts);
  stored.config.enabled=false;
  const previousReads=reads;
  await refresh();
  assert.equal(reads,previousReads);

  let polled=0,sent=0;
  stored.config.enabled=true;stored.enabledCards=['grok'];
  const content=vm.createContext({chrome:{storage:{local:storage},runtime:{sendMessage:()=>sent++}},
    location:{hostname:'www.tiktok.com',pathname:'/@zoltan.ppp'},
    document:{querySelector:()=>{polled++;return {textContent:'123'};}},
    MiniPiExtract:{exactCount:Number},setTimeout:()=>{},setInterval:()=>{}});
  vm.runInContext(source('content.js'),content);
  await vm.runInContext('collect()',content);
  assert.equal(polled,0);assert.equal(sent,0);
  stored.enabledCards=['tiktok'];
  await vm.runInContext('collect()',content);
  assert.equal(polled,1);assert.equal(sent,1);
  console.log('Browser refresh gating passed: hidden cards, re-enable, ingestion, offline, invalid state, disabled collector, content polling.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
