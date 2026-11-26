"""首页进入动效：拆 → 聚 → 成。

一句名家原文（苏轼「一蓑烟雨任平生」，公版）以墨字出现；
随即碎成上千粒墨点（拆：文字被拆成原子）；
墨点按三个族群各自归队，沿三道风痕聚拢成采风的标志（聚：原子归族、装配成引擎），
最后一族是朱红；
风痕再次散开，重新组合成「自成一体」四个字（成：用同一批原子写出自己的字）；
纸幕上卷，首页口号接着墨显。

同一批粒子贯穿全程，不增不减：别人的字拆下来的原子，最后写成你自己的字。
每次会话只放一次；点击或按键跳过；减弱动效时不放。全程约 4.3 秒。
"""

INTRO_CSS = r"""
#intro{display:none}
html.intro #intro{display:block;position:fixed;inset:0;z-index:60;background:var(--paper);cursor:pointer;
  animation:in-lift 1s cubic-bezier(.76,0,.24,1) 3.75s forwards}
html.intro body{overflow:hidden}
#intro canvas{position:absolute;inset:0;display:block}
@keyframes in-lift{to{transform:translateY(-100%)}}
.in-stage{position:absolute;left:0;right:0;bottom:11vh;display:flex;justify-content:center;gap:clamp(28px,5vw,64px);
  font:400 11px var(--mono);letter-spacing:.42em;color:var(--ink2)}
.in-stage span{opacity:.22;transition:opacity .5s ease,color .5s ease}
.in-stage span.on{opacity:1;color:var(--ink)}
.in-stage span:last-child.on{color:var(--zhu)}
.in-stage b{font:600 13px var(--serif);letter-spacing:0;margin-right:.7em}
.in-src{position:absolute;left:0;right:0;top:12vh;text-align:center;font:400 12px var(--serif);letter-spacing:.3em;
  color:var(--ink2);opacity:0;transition:opacity .6s ease}
.in-src.on{opacity:1}
.in-skip{position:absolute;right:28px;top:22px;font:400 11px var(--mono);letter-spacing:.3em;color:var(--ink2);opacity:.6}
html.skip #intro{animation:in-lift .5s cubic-bezier(.76,0,.24,1) forwards!important}
html.intro .h-hero h1 span{opacity:0;animation:in-ink 1s cubic-bezier(.2,.7,.2,1) forwards}
html.intro .h-hero h1 span:nth-child(1){animation-delay:4.15s}
html.intro .h-hero h1 span:nth-child(2){animation-delay:4.33s}
html.intro .h-hero h1 span:nth-child(3){animation-delay:4.51s}
html.skip .h-hero h1 span{animation-delay:.35s!important}
@keyframes in-ink{from{opacity:0;filter:blur(10px);transform:translateY(.2em)}to{opacity:1;filter:none;transform:none}}
@media(prefers-reduced-motion:reduce){html.intro #intro{display:none}html.intro body{overflow:auto}
  html.intro .h-hero h1 span{animation:none;opacity:1}}
"""

INTRO_JS = r"""
(()=>{const h=document.documentElement;if(!h.classList.contains('intro'))return;
const box=document.getElementById('intro'),cv=box.querySelector('canvas'),ctx=cv.getContext('2d');
const stg=[...box.querySelectorAll('.in-stage span')],src=box.querySelector('.in-src');
const dpr=Math.min(2,devicePixelRatio||1);let W=innerWidth,H=innerHeight,alive=true;
cv.width=W*dpr;cv.height=H*dpr;cv.style.width=W+'px';cv.style.height=H+'px';ctx.setTransform(dpr,0,0,dpr,0,0);
const N=W<700?1100:2200,PAPER='#F5F1E8';
const FONT='"Noto Serif SC","Source Han Serif SC","Songti SC",serif';
function textPts(txt,fs){const o=document.createElement('canvas');o.width=W;o.height=H;const c=o.getContext('2d');
  c.font=`900 ${fs}px ${FONT}`;c.textAlign='center';c.textBaseline='middle';c.fillText(txt,W/2,H/2);
  const d=c.getImageData(0,0,W,H).data,p=[],st=Math.max(2,Math.round(fs/46));
  for(let y=0;y<H;y+=st)for(let x=0;x<W;x+=st)if(d[(y*W+x)*4+3]>140)p.push([x,y]);
  for(let i=p.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[p[i],p[j]]=[p[j],p[i]]}return p}
function strokePts(){const s=Math.min(W*.46,500)/88,ox=W/2-48*s,oy=H/2-30*s,ws=[2.6,2,2.6];
  const ps=[...box.querySelectorAll('svg.src path')],share=[.42,.33,.25],out=[];let k0=0;
  ps.forEach((p,g)=>{const L=p.getTotalLength(),n=g<2?Math.round(N*share[g]):N-k0;
    for(let i=0;i<n;i++){const q=p.getPointAtLength(Math.random()*L),off=(Math.random()-.5)*ws[g]*1.1;
      out.push({x:ox+q.x*s,y:oy+(q.y+off)*s,g})}k0+=n});return out}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{try{await Promise.race([document.fonts.load(`900 100px ${FONT}`,'一蓑烟雨任平生自成体'),sleep(700)])}catch(e){}
  if(!alive)return;
  const A=textPts('一蓑烟雨任平生',Math.min(W/8.2,112)),S=strokePts(),B=textPts('自成一体',Math.min(W/5.4,178));
  const C=[[26,26,26],[26,26,26],[178,58,43]],INK=[26,26,26];
  const P=[];for(let i=0;i<N;i++){const a=A[i%A.length],sp=S[i],b=B[i%B.length],ang=Math.random()*6.283;
    P.push({x:a[0],y:a[1],vx:0,vy:0,a,sp,b,g:sp.g,ex:a[0]+Math.cos(ang)*(90+Math.random()*260),
      ey:a[1]+Math.sin(ang)*(60+Math.random()*190),d:Math.random(),r:.9+Math.random()*1.1,col:INK.slice()})}
  const T=[0,650,1350,2350,3150,3750];let t0=performance.now(),lastStage=-1;
  function stage(i){if(i===lastStage)return;lastStage=i;stg.forEach((s,k)=>s.classList.toggle('on',k===i));
    src.classList.toggle('on',i===0||i===-2)}
  src.classList.add('on');
  function frame(now){if(!alive)return;const t=now-t0;ctx.fillStyle=PAPER;ctx.fillRect(0,0,W,H);
    const fade=Math.min(1,t/450);
    if(t>T[1])stage(t<T[2]?0:t<T[4]?1:2);
    if(t>T[1]+300)src.classList.remove('on');
    for(const p of P){let tx,ty,k=.09,cc=INK;
      if(t<T[1]){tx=p.a[0];ty=p.a[1];k=1}
      else if(t<T[2]){const sw=(t-T[1])/700;tx=p.ex+Math.sin(sw*3+p.d*6)*18;ty=p.ey+Math.cos(sw*2.6+p.d*6)*14;k=.035+p.d*.03}
      else if(t<T[3]+p.d*250&&t<T[4]){if(t<T[2]+p.g*170+p.d*260){tx=p.ex;ty=p.ey;k=.02}else{tx=p.sp.x;ty=p.sp.y;k=.085}cc=C[p.g]}
      else if(t<T[4]){tx=p.sp.x;ty=p.sp.y+Math.sin(now/520+p.d*9)*.6;k=.12;cc=C[p.g]}
      else{if(t<T[4]+p.d*380){tx=p.sp.x+(p.x-p.sp.x);ty=p.sp.y-6;k=.03;cc=C[p.g]}else{tx=p.b[0];ty=p.b[1];k=.1;cc=t<T[5]-150?C[p.g]:INK}}
      p.vx=(p.vx+(tx-p.x)*k)*.78;p.vy=(p.vy+(ty-p.y)*k)*.78;
      if(k===1){p.x=tx;p.y=ty;p.vx=p.vy=0}else{p.x+=p.vx;p.y+=p.vy}
      for(let j=0;j<3;j++)p.col[j]+=(cc[j]-p.col[j])*.08;
      ctx.globalAlpha=fade;ctx.fillStyle=`rgb(${p.col[0]|0},${p.col[1]|0},${p.col[2]|0})`;
      ctx.fillRect(p.x-p.r/2,p.y-p.r/2,p.r,p.r)}
    ctx.globalAlpha=1;requestAnimationFrame(frame)}
  requestAnimationFrame(frame)})();
const end=()=>{if(!alive)return;h.classList.add('skip');setTimeout(()=>{alive=false;h.classList.remove('intro','skip');box.remove()},520)};
box.addEventListener('click',end);addEventListener('keydown',end,{once:true});
box.addEventListener('animationend',e=>{if(e.animationName==='in-lift'){alive=false;h.classList.remove('intro');box.remove()}});
})();
"""

INTRO_HTML = (
    '<script>(function(h){try{if(!sessionStorage.cfIntro&&!matchMedia("(prefers-reduced-motion: reduce)").matches){'
    'h.classList.add("intro");sessionStorage.cfIntro=1}}catch(e){}})(document.documentElement)</script>'
    '<div id="intro" aria-hidden="true"><canvas></canvas>'
    '<svg class="src" width="0" height="0" style="position:absolute"><path d="M4 14 C30 6, 56 24, 92 12"/>'
    '<path d="M12 30 C36 22, 58 38, 82 28"/><path d="M20 46 C40 39, 58 53, 72 44"/></svg>'
    '<p class="in-src">苏轼 · 定风波</p>'
    '<span class="in-skip">点击跳过</span>'
    '<div class="in-stage"><span><b>拆</b>DECOMPOSE</span><span><b>聚</b>ATOMS</span><span><b>成</b>COMPOSE</span></div>'
    f'</div><script>{INTRO_JS}</script>'
)
