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
