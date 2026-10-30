(function(){function init(){var R=document.querySelectorAll('.rb');if(!R.length||window.rbInit)return;window.rbInit=1;
var r=document,P=document.querySelector('.rb--page')||R[0];
function ready(){[].forEach.call(R,function(x){x.classList.add('rb-ready');});}if(document.readyState==='complete')ready();else addEventListener('load',ready);
var path=location.pathname;if(path.length>1&&path.slice(-1)==='/')path=path.slice(0,-1);
[].forEach.call(document.querySelectorAll('.rb-head a[href],.rb-foot a[href]'),function(a){var u=a.getAttribute('href');
 if(!u||u.charAt(0)!=='/'||/[?#]/.test(u)||(u.length>1&&u.slice(-1)==='/'?u.slice(0,-1):u)!==path)return;a.setAttribute('aria-current','page');
 var g=a.closest('.rb-dd,.rb-mgroup');if(g){if(g.tagName==='DETAILS')g.open=true;else g.classList.add('is-on');}});
var b=r.querySelector('.rb-burger'),m=r.querySelector('.rb-mnav');
if(b&&m)b.addEventListener('click',function(){var o=m.hasAttribute('data-open');if(o)m.removeAttribute('data-open');else m.setAttribute('data-open','');b.setAttribute('aria-expanded',String(!o));});
r.querySelectorAll('.rb-dd').forEach(function(d){var t=d.querySelector('.rb-nav__top');
 t.addEventListener('click',function(e){e.stopPropagation();var o=!d.classList.contains('is-open');r.querySelectorAll('.rb-dd.is-open').forEach(function(x){x.classList.remove('is-open');x.querySelector('.rb-nav__top').setAttribute('aria-expanded','false');});
  d.classList.toggle('is-open',o);t.setAttribute('aria-expanded',String(o));});});
document.addEventListener('click',function(){r.querySelectorAll('.rb-dd.is-open').forEach(function(x){x.classList.remove('is-open');x.querySelector('.rb-nav__top').setAttribute('aria-expanded','false');});});
document.addEventListener('keydown',function(e){if(e.key==='Escape')r.querySelectorAll('.rb-dd.is-open').forEach(function(x){x.classList.remove('is-open');x.querySelector('.rb-nav__top').setAttribute('aria-expanded','false');});});
r.querySelectorAll('.rb-feat').forEach(function(c){c.addEventListener('pointermove',function(e){var b=c.getBoundingClientRect();c.style.setProperty('--mx',(e.clientX-b.left)+'px');c.style.setProperty('--my',(e.clientY-b.top)+'px');});});
var fw=r.querySelector('.rb-flow');if(fw){var fs=fw.querySelector('svg'),fb=fw.querySelector('.rb-flow__base'),fl=fw.querySelector('.rb-flow__lit'),fdot=fw.querySelector('.rb-flow__dot'),FL=0,FH=1,ft=false;
 function fdraw(){var W=P.clientWidth,mn=P.querySelector('main'),H=mn?mn.offsetTop+mn.offsetHeight:P.scrollHeight,st=Math.max(760,innerHeight*.95),a=W*.06,b=W*.94,x=W*.72,y=0,k=0,d;
  if(W<700){a=W*.04;b=W*.96;}d='M'+x+' 0';while(y<H){var ny=Math.min(y+st,H+st),nx=k%2?b:a;d+=' C'+x+' '+(y+st*.55)+' '+nx+' '+(ny-st*.55)+' '+nx+' '+ny;x=nx;y=ny;k++;}
  fs.setAttribute('viewBox','0 0 '+W+' '+P.scrollHeight);fb.setAttribute('d',d);fl.setAttribute('d',d);FL=fl.getTotalLength();FH=H;fl.style.strokeDasharray=FL+' '+FL;fscroll();}
 function fscroll(){ft=false;var p=Math.min(1,Math.max(0,(scrollY+innerHeight*.7-P.getBoundingClientRect().top-scrollY)/FH)),L=FL*p;fl.style.strokeDashoffset=FL-L;var pt=fl.getPointAtLength(L);fdot.setAttribute('cx',pt.x);fdot.setAttribute('cy',pt.y);}
 fdraw();if(window.ResizeObserver)new ResizeObserver(function(){fdraw();}).observe(P);else addEventListener('resize',fdraw);
 addEventListener('scroll',function(){if(!ft){ft=true;requestAnimationFrame(fscroll);}},{passive:true});}
var y=r.querySelector('[data-rb-year]');if(y)y.textContent=new Date().getFullYear();
r.querySelectorAll('.rb-gal').forEach(function(g){var im=g.querySelector('.rb-gal__main img'),th=[].slice.call(g.querySelectorAll('.rb-gal__thumbs button')),i=0;
 function go(n){if(!th.length)return;i=(n+th.length)%th.length;im.src=th[i].getAttribute('data-src');th.forEach(function(t,k){if(k===i)t.setAttribute('aria-current','true');else t.removeAttribute('aria-current');});}
 th.forEach(function(t,k){t.addEventListener('click',function(){go(k);});});
 var p=g.querySelector('.rb-gal__nav--prev'),n=g.querySelector('.rb-gal__nav--next');
 if(p)p.addEventListener('click',function(){go(i-1);});if(n)n.addEventListener('click',function(){go(i+1);});});
var rm=matchMedia('(prefers-reduced-motion: reduce)').matches;
r.querySelectorAll('.rb-stage').forEach(function(st){
 var sec=st.closest('.rb-intro'),im=st.querySelectorAll('.rb-stage__img'),dt=st.querySelectorAll('.rb-stage__dots button'),cards=sec.querySelectorAll('.rb-brand'),
  svg=sec.querySelector('.rb-links'),links=svg?svg.querySelectorAll('.rb-link'):[],cap=st.querySelector('.rb-stage__cap'),pv=st.querySelectorAll('.rb-pt'),ho=st.querySelectorAll('.rb-holo'),hl=svg?svg.querySelector('.rb-link__holo'):null,n=im.length,i=0,t=null,ms=+st.getAttribute('data-interval')||6000;
 function ldr(){[].forEach.call(im,function(x){if(x.dataset.srcset){x.srcset=x.dataset.srcset;x.removeAttribute('data-srcset');}if(x.dataset.src){x.src=x.dataset.src;x.removeAttribute('data-src');}});}if(im[0].complete)setTimeout(ldr,200);else{im[0].addEventListener('load',ldr);im[0].addEventListener('error',ldr);}
 function pts(k){return (im[k].getAttribute('data-hs')||'').split(';').map(function(p){var c=p.split(',');return [+c[0],+c[1]];});}
 var cur=pts(0),from=cur,to=cur,t0=0,anim=0;
 function draw(){[].forEach.call(pv,function(b,k){if(cur[k]){b.style.left=cur[k][0]+'%';b.style.top=cur[k][1]+'%';}});
  if(!svg||!links.length||getComputedStyle(svg).display==='none')return;var sr=sec.getBoundingClientRect(),fr=st.getBoundingClientRect();
  svg.setAttribute('viewBox','0 0 '+sr.width+' '+sr.height);
  var bi=+im[i].getAttribute('data-brand'),ah=ho[bi];if(hl&&ah&&cur[bi]){var hr=ah.getBoundingClientRect(),px=fr.left-sr.left+cur[bi][0]/100*fr.width,py=fr.top-sr.top+cur[bi][1]/100*fr.height,hx=hr.left-sr.left,hy=hr.top-sr.top+22;hl.setAttribute('d','M'+px+' '+py+'L'+(px+(hx-px)*.55)+' '+hy+'H'+hx);}
  [].forEach.call(links,function(g,k){var c=cards[k]&&cards[k].querySelector('.rb-brand__head');if(!c||!cur[k])return;var cr=c.getBoundingClientRect(),sx=cr.right-sr.left,sy=cr.top+cr.height/2-sr.top,
   ex=fr.left-sr.left+cur[k][0]/100*fr.width,ey=fr.top-sr.top+cur[k][1]/100*fr.height,dx=(ex-sx)*.5,d='M'+sx+' '+sy+'C'+(sx+dx)+' '+sy+' '+(ex-dx)+' '+ey+' '+ex+' '+ey;
   g.querySelector('.rb-link__base').setAttribute('d',d);g.querySelector('.rb-link__pulse').setAttribute('d',d);g.querySelector('.rb-link__spark').setAttribute('d',d);});}
 function tween(ts){if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/1200),e=p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
  cur=to.map(function(q,k){var f=from[k]||q;return [f[0]+(q[0]-f[0])*e,f[1]+(q[1]-f[1])*e];});draw();if(p<1)anim=requestAnimationFrame(tween);}
 function show(k){i=(k+n)%n;
  [].forEach.call(im,function(e,j){e.classList.toggle('is-active',j===i);});
  var bi=im[i].getAttribute('data-brand');
  [].forEach.call(cards,function(e){var a=e.getAttribute('data-brand')===bi;e.classList.toggle('is-active',a);var h=e.querySelector('.rb-brand__head');if(h)h.setAttribute('aria-expanded',String(a));});
  [].forEach.call(pv,function(e){e.classList.toggle('is-active',e.getAttribute('data-brand')===bi);});
  [].forEach.call(ho,function(e){e.classList.toggle('is-active',e.getAttribute('data-brand')===bi);});
  [].forEach.call(links,function(e,j){e.classList.toggle('is-active',String(j)===bi);});
  if(cap){var nt=im[i].getAttribute('data-name'),pt=im[i].getAttribute('data-labels');cap.classList.add('is-swap');setTimeout(function(){cap.querySelector('.rb-stage__name').textContent=nt;cap.querySelector('.rb-stage__pts').textContent=pt;cap.classList.remove('is-swap');},rm?0:500);}
  [].forEach.call(dt,function(e,j){e.classList.toggle('is-active',j===i);e.classList.toggle('is-done',j<i);if(j===i)e.setAttribute('aria-current','true');else e.removeAttribute('aria-current');});
  from=cur;to=pts(i);cancelAnimationFrame(anim);t0=0;if(rm){cur=to;draw();setTimeout(draw,650);}else anim=requestAnimationFrame(tween);}
 function brand(b){for(var j=0;j<n;j++){if(im[j].getAttribute('data-brand')===b){if(j!==i)show(j);return;}}}
 function play(){stop();if(rm||n<2)return;st.setAttribute('data-playing','');st.style.setProperty('--rb-int',ms+'ms');t=setInterval(function(){show(i+1);},ms);}
 function stop(){if(t){clearInterval(t);t=null;}st.removeAttribute('data-playing');}
 [].forEach.call(dt,function(e,j){e.addEventListener('click',function(){show(j);play();});});
 [].forEach.call(cards,function(c){var b=c.getAttribute('data-brand'),h=c.querySelector('.rb-brand__head');
  c.addEventListener('mouseenter',function(){brand(b);stop();st.setAttribute('data-paused','');});
  c.addEventListener('mouseleave',function(){st.removeAttribute('data-paused');play();});
  if(h)h.addEventListener('click',function(){brand(b);play();});});
 [].forEach.call(pv,function(p){var b=p.getAttribute('data-brand');
  p.addEventListener('mouseenter',function(){brand(b);stop();st.setAttribute('data-paused','');});
  p.addEventListener('focus',function(){brand(b);stop();});p.addEventListener('click',function(){brand(b);play();});});
 st.addEventListener('mouseenter',function(){st.setAttribute('data-paused','');stop();});
 st.addEventListener('mouseleave',function(){st.removeAttribute('data-paused');play();});
 document.addEventListener('visibilitychange',function(){if(document.hidden)stop();else play();});
 draw();window.addEventListener('resize',draw);window.addEventListener('load',draw);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(draw);
 if('ResizeObserver' in window)new ResizeObserver(draw).observe(sec);
 play();
});
r.querySelectorAll('.rb-cat').forEach(function(cat){
 var cards=[].slice.call(cat.querySelectorAll('.rb-prod')),groups=[].slice.call(cat.querySelectorAll('.rb-filter')),dlg=cat.querySelector('.rb-dlg'),empty=cat.querySelector('.rb-cat__empty'),st={};
 var q=new URLSearchParams(location.search);
 function apply(){var n=0;cards.forEach(function(c){var ok=Object.keys(st).every(function(k){return st[k]==='all'||(c.getAttribute('data-'+k)||'').split(' ').indexOf(st[k])>-1;});c.hidden=!ok;if(ok)n++;});if(empty)empty.hidden=n>0;}
 function set(k,v,push){st[k]=v;groups.forEach(function(g){if(g.getAttribute('data-f')===k)[].forEach.call(g.querySelectorAll('button'),function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-v')===v));});});
  apply();if(push&&history.replaceState){var u=new URLSearchParams(location.search);if(v==='all')u.delete(k);else u.set(k,v);var qs=u.toString();history.replaceState(null,'',location.pathname+(qs?'?'+qs:'')+location.hash);}}
 groups.forEach(function(g){var k=g.getAttribute('data-f'),v=q.get(k);if(v&&!g.querySelector('[data-v="'+v+'"]'))v=null;set(k,v||'all',false);
  [].forEach.call(g.querySelectorAll('button'),function(b){b.addEventListener('click',function(){set(k,b.getAttribute('data-v'),true);});});});
 var DET={};
 function open(c){if(!dlg||!c)return;dlg.classList.toggle('rb-dlg--photo',c.classList.contains('rb-prod--photo'));var im=c.querySelector('.rb-prod__ph img'),di=dlg.querySelector('.rb-dlg__ph img');di.src=im.src;di.alt=im.alt;
  dlg.querySelector('.rb-prod__en').textContent=c.querySelector('.rb-prod__en').textContent;dlg.querySelector('h3').textContent=c.querySelector('.rb-prod__bd b').textContent;
  dlg.querySelector('.rb-dlg__desc').textContent=c.querySelector('.rb-prod__desc').textContent;var ks=c.querySelector('.rb-keys'),dk=dlg.querySelector('.rb-dlg__keys');if(dk)dk.innerHTML=ks?'<span class="rb-dlg__klabel">Ключевые компоненты</span>'+ks.outerHTML:'';var pd=c.querySelector('.rb-prod__pd');
  dlg.querySelector('.rb-dlg__meta').textContent=pd.querySelector('.rb-prod__meta').textContent;var u=pd.getAttribute('data-url'),more=u?'<div class="rb-dl"><dt>Подробнее</dt><dd><a href="'+u+'" target="_blank" rel="noopener">Описание, протоколы и результаты на сайте бренда →</a></dd></div>':'';
  var id=c.getAttribute('data-id'),dl=dlg.querySelector('.rb-dlg__dl'),cat=c.closest('.rb-cat'),src=cat&&cat.getAttribute('data-details');dlg.setAttribute('data-cur',id);
  if(src&&!pd.querySelector('.rb-dl')){dl.innerHTML='<div class="rb-dl"><dd class="rb-muted">Загружаем состав…</dd></div>';
   (DET[src]||(DET[src]=fetch(src).then(function(x){return x.json();}))).then(function(d){if(dlg.getAttribute('data-cur')===id)dl.innerHTML=(d[id]||'')+more;})['catch'](function(){delete DET[src];if(dlg.getAttribute('data-cur')===id)dl.innerHTML=more;});}
  else dl.innerHTML=[].map.call(pd.querySelectorAll('.rb-dl'),function(x){return x.outerHTML;}).join('')+more;
  if(!dlg.open){if(dlg.showModal)dlg.showModal();else dlg.setAttribute('open','');}dlg.querySelector('.rb-dlg__bd').scrollTop=0;
  if(history.replaceState)history.replaceState(null,'',location.pathname+location.search+'#p-'+c.getAttribute('data-id'));}
 function close(){if(dlg.open){if(dlg.close)dlg.close();else dlg.removeAttribute('open');}}
 if(dlg){dlg.addEventListener('close',function(){if(/^#p-/.test(location.hash)&&history.replaceState)history.replaceState(null,'',location.pathname+location.search);});
  dlg.querySelector('.rb-dlg__x').addEventListener('click',close);dlg.addEventListener('click',function(e){if(e.target===dlg)close();});
  [].forEach.call(dlg.querySelectorAll('[data-close]'),function(a){a.addEventListener('click',close);});}
 cards.forEach(function(c){if(c.classList.contains('rb-prod--link'))return;c.addEventListener('click',function(e){e.preventDefault();open(c);});});
 function fromHash(){var m=location.hash.match(/^#p-([\w-]+)/)||location.search.match(/[?&]p=([\w-]+)/);if(!m)return;var c=cat.querySelector('.rb-prod[data-id="'+m[1]+'"]');if(c){if(c.hidden)groups.forEach(function(g){set(g.getAttribute('data-f'),'all',false);});c.scrollIntoView({block:'center'});open(c);}}
 fromHash();window.addEventListener('hashchange',fromHash);
});
r.querySelectorAll('.rb-pans').forEach(function(w){var ps=[].slice.call(w.querySelectorAll('.rb-pan'));
 function act(p){ps.forEach(function(x){var a=x===p;x.classList.toggle('is-active',a);x.querySelector('.rb-pan__tab').setAttribute('aria-expanded',String(a));});}
 [].forEach.call(w.querySelectorAll('[data-filter]'),function(a){a.addEventListener('click',function(e){var f=(a.getAttribute('data-filter')||'').split('='),cat=r.querySelector('.rb-cat');
  if(!cat||f.length<2)return;var b=cat.querySelector('.rb-filter[data-f="'+f[0]+'"] button[data-v="'+f[1]+'"]');if(!b)return;e.preventDefault();
  var all=cat.querySelectorAll('.rb-filter button[data-v="all"]');[].forEach.call(all,function(x){if(x!==b)x.click();});b.click();
  var k=r.querySelector('#katalog');if(k)k.scrollIntoView({behavior:rm?'auto':'smooth'});});});
 ps.forEach(function(p){var t=p.querySelector('.rb-pan__tab');t.addEventListener('click',function(){act(p);});
  if(matchMedia('(hover:hover) and (min-width:901px)').matches)p.addEventListener('mouseenter',function(){act(p);});});});
r.querySelectorAll('.rb-railnav button').forEach(function(bt){bt.addEventListener('click',function(){var sec=bt.closest('.rb-wrap'),rl=sec&&sec.querySelector('.rb-rail');if(!rl)return;var c=rl.querySelector('.rb-pcard');var w=c?c.getBoundingClientRect().width+20:rl.clientWidth*0.8;rl.scrollBy({left:w*(+bt.getAttribute('data-dir')),behavior:rm?'auto':'smooth'});});});
var h=r.querySelector('.rb-head');function sc(){if(!h)return;if(window.scrollY>10)h.setAttribute('data-scrolled','');else h.removeAttribute('data-scrolled');}
sc();window.addEventListener('scroll',sc,{passive:true});
if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
 [].forEach.call(R,function(x){x.classList.add('rb-js');});
 var els=r.querySelectorAll('.rb-sec h2,.rb-sec .rb-kicker,.rb-card,.rb-review,.rb-row,.rb-stats>div,.rb-adv figure,.rb-panel,.rb-gal,.rb-fields');
 var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('is-in');io.unobserve(e.target);}});},{rootMargin:'0px 0px -8% 0px'});
 els.forEach(function(el,k){el.classList.add('rb-reveal');el.style.transitionDelay=(k%4)*70+'ms';io.observe(el);});
}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();