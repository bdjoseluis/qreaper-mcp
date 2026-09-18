"""
Módulo — Web mínima de respaldo  ·  Responsable: Jose

Interfaz web autocontenida (una sola página, sin dependencias de front ni
CDN) que consume la API REST del mismo servicio. Sirve de red de seguridad
para el requisito 1 de la práctica ("aplicación web funcionando") por si la
web principal no llega a tiempo.

Se monta sobre la app de FastAPI en la ruta ``/app`` desde ``api.py``.
Todo el JS llama a los endpoints ya existentes (/analizar/url,
/analizar/archivo, /historial), así que no duplica lógica.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QReaper — analizador anti-quishing</title>
<style>
  :root {
    --bg:#0b0f14; --panel:#151b23; --line:#232c38; --txt:#e6edf3;
    --muted:#8b98a5; --accent:#4da3ff;
    --peligro:#ff5c5c; --sospechoso:#ffb020; --seguro:#3ecf8e; --desc:#8b98a5;
  }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--txt); }
  .wrap { max-width:920px; margin:0 auto; padding:32px 20px 64px; }
  h1 { font-size:26px; margin:0 0 4px; letter-spacing:-.02em; }
  h1 span { color:var(--accent); }
  .sub { color:var(--muted); margin:0 0 28px; }
  .card { background:var(--panel); border:1px solid var(--line);
          border-radius:12px; padding:20px; margin-bottom:20px; }
  .card h2 { font-size:15px; text-transform:uppercase; letter-spacing:.08em;
             color:var(--muted); margin:0 0 14px; }
  .row { display:flex; gap:10px; flex-wrap:wrap; }
  input[type=text], input[type=file] { flex:1; min-width:220px; padding:11px 13px;
     background:#0e141b; border:1px solid var(--line); border-radius:8px;
     color:var(--txt); font-size:14px; }
  button { padding:11px 20px; border:0; border-radius:8px; cursor:pointer;
     background:var(--accent); color:#04121f; font-weight:600; font-size:14px; }
  button:disabled { opacity:.5; cursor:progress; }
  .verd { display:inline-block; padding:3px 10px; border-radius:999px;
     font-weight:700; font-size:12px; letter-spacing:.05em; }
  .PELIGRO{background:rgba(255,92,92,.15);color:var(--peligro);}
  .SOSPECHOSO{background:rgba(255,176,32,.15);color:var(--sospechoso);}
  .SEGURO{background:rgba(62,207,142,.15);color:var(--seguro);}
  .DESCONOCIDO{background:rgba(139,152,165,.15);color:var(--desc);}
  .res { margin-top:16px; padding:16px; border:1px solid var(--line);
     border-radius:10px; background:#0e141b; }
  .res .url { word-break:break-all; color:var(--accent); margin:8px 0; }
  ul.motivos { margin:8px 0 0; padding-left:18px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th,td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; }
  td.url { word-break:break-all; max-width:360px; }
  .muted { color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Q<span>Reaper</span></h1>
  <p class="sub">Analizador anti-quishing — extrae la URL de un QR, la detona en un sandbox aislado y dictamina el riesgo.</p>

  <div class="card">
    <h2>Analizar una URL</h2>
    <div class="row">
      <input type="text" id="url" placeholder="https://correos-es.top/pago" autocomplete="off">
      <button id="btnUrl" onclick="analizarUrl()">Analizar</button>
    </div>
    <div id="resUrl"></div>
  </div>

  <div class="card">
    <h2>Analizar un archivo (imagen · PDF · .eml)</h2>
    <div class="row">
      <input type="file" id="file" accept="image/*,.pdf,.eml">
      <button id="btnFile" onclick="analizarArchivo()">Subir y analizar</button>
    </div>
    <div id="resFile"></div>
  </div>

  <div class="card">
    <h2>Generar QR malicioso (demo)</h2>
    <div class="row">
      <input type="text" id="urlQr" placeholder="https://correos-es.top/pago" autocomplete="off">
      <button onclick="generarQr()">Generar QR</button>
    </div>
    <div id="resQr"></div>
  </div>

  <div class="card">
    <h2>Historial de análisis</h2>
    <div id="hist"><p class="muted">Cargando…</p></div>
  </div>
</div>

<script>
function pinta(r) {
  const v = (r.scoring && r.scoring.veredicto) || r.veredicto || "DESCONOCIDO";
  const nota = (r.scoring ? r.scoring.nota : r.nota);
  const motivos = (r.scoring ? r.scoring.motivos : r.motivos) || [];
  const finalUrl = (r.sandbox && r.sandbox.url_final) || r.url_final;
  let h = '<div class="res"><span class="verd '+v+'">'+v+'</span>';
  if (nota !== null && nota !== undefined) h += ' <span class="muted">nota '+nota+'/100</span>';
  h += '<div class="url">'+ (r.url||'') +'</div>';
  if (finalUrl && finalUrl !== r.url) h += '<div class="muted">URL final: '+finalUrl+'</div>';
  if (motivos.length) h += '<ul class="motivos">'+ motivos.map(m=>'<li>'+m+'</li>').join('') +'</ul>';
  h += '</div>';
  return h;
}
async function analizarUrl() {
  const b=document.getElementById('btnUrl'), out=document.getElementById('resUrl');
  const url=document.getElementById('url').value.trim();
  if(!url){out.innerHTML='<p class="muted">Escribe una URL.</p>';return;}
  b.disabled=true; out.innerHTML='<p class="muted">Analizando… (el sandbox puede tardar unos segundos)</p>';
  try{
    const resp=await fetch('/analizar/url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const data=await resp.json();
    if(!resp.ok){out.innerHTML='<p class="muted">Error: '+(data.detail||resp.status)+'</p>';}
    else{out.innerHTML=pinta(data); cargarHist();}
  }catch(e){out.innerHTML='<p class="muted">Fallo de red: '+e+'</p>';}
  b.disabled=false;
}
async function analizarArchivo() {
  const b=document.getElementById('btnFile'), out=document.getElementById('resFile');
  const f=document.getElementById('file').files[0];
  if(!f){out.innerHTML='<p class="muted">Elige un archivo.</p>';return;}
  b.disabled=true; out.innerHTML='<p class="muted">Analizando…</p>';
  const fd=new FormData(); fd.append('archivo',f);
  try{
    const resp=await fetch('/analizar/archivo',{method:'POST',body:fd});
    const data=await resp.json();
    if(!resp.ok){out.innerHTML='<p class="muted">Error: '+(data.detail||resp.status)+'</p>';}
    else if(!data.resultados||!data.resultados.length){out.innerHTML='<p class="muted">No se han encontrado QR con URL.</p>';}
    else{out.innerHTML=data.resultados.map(pinta).join(''); cargarHist();}
  }catch(e){out.innerHTML='<p class="muted">Fallo de red: '+e+'</p>';}
  b.disabled=false;
}
async function cargarHist() {
  const out=document.getElementById('hist');
  try{
    const resp=await fetch('/historial?limite=20'); const data=await resp.json();
    if(!data.analisis||!data.analisis.length){out.innerHTML='<p class="muted">Sin análisis todavía.</p>';return;}
    let h='<table><thead><tr><th>Fecha</th><th>URL</th><th>Veredicto</th><th>Nota</th></tr></thead><tbody>';
    for(const r of data.analisis){
      h+='<tr><td class="muted">'+(r.fecha||'').replace('T',' ').replace('+00:00','')+'</td>'+
         '<td class="url">'+(r.url||'')+'</td>'+
         '<td><span class="verd '+(r.veredicto||'DESCONOCIDO')+'">'+(r.veredicto||'—')+'</span></td>'+
         '<td>'+(r.nota??'—')+'</td></tr>';
    }
    out.innerHTML=h+'</tbody></table>';
  }catch(e){out.innerHTML='<p class="muted">No se pudo cargar el historial.</p>';}
}
cargarHist();
let _qrUrl='';
async function generarQr(){
  const url=document.getElementById('urlQr').value.trim();
  const out=document.getElementById('resQr');
  if(!url){out.innerHTML='<p class="muted">Escribe una URL.</p>';return;}
  _qrUrl=url;
  const src='/generar/qr?url='+encodeURIComponent(url);
  out.innerHTML='<div style="margin-top:14px;display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap">'
    +'<img src="'+src+'" style="width:180px;height:180px;border-radius:8px;background:#fff;padding:6px" alt="QR">'
    +'<div style="display:flex;flex-direction:column;gap:8px">'
    +'<a href="'+src+'" download="qr_malicioso.png"><button type="button">Descargar PNG</button></a>'
    +'<button type="button" onclick="analizarQrGenerado()">Analizar esta URL</button>'
    +'</div></div>';
}
async function analizarQrGenerado(){
  const url=_qrUrl; if(!url) return;
  const out=document.getElementById('resQr');
  out.innerHTML+='<p class="muted" style="margin-top:12px">Analizando...</p>';
  try{
    const resp=await fetch('/analizar/url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const data=await resp.json();
    const prev=out.querySelector('div');
    out.innerHTML=''; if(prev) out.appendChild(prev);
    out.innerHTML+=pinta(data); cargarHist();
  }catch(e){out.innerHTML+='<p class="muted">Error: '+e+'</p>';}
}
</script>
</body>
</html>"""


def pagina_html() -> HTMLResponse:
    """Devuelve la página web de respaldo."""
    return HTMLResponse(PAGINA)
