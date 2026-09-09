const source = document.querySelector('#source'), compile = document.querySelector('#compile');
const status = document.querySelector('#status'), output = document.querySelector('#output');
const telemetry = document.querySelector('#telemetry'), canvas = document.querySelector('#map'), ctx = canvas.getContext('2d');
const play = document.querySelector('#play'), pause = document.querySelector('#pause'), reset = document.querySelector('#reset'), speed = document.querySelector('#speed');
let result = null, frame = 0, running = false, timer = null;

fetch('/api/sample').then(r => r.json()).then(data => source.value = data.source);
compile.onclick = async () => {
  running = false; clearInterval(timer); setStatus('COMPILING', 'idle'); output.textContent = 'Running AeroSafeX compiler pipeline…';
  const response = await fetch('/api/compile', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({source: source.value})});
  result = await response.json(); frame = 0; draw(); renderResult();
  const safe = result.status === 'COMPLETED'; [play, pause, reset].forEach(button => button.disabled = !safe); if (safe) { setStatus('SAFE', 'safe'); start(); } else setStatus('REJECTED', 'rejected');
};
play.onclick = () => start(); pause.onclick = () => { running = false; clearInterval(timer); }; reset.onclick = () => { running = false; clearInterval(timer); frame = 0; draw(); updateTelemetry(); };
function start() { if (!result?.drone) return; running = true; clearInterval(timer); timer = setInterval(() => { if (frame >= result.drone.trace.length - 1) { running = false; clearInterval(timer); return; } frame++; draw(); updateTelemetry(); }, 170 / Number(speed.value)); }
function setStatus(text, kind) { status.textContent = text; status.className = `status ${kind}`; }
function renderResult() {
  if (result.status !== 'COMPLETED') { output.textContent = `${result.stage} error\n${result.error}\n\n${(result.issues || []).map(i => `• ${i.message}`).join('\n')}`; telemetry.innerHTML = `<dt>Mission status</dt><dd>BLOCKED</dd><dt>Safety status</dt><dd>UNSAFE</dd>`; return; }
  output.textContent = `Safety status: SAFE\n\nOptimized IR\n${result.ir}\n\nGenerated simulator code\n${result.generated_code}`; updateTelemetry();
}
function updateTelemetry() { if (!result?.drone) return; const trace = result.drone.trace[Math.min(frame, result.drone.trace.length - 1)], final = frame >= result.drone.trace.length - 1; telemetry.innerHTML = `<dt>Mission status</dt><dd>${final ? result.drone.mission_status : 'RUNNING'}</dd><dt>Flight state</dt><dd>${final ? result.drone.flight_state : 'AIRBORNE'}</dd><dt>Position</dt><dd>${trace[0].toFixed(1)}, ${trace[1].toFixed(1)}</dd><dt>Altitude</dt><dd>${trace[2].toFixed(1)} m</dd><dt>Battery</dt><dd>${trace[3].toFixed(1)}%</dd><dt>Route distance</dt><dd>${result.distance.toFixed(1)} m</dd><dt>Safety</dt><dd>PASS</dd>`; }
function bounds() { const points = [...result.route]; Object.values(result.zones).forEach(z => points.push([z[0],z[1]],[z[2],z[3]])); const xs=points.map(p=>p[0]), ys=points.map(p=>p[1]), pad=30; return [Math.min(...xs)-pad, Math.max(...xs)+pad, Math.min(...ys)-pad, Math.max(...ys)+pad]; }
function transform(p) { const [minX,maxX,minY,maxY]=bounds(), margin=44; return [margin+(p[0]-minX)/(maxX-minX)*(canvas.width-margin*2), canvas.height-margin-(p[1]-minY)/(maxY-minY)*(canvas.height-margin*2)]; }
function draw() { ctx.clearRect(0,0,canvas.width,canvas.height); ctx.fillStyle='#a7c1d4'; ctx.font='12px system-ui'; if (!result) { ctx.fillText('Compile a mission to display its actual route.', 44, 54); return; } if (!result.route) { ctx.fillStyle='#ff9a9a'; ctx.fillText(`Mission rejected during ${result.stage} analysis.`, 44, 54); return; } const [minX,maxX,minY,maxY]=bounds();
  ctx.strokeStyle='#24445d'; ctx.strokeRect(44,24,canvas.width-88,canvas.height-68); Object.entries(result.zones).forEach(([name,z])=>{const a=transform([z[0],z[1]]),b=transform([z[2],z[3]]); ctx.fillStyle='rgba(226,78,82,.35)';ctx.fillRect(a[0],b[1],b[0]-a[0],a[1]-b[1]);ctx.fillStyle='#ff9a9a';ctx.fillText(name,a[0]+5,b[1]+16);});
  ctx.beginPath(); result.route.forEach((p,i)=>{const q=transform(p); i?ctx.lineTo(...q):ctx.moveTo(...q);});ctx.strokeStyle=result.status==='COMPLETED'?'#24c99a':'#e85d66';ctx.lineWidth=3;ctx.stroke();
  Object.entries(result.waypoints).forEach(([name,p])=>marker(p,'#7bd8ff',name)); marker(result.home,'#f6d56d','HOME'); if(result.drone){const p=result.drone.trace[Math.min(frame,result.drone.trace.length-1)]; marker(p,'#ffffff','DRONE');}
  function marker(p,color,label){const q=transform(p);ctx.beginPath();ctx.arc(q[0],q[1],7,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.fillStyle='#eaf2fb';ctx.fillText(label,q[0]+10,q[1]-10);}
}
