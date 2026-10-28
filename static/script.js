(function(){
  var d=document.getElementById('today');
  if(d){try{d.textContent=new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Kolkata'});}catch(e){}}
  var b=document.getElementById('menuBtn'),n=document.getElementById('mainNav');
  if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');b.setAttribute('aria-label',o?'Close sections menu':'Open sections menu');});}
})();
