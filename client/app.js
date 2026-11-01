const $=id=>document.getElementById(id);
const canvas=$('game'), ctx=canvas.getContext('2d');
let state=null, frozen=null, bullet=false, audio=null, enabled=false, beat=0;
let viewer=sessionStorage.getItem('odyssey-viewer');
if(!viewer){viewer='viewer-'+crypto.randomUUID().slice(0,8);sessionStorage.setItem('odyssey-viewer',viewer);}
const names=['Neon Foxes','Bay Phantoms','Golden Glitches','Pixel Pirates'];
const colors=['#b59aff','#7bd8db','#edb76a','#f293ae'];
const route=[[950,104],[714,180],[480,210],[350,330],[555,452],[730,487]];
function atProgress(p){const n=Math.min(4.9999,p/20),i=Math.floor(n),f=n-i;return [route[i][0]+(route[i+1][0]-route[i][0])*f,route[i][1]+(route[i+1][1]-route[i][1])*f];}
function text(t,x,y,size=12,color='#b9cbd2'){ctx.fillStyle=color;ctx.font=`${size}px monospace`;ctx.fillText(t,x,y);}
function building(x,y,w,h,roof){ctx.fillStyle='#0c1c29';ctx.fillRect(x+7,y+10,w,h);ctx.fillStyle=roof;ctx.fillRect(x,y,w,h);ctx.fillStyle='#253d49';ctx.fillRect(x,y+h-7,w,7);ctx.fillStyle='#436272';for(let i=7;i<w-6;i+=13)for(let j=9;j<h-12;j+=16)ctx.fillRect(x+i,y+j,4,5);}
function draw(now){
 const s=bullet?frozen:state;ctx.clearRect(0,0,1100,620);
 ctx.fillStyle='#183b48';ctx.fillRect(0,0,1100,620);
 for(let i=0;i<14;i++){ctx.strokeStyle='#28505b';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(780+i*34,0);ctx.lineTo(970+i*34,620);ctx.stroke();}
 ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(920,0);ctx.lineTo(1000,140);ctx.lineTo(881,288);ctx.lineTo(1035,620);ctx.lineTo(0,620);ctx.closePath();ctx.fillStyle='#1c2b36';ctx.fill();
 ctx.save();ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(920,0);ctx.lineTo(1000,140);ctx.lineTo(881,288);ctx.lineTo(1035,620);ctx.lineTo(0,620);ctx.closePath();ctx.clip();
 for(let y=-90;y<740;y+=108){ctx.strokeStyle='#34444d';ctx.lineWidth=21;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1100,y+140);ctx.stroke();ctx.strokeStyle='#697067';ctx.lineWidth=1;ctx.setLineDash([5,10]);ctx.stroke();ctx.setLineDash([]);}
 for(let x=-100;x<1200;x+=150){ctx.strokeStyle='#34444d';ctx.lineWidth=18;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x-170,620);ctx.stroke();}
 for(let row=0;row<5;row++)for(let col=0;col<7;col++){let x=col*148+24-row*29,y=row*108+22+col*18;if(x>820)continue;building(x,y,45+(col%3)*12,48+(row%2)*13,['#2b3b48','#30414d','#374651'][(row+col)%3]);building(x+66,y+8,36,45,'#293b48');}
 // Waterfront greenery and warm Gaslamp street lights.
 ctx.fillStyle='#294b3d';ctx.fillRect(450,365,145,72);for(let i=0;i<8;i++){ctx.fillStyle='#477354';ctx.beginPath();ctx.arc(463+i*17,385+i%2*22,9,0,7);ctx.fill();}
 for(let i=0;i<8;i++){ctx.fillStyle='#d38962';ctx.fillRect(345+i*16,195,6,9);}
 // Stylized waterfront skyline; this is not a surveyed city model.
 ctx.fillStyle='#607b86';ctx.fillRect(610,116,24,104);ctx.fillRect(640,82,26,138);ctx.fillRect(672,140,22,80);ctx.fillStyle='#87a2a9';ctx.fillRect(646,95,8,125);
 ctx.restore();
 text('S A N  D I E G O  B A Y',920,366,10,'#6596a3');
 ctx.save();ctx.beginPath();route.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.strokeStyle='#a8f27625';ctx.lineWidth=18;ctx.stroke();ctx.setLineDash([5,8]);ctx.strokeStyle='#a8f2a0';ctx.lineWidth=3;ctx.stroke();ctx.restore();
 const labels=[['LITTLE ITALY / NORTH EMBARCADERO',760,61],['EMBARCADERO / MARINA',337,167],['GASLAMP QUARTER',600,259],['SAN DIEGO CONVENTION CENTER',423,480]];
 for(const [label,x,y] of labels){ctx.fillStyle='#101c26e8';ctx.fillRect(x-9,y-17,label.length*8+18,28);text(label,x,y,11,'#c5d6db');}
 const booths=[['TWITCH',770,139,'#b59aff'],['CODEX',292,295,'#a8f276'],['AWS / IVS',535,387,'#edb76a']];
 for(const [name,x,y,color] of booths){ctx.fillStyle='#101c26';ctx.fillRect(x-5,y-5,83,43);ctx.strokeStyle=color;ctx.strokeRect(x-5,y-5,83,43);text('◇ '+name,x+3,y+12,10,color);text('SPONSOR',x+3,y+27,8,'#8cabb7');}
 ctx.fillStyle='#6a5298';ctx.fillRect(674,510,188,56);ctx.fillStyle='#aa8bdf';ctx.fillRect(667,499,202,13);text('TWITCHCON',691,535,14,'#fff');text('SAN DIEGO CONVENTION CENTER',650,574,10,'#c7b4e9');text('FICTIONAL MAIN STAGE',680,592,10,'#c7b4e9');
 if(s){const [x,y]=atProgress(s.progress);let bob=bullet?0:Math.sin(now/150)*2;ctx.shadowColor='#a8f276';ctx.shadowBlur=20;ctx.fillStyle='#a8f276';ctx.fillRect(x-10,y-15+bob,20,23);ctx.shadowBlur=0;ctx.fillStyle='#182b32';ctx.fillRect(x-6,y-11+bob,12,7);ctx.fillStyle='#fff';ctx.fillRect(x+11,y-7+bob,10,12);text('YOU + BUILD',x-34,y-26,9,'#d4ffc0');if(s.phase==='action'&&!bullet){ctx.strokeStyle='#a8f276';ctx.beginPath();ctx.arc(x,y,24+Math.sin(now/160)*5,0,7);ctx.stroke();}if(s.status!=='racing'){ctx.fillStyle='#0b1018e8';ctx.fillRect(200,240,700,110);text(s.status==='delivered'?'BUILD DELIVERED. SEE YOU ON STAGE.':'BUILD LOST. REPLAY AND RALLY.',245,285,23,'#a8f276');text(`BOUNTY ${s.pool} CREDITS / ${s.rewards.participants||0} PARTICIPANTS`,300,321,13);}}
 requestAnimationFrame(draw);
}
function render(s){
 $('district').textContent=s.district;$('tick').textContent=`TICK ${String(s.tick).padStart(5,'0')} / 20 HZ`;
 $('pool').textContent=s.pool.toLocaleString();$('integrity').textContent=s.integrity+'%';$('integrity-fill').style.width=s.integrity+'%';$('progress').textContent=Math.floor(s.progress)+'%';$('progress-fill').style.width=s.progress+'%';
 $('round').textContent=`ROUND ${String(s.round).padStart(2,'0')} / ${s.phase.toUpperCase()}`;
 $('phase-title').textContent=s.status==='delivered'?'Main stage unlocked.':s.status==='failed'?'The city won this time.':s.phase==='planning'?'Your move, chat.':'Watch your moves land.';
 $('crisis').textContent=s.status==='delivered'?`Demo rewards: ${s.rewards.broadcaster} broadcaster / ${s.rewards.viewer_pool} viewer pool`:'⚠ '+s.crisis;
 $('clock').textContent=s.remaining.toFixed(1);$('timer-fill').style.width=s.remaining/(s.phase==='planning'?20:5)*100+'%';
 $('viewers').textContent=s.viewers+' VIEWERS';
 $('squads').replaceChildren(...s.squads.map((q,i)=>{const row=document.createElement('div');row.className='squad';const left=document.createElement('div'),icon=document.createElement('i'),name=document.createElement('span'),right=document.createElement('small');icon.textContent=['◇','◈','ϟ','✦'][i];icon.style.color=colors[i];name.textContent=names[i];right.textContent=(q.bot?'BOT':q.members+' VOTERS')+' / '+q.winner.toUpperCase();left.append(icon,name);row.append(left,right);return row;}));
 document.querySelectorAll('[data-action]').forEach(b=>b.disabled=s.phase!=='planning'||s.status!=='racing');
 const latest=kind=>[...s.telemetry].reverse().find(e=>e.kind===kind);
 const chat=latest('chat'),tool=latest('tool_call'),exec=latest('execution'),validation=latest('validation');
 if(chat)$('chat-event').textContent=`${chat.viewer}: “${chat.text}”`;
 if(tool)$('tool-event').textContent=tool.name+'('+JSON.stringify(tool.arguments)+')';
 if(exec)$('exec-event').textContent=`tick ${exec.tick} · ${exec.effects.join(' + ')}\ndamage: ${exec.damage} · authority: server`;
 if(validation&&validation.viewer===viewer)$('feedback').textContent=validation.accepted?'Vote accepted. Your squad is ready.':'Rejected: '+validation.reason;
}
async function poll(){try{const r=await fetch('/api/state');if(!r.ok)throw Error('Server unavailable');state=await r.json();if(!bullet)render(state);$('connection').textContent=bullet?'BULLET TIME / inspector frozen; server keeps running':'CONNECTED / server authority · bounded chat queue · no API calls on simulation thread';}catch(e){$('connection').textContent='DISCONNECTED / '+e.message;}setTimeout(poll,200);}
async function send(text){if(!state)return;try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({viewer,text,round:state.round})});const body=await r.json();$('feedback').textContent=r.ok?'Queued for schema validation…':body.error;}catch(e){$('feedback').textContent='Connection unavailable. Try again.';}}
$('chat').addEventListener('submit',e=>{e.preventDefault();const t=$('message').value.trim();if(t)send(t);$('message').value='';});
for(const b of document.querySelectorAll('[data-action]'))b.addEventListener('click',()=>send('!'+b.dataset.action));
$('bullet').onclick=()=>{bullet=!bullet;frozen=structuredClone(state);document.body.classList.toggle('bullet',bullet);$('bullet').setAttribute('aria-pressed',bullet);$('bullet').textContent=bullet?'▶ Resume inspector':'◷ Bullet time';if(state)render(bullet?frozen:state);};
$('sound').onclick=()=>{enabled=!enabled;if(enabled){audio??=new AudioContext();audio.resume();}$('sound').textContent=enabled?'♫ Sound on':'♫ Sound off';$('sound').setAttribute('aria-pressed',enabled);};
setInterval(()=>{if(!enabled||!audio||!state)return;const mode=state.status==='delivered'?'festival':state.phase==='action'?'synthwave':'8-bit';const notes=mode==='festival'?[261.63,329.63,392,523.25]:mode==='synthwave'?[110,164.81,220,164.81]:[220,261.63,329.63,293.66];const osc=audio.createOscillator(),gain=audio.createGain();osc.type=mode==='8-bit'?'square':mode==='synthwave'?'sawtooth':'triangle';osc.frequency.value=notes[beat++%notes.length];gain.gain.setValueAtTime(.022,audio.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.18);osc.connect(gain).connect(audio.destination);osc.start();osc.stop(audio.currentTime+.2);},250);
fetch('/api/health').then(r=>r.json()).then(h=>$('provider').textContent=h.provider.toUpperCase()).catch(()=>{});
requestAnimationFrame(draw);poll();
