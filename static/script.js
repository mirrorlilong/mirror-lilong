(function(){
  var d=document.getElementById('today');
  if(d){try{d.textContent=new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Kolkata'});}catch(e){}}
  var b=document.getElementById('menuBtn'),n=document.getElementById('mainNav');
  if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');b.setAttribute('aria-label',o?'Close sections menu':'Open sections menu');});}
})();

(function(){
  var sl=document.querySelector('[data-slider]');if(!sl)return;
  var tr=sl.querySelector('.ls-track'),slides=tr.children,n=slides.length,dots=sl.querySelectorAll('.ls-dots button');
  if(n<2)return;
  var rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DELAY=5000,timer=null,hold=0,cur=0,st=null;
  function idx(){return Math.max(0,Math.min(n-1,Math.round(tr.scrollLeft/(tr.clientWidth||1))));}
  function mark(){cur=idx();for(var k=0;k<dots.length;k++){if(k===cur)dots[k].setAttribute('aria-current','true');else dots[k].removeAttribute('aria-current');}
    for(var j=0;j<n;j++){var a=slides[j].querySelector('a');if(a){if(j===cur)a.removeAttribute('tabindex');else a.setAttribute('tabindex','-1');}}}
  function go(k){k=(k%n+n)%n;tr.scrollTo({left:k*tr.clientWidth,behavior:rm?'auto':'smooth'});}
  function stop(){if(timer){clearTimeout(timer);timer=null;}}
  function plan(){stop();if(rm||hold>0||document.hidden)return;timer=setTimeout(function(){go(idx()+1);},DELAY);}
  function pause(){hold++;stop();}
  function resume(){hold=Math.max(0,hold-1);plan();}
  tr.addEventListener('scroll',function(){clearTimeout(st);st=setTimeout(function(){mark();plan();},120);},{passive:true});
  for(var k=0;k<dots.length;k++){(function(k){dots[k].addEventListener('click',function(){go(k);});})(k);}
  var p=sl.querySelector('.ls-prev'),nx=sl.querySelector('.ls-next');
  if(p)p.addEventListener('click',function(){go(idx()-1);});
  if(nx)nx.addEventListener('click',function(){go(idx()+1);});
  var touching=false;
  tr.addEventListener('touchstart',function(){if(!touching){touching=true;pause();}},{passive:true});
  function tend(){if(touching){touching=false;resume();}}
  tr.addEventListener('touchend',tend,{passive:true});tr.addEventListener('touchcancel',tend,{passive:true});
  var hov=false,foc=false;
  sl.addEventListener('pointerenter',function(e){if(e.pointerType==='mouse'&&!hov){hov=true;pause();}});
  sl.addEventListener('pointerleave',function(e){if(hov){hov=false;resume();}});
  sl.addEventListener('focusin',function(e){if(!foc&&e.target.matches&&e.target.matches(':focus-visible')){foc=true;pause();}});
  sl.addEventListener('focusout',function(e){if(foc&&!sl.contains(e.relatedTarget)){foc=false;resume();}});
  document.addEventListener('visibilitychange',plan);
  window.addEventListener('resize',function(){tr.style.scrollBehavior='auto';tr.scrollLeft=cur*tr.clientWidth;tr.style.scrollBehavior='';});
  mark();plan();
})();

/* ===== v2: Northeast dropdown ===== */
(function(){
  var subs=document.querySelectorAll('.has-sub');
  for(var i=0;i<subs.length;i++){(function(li){
    var btn=li.querySelector('.sub-btn');if(!btn)return;
    btn.addEventListener('click',function(e){e.stopPropagation();var o=li.classList.toggle('open');btn.setAttribute('aria-expanded',o?'true':'false');});
    document.addEventListener('click',function(e){if(!li.contains(e.target)&&li.classList.contains('open')){li.classList.remove('open');btn.setAttribute('aria-expanded','false');}});
    li.addEventListener('keydown',function(e){if(e.key==='Escape'){li.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.focus();}});
  })(subs[i]);}
})();

/* ===== v2: search (header live results + /search page) ===== */
(function(){
  var IDX=null,loading=null;
  function load(){
    if(IDX)return Promise.resolve(IDX);
    if(loading)return loading;
    loading=fetch('/search.json',{cache:'no-cache'}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(d){
      IDX=d.map(function(s){s._h=norm([s.t,s.s,s.c,s.a,(s.st||[]).join(' ')].join(' '));s._t=norm(s.t);return s;});return IDX;
    }).catch(function(){loading=null;return [];});
    return loading;
  }
  function norm(x){x=String(x||'');try{x=x.normalize('NFKD').replace(/[\u0300-\u036f]/g,'');}catch(e){}return x.toLowerCase().replace(/[\u2018\u2019']/g,'').replace(/\s+/g,' ').trim();}
  function find(q){
    var toks=norm(q).split(' ').filter(Boolean);if(!toks.length||!IDX)return [];
    var out=[];
    for(var i=0;i<IDX.length;i++){var s=IDX[i],ok=true,sc=0;
      for(var k=0;k<toks.length;k++){var t=toks[k];if(s._h.indexOf(t)<0){ok=false;break;}if(s._t.indexOf(t)>=0)sc+=2;else sc+=1;}
      if(ok)out.push({s:s,sc:sc,i:i});}
    out.sort(function(a,b){return b.sc-a.sc||a.i-b.i;});
    return out.map(function(o){return o.s;});
  }
  function e(x){return String(x||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  window.MLsearch={load:load,find:find,esc:e};

  var box=document.getElementById('hSearch');if(!box)return;
  var btn=document.getElementById('hsBtn'),form=document.getElementById('hsForm'),inp=form.querySelector('.hs-input'),res=document.getElementById('hsRes'),sel=-1,t=null;
  function setOpen(o){box.classList.toggle('open',o);btn.setAttribute('aria-expanded',o?'true':'false');btn.setAttribute('aria-label',o?'Close search':'Search news');
    if(o){load();setTimeout(function(){inp.focus();},30);}else{res.hidden=true;}}
  btn.addEventListener('click',function(){setOpen(!box.classList.contains('open'));});
  function render(){
    var q=inp.value.trim();sel=-1;
    if(!q){res.hidden=true;res.innerHTML='';return;}
    load().then(function(){
      if(inp.value.trim()!==q)return;
      var r=find(q),h='';
      if(!r.length)h='<div class="hs-empty">No stories found for &ldquo;'+e(q)+'&rdquo;</div>';
      else{r.slice(0,6).forEach(function(s){h+='<a class="hs-item" href="'+e(s.u)+'"><img src="'+e(s.i)+'" alt="" loading="lazy"><span><span class="kicker">'+e(s.c)+' &middot; '+e(s.df)+'</span><b>'+e(s.t)+'</b></span></a>';});}
      h+='<a class="hs-all" href="/search?q='+encodeURIComponent(q)+'">'+(r.length?'See all '+r.length+' result'+(r.length===1?'':'s'):'Search all stories')+' &rsaquo;</a>';
      res.innerHTML=h;res.hidden=false;
    });
  }
  inp.addEventListener('focus',load);
  inp.addEventListener('input',function(){clearTimeout(t);t=setTimeout(render,90);});
  inp.addEventListener('keydown',function(ev){
    var items=res.querySelectorAll('.hs-item');
    if(ev.key==='ArrowDown'||ev.key==='ArrowUp'){if(!items.length)return;ev.preventDefault();sel=(sel+(ev.key==='ArrowDown'?1:-1)+items.length)%items.length;
      for(var i=0;i<items.length;i++)items[i].classList.toggle('sel',i===sel);}
    else if(ev.key==='Enter'&&sel>=0&&items[sel]){ev.preventDefault();location.href=items[sel].getAttribute('href');}
    else if(ev.key==='Escape'){if(box.classList.contains('open'))setOpen(false);else{res.hidden=true;inp.blur();}}
  });
  form.addEventListener('submit',function(ev){if(!inp.value.trim()){ev.preventDefault();inp.focus();}});
  document.addEventListener('click',function(ev){if(!box.contains(ev.target)){res.hidden=true;if(box.classList.contains('open')&&window.innerWidth<980)setOpen(false);}});

  // results page
  var out=document.getElementById('srResults');if(!out)return;
  var si=document.getElementById('srInput'),cnt=document.getElementById('srCount');
  var q0='';try{q0=new URLSearchParams(location.search).get('q')||'';}catch(er){}
  si.value=q0;
  function page(){
    var q=si.value.trim();
    if(!q){out.innerHTML='<p class="note">Type a word above, like a place, name or topic.</p>';cnt.textContent='';return;}
    load().then(function(){
      var r=find(q);
      cnt.textContent=r.length+' result'+(r.length===1?'':'s')+' for \u201c'+q+'\u201d';
      if(!r.length){out.innerHTML='<div class="empty-state"><p class="es-big">No stories found</p><p>Try a different word or check the spelling.</p></div>';return;}
      out.innerHTML='<div class="grid g3">'+r.map(function(s){return '<article class="card card-m"><a href="'+e(s.u)+'" class="card-link"><div class="thumb"><img src="'+e(s.i)+'" alt="" loading="lazy" width="1200" height="675"></div><div class="card-body"><div class="meta-top"><span class="kicker">'+e(s.c)+'</span></div><h3>'+e(s.t)+'</h3>'+(s.s?'<p class="dek">'+e(s.s)+'</p>':'')+'<time datetime="'+e(s.d)+'">'+e(s.df)+'</time></div></a></article>';}).join('')+'</div>';
    });
  }
  var pt=null;
  si.addEventListener('input',function(){clearTimeout(pt);pt=setTimeout(function(){page();try{history.replaceState(null,'',si.value.trim()?'?q='+encodeURIComponent(si.value.trim()):location.pathname);}catch(er){}},120);});
  si.form.addEventListener('submit',function(ev){ev.preventDefault();page();});
  page();
})();

/* ===== v2: share buttons ===== */
(function(){
  var bars=document.querySelectorAll('[data-share]');if(!bars.length)return;
  var toast=null,tt=null;
  function say(m){if(!toast){toast=document.createElement('div');toast.className='toast';toast.setAttribute('role','status');document.body.appendChild(toast);}
    toast.textContent=m;toast.classList.add('show');clearTimeout(tt);tt=setTimeout(function(){toast.classList.remove('show');},1800);}
  function copy(txt){
    if(navigator.clipboard&&window.isSecureContext)return navigator.clipboard.writeText(txt);
    return new Promise(function(ok,no){var a=document.createElement('textarea');a.value=txt;a.setAttribute('readonly','');a.style.position='fixed';a.style.top='-1000px';document.body.appendChild(a);a.select();
      try{document.execCommand('copy')?ok():no();}catch(er){no();}document.body.removeChild(a);});
  }
  for(var i=0;i<bars.length;i++){(function(b){
    var u=b.getAttribute('data-url'),ti=b.getAttribute('data-title');
    var st=b.querySelector('[data-native]');
    if(st)st.addEventListener('click',function(ev){
      if(navigator.share){ev.preventDefault();navigator.share({title:ti,text:ti,url:u}).catch(function(){});}
    });
    var cp=b.querySelector('[data-copy]');
    if(cp)cp.addEventListener('click',function(){
      var lab=cp.querySelector('span');
      copy(u).then(function(){say('Copied!');cp.classList.add('done');lab.textContent='Copied!';setTimeout(function(){cp.classList.remove('done');lab.textContent='Copy link';},1800);},
        function(){window.prompt('Copy this link:',u);});
    });
  })(bars[i]);}
})();

/* ===== v2: Northeast weather (Open-Meteo, cached 30 min) ===== */
(function(){
  var boxes=document.querySelectorAll('[data-wx]');if(!boxes.length)return;
  var coords;try{coords=JSON.parse(boxes[0].getAttribute('data-wx'));}catch(e){return;}
  var KEY='ml-wx-v1',TTL=30*60*1000;
  function icon(c,day){
    if(c===0)return day?'\u2600\ufe0f':'\ud83c\udf19';
    if(c===1||c===2)return day?'\ud83c\udf24\ufe0f':'\ud83c\udf19';
    if(c===3)return '\u2601\ufe0f';
    if(c===45||c===48)return '\ud83c\udf2b\ufe0f';
    if(c>=51&&c<=57)return '\ud83c\udf26\ufe0f';
    if((c>=61&&c<=67)||(c>=80&&c<=82))return '\ud83c\udf27\ufe0f';
    if((c>=71&&c<=77)||c===85||c===86)return '\u2744\ufe0f';
    if(c>=95)return '\u26c8\ufe0f';
    return '\ud83c\udf21\ufe0f';
  }
  function label(c){
    if(c===0)return 'Clear';if(c<=2)return 'Partly cloudy';if(c===3)return 'Cloudy';if(c===45||c===48)return 'Fog';
    if(c>=51&&c<=57)return 'Drizzle';if((c>=61&&c<=67)||(c>=80&&c<=82))return 'Rain';if((c>=71&&c<=77)||c===85||c===86)return 'Snow';if(c>=95)return 'Thunderstorm';return '';
  }
  function paint(data,ts,stale){
    for(var b=0;b<boxes.length;b++){
      var lis=boxes[b].querySelectorAll('li[data-i]');
      for(var k=0;k<lis.length;k++){var d=data[+lis[k].getAttribute('data-i')];if(!d)continue;
        lis[k].querySelector('.wx-ic').textContent=icon(d.c,d.day);
        lis[k].querySelector('.wx-t').textContent=Math.round(d.t)+'\u00b0';
        lis[k].querySelector('.wx-hl').innerHTML='<b>'+Math.round(d.hi)+'\u00b0</b> / '+Math.round(d.lo)+'\u00b0';
        lis[k].title=label(d.c)+', high '+Math.round(d.hi)+'\u00b0C, low '+Math.round(d.lo)+'\u00b0C';
      }
      var n=boxes[b].querySelector('.wx-note');
      if(n){var tm='';try{tm=new Date(ts).toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit',timeZone:'Asia/Kolkata'});}catch(e){}
        n.textContent=(stale?'Offline \u00b7 last updated ':'Updated ')+tm+' IST \u00b7 \u00b0C, today\u2019s high / low';}
    }
  }
  function fail(){for(var b=0;b<boxes.length;b++){var n=boxes[b].querySelector('.wx-note');if(n)n.textContent='Weather is unavailable right now.';}
    var s=document.querySelector('.wx-strip');if(s&&!cached)s.style.display='none';}
  var cached=null;try{cached=JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){}
  if(cached&&cached.d&&Date.now()-cached.ts<TTL){paint(cached.d,cached.ts);return;}
  if(cached&&cached.d)paint(cached.d,cached.ts,true);
  var u='https://api.open-meteo.com/v1/forecast?latitude='+coords.map(function(c){return c[0];}).join(',')+'&longitude='+coords.map(function(c){return c[1];}).join(',')+
    '&current=temperature_2m,weather_code,is_day&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FKolkata&forecast_days=1';
  fetch(u).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(j){
    if(!Array.isArray(j))j=[j];
    var d=j.map(function(x){return {t:x.current.temperature_2m,c:x.current.weather_code,day:x.current.is_day,hi:x.daily.temperature_2m_max[0],lo:x.daily.temperature_2m_min[0]};});
    var ts=Date.now();try{localStorage.setItem(KEY,JSON.stringify({ts:ts,d:d}));}catch(e){}
    paint(d,ts);
  }).catch(function(){if(cached&&cached.d)paint(cached.d,cached.ts,true);else fail();});
})();
