<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scanner</title>
<style>
  :root{
    --bg: #0a0d10;
    --panel: #10151a;
    --panel-2: #141a20;
    --line: #1f2830;
    --text: #d8e0e6;
    --text-dim: #6b7a85;
    --text-mid: #9aa8b2;
    --green: #3ddc84;
    --green-dim: #1d5a3a;
    --red: #ff5c5c;
    --red-dim: #5a2323;
    --amber: #e8b23d;
    --blue: #4d9de0;
    --mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
    --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{
    background:
      radial-gradient(circle at 15% 0%, rgba(61,220,132,0.05), transparent 40%),
      radial-gradient(circle at 85% 100%, rgba(77,157,224,0.04), transparent 40%),
      var(--bg);
    color:var(--text);
    font-family:var(--sans);
    min-height:100vh;
    padding:20px;
  }
  @font-face{font-family:'IBM Plex Mono';src:local('IBM Plex Mono');}

  .wrap{max-width:1400px;margin:0 auto;}

  /* header */
  header{
    display:flex;justify-content:space-between;align-items:flex-end;
    margin-bottom:18px;padding-bottom:16px;border-bottom:1px solid var(--line);
    flex-wrap:wrap;gap:12px;
  }
  .title-block h1{
    font-family:var(--mono);font-size:22px;font-weight:600;letter-spacing:-0.5px;
    margin:0;color:#fff;
  }
  .title-block .sub{font-size:12.5px;color:var(--text-dim);margin-top:4px;font-family:var(--mono);}
  .status-block{text-align:right;font-family:var(--mono);font-size:12px;color:var(--text-dim);}
  .status-row{display:flex;align-items:center;gap:8px;justify-content:flex-end;margin-bottom:4px;}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--text-dim);flex-shrink:0;}
  .dot.live{background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;}
  .dot.err{background:var(--red);box-shadow:0 0 8px var(--red);}
  @keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
  .src-link{color:var(--text-dim);font-size:10.5px;word-break:break-all;max-width:340px;display:inline-block;}
  .src-link a{color:var(--blue);text-decoration:none;}

  /* top picks */
  .picks{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:20px;}
  .pick-card{
    background:linear-gradient(180deg, var(--panel-2), var(--panel));
    border:1px solid var(--line);border-radius:10px;padding:14px 16px;
    position:relative;overflow:hidden;
  }
  .pick-card::before{
    content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg, var(--green), transparent);
  }
  .pick-rank{font-family:var(--mono);font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;}
  .pick-ticker{font-family:var(--mono);font-size:22px;font-weight:700;color:#fff;margin:4px 0 2px;}
  .pick-sector{font-size:11px;color:var(--text-mid);margin-bottom:10px;}
  .pick-price-row{display:flex;align-items:baseline;gap:8px;margin-bottom:8px;}
  .pick-price{font-family:var(--mono);font-size:16px;color:var(--text);}
  .pick-chg{font-family:var(--mono);font-size:13px;font-weight:600;}
  .pick-score-row{display:flex;justify-content:space-between;align-items:center;}
  .pick-score{font-family:var(--mono);font-size:12px;color:var(--text-mid);}
  .badge{
    font-family:var(--mono);font-size:10.5px;font-weight:700;letter-spacing:0.5px;
    padding:3px 8px;border-radius:20px;text-transform:uppercase;
  }
  .badge.strongbuy{background:rgba(61,220,132,0.15);color:var(--green);border:1px solid var(--green-dim);}
  .badge.buy{background:rgba(77,157,224,0.12);color:var(--blue);border:1px solid #234a63;}
  .badge.hold{background:rgba(232,178,61,0.1);color:var(--amber);border:1px solid #5c481d;}

  /* controls */
  .controls{
    display:flex;flex-wrap:wrap;gap:14px;align-items:center;
    background:var(--panel);border:1px solid var(--line);border-radius:10px;
    padding:12px 16px;margin-bottom:14px;font-size:12.5px;
  }
  .ctl-group{display:flex;flex-direction:column;gap:4px;}
  .ctl-group label{font-family:var(--mono);font-size:10.5px;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.5px;}
  select,input[type=text]{
    background:var(--bg);border:1px solid var(--line);color:var(--text);
    padding:6px 10px;border-radius:6px;font-family:var(--mono);font-size:12.5px;
  }
  input[type=range]{accent-color:var(--green);}
  .toggle{
    display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;
    font-family:var(--mono);font-size:12px;color:var(--text-mid);
  }
  .toggle input{accent-color:var(--green);}
  .spacer{flex:1;}
  .btn{
    background:var(--panel-2);border:1px solid var(--line);color:var(--text);
    padding:7px 14px;border-radius:6px;font-family:var(--mono);font-size:12px;
    cursor:pointer;transition:border-color .15s;
  }
  .btn:hover{border-color:var(--green-dim);color:var(--green);}
  .match-count{font-family:var(--mono);font-size:12px;color:var(--text-dim);}

  /* table */
  .table-wrap{
    background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;
  }
  table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px;}
  thead th{
    text-align:right;padding:10px 12px;font-size:10.5px;color:var(--text-dim);
    text-transform:uppercase;letter-spacing:0.5px;font-weight:600;
    border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;
    position:sticky;top:0;background:var(--panel-2);
  }
  thead th:hover{color:var(--text);}
  thead th.left,td.left{text-align:left;}
  thead th.active{color:var(--green);}
  tbody tr{border-bottom:1px solid var(--line);transition:background .1s;}
  tbody tr:hover{background:var(--panel-2);}
  tbody tr:last-child{border-bottom:none;}
  td{padding:9px 12px;text-align:right;white-space:nowrap;}
  td.ticker{font-weight:700;color:#fff;}
  td.sector{color:var(--text-dim);font-size:11px;text-align:left;}
  .star{cursor:pointer;color:var(--text-dim);font-size:14px;text-align:center;padding:9px 6px;}
  .star.on{color:var(--amber);}
  .up{color:var(--green);}
  .down{color:var(--red);}
  .flat{color:var(--text-mid);}
  .trend-up::before{content:'▲ ';font-size:9px;}
  .trend-down::before{content:'▼ ';font-size:9px;}
  .trend-flat::before{content:'– ';font-size:9px;color:var(--text-dim);}
  .score-cell{font-weight:700;}
  .score-bar-wrap{display:flex;align-items:center;gap:8px;justify-content:flex-end;}
  .score-bar{width:40px;height:4px;background:var(--line);border-radius:2px;overflow:hidden;}
  .score-bar-fill{height:100%;border-radius:2px;}
  .rating{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:4px;letter-spacing:0.3px;}

  footer{
    margin-top:16px;font-size:11px;color:var(--text-dim);text-align:center;
    font-family:var(--mono);line-height:1.6;padding:10px 0;
  }

  @media (max-width:700px){
    .table-wrap{overflow-x:auto;}
    table{min-width:820px;}
  }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="title-block">
      <h1>◆ SCANNER</h1>
      <div class="sub">S&amp;P 100 · ranked by momentum, RSI, MACD, trend &amp; relative strength</div>
    </div>
    <div class="status-block">
      <div class="status-row">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">connecting…</span>
      </div>
      <div class="src-link">source: <a href="https://raw.githubusercontent.com/Romaita/stock-scanner/main/scanner_output.json" target="_blank">stock-scanner/scanner_output.json</a></div>
    </div>
  </header>

  <div class="picks" id="picksRow"></div>

  <div class="controls">
    <div class="ctl-group">
      <label>Sector</label>
      <select id="sectorFilter"><option value="">All</option></select>
    </div>
    <div class="ctl-group">
      <label>Min RVol: <span id="rvolVal">0.0x</span></label>
      <input type="range" id="rvolFilter" min="0" max="12" step="0.5" value="0">
    </div>
    <div class="ctl-group">
      <label>Min |Chg|: <span id="chgVal">any</span></label>
      <input type="range" id="chgFilter" min="0" max="3" step="0.1" value="0">
    </div>
    <div class="ctl-group">
      <label>Search</label>
      <input type="text" id="searchBox" placeholder="ticker…" style="width:90px;">
    </div>
    <label class="toggle">
      <input type="checkbox" id="watchlistOnly"> Watchlist only
    </label>
    <div class="spacer"></div>
    <span class="match-count" id="matchCount"></span>
    <button class="btn" id="exportBtn">Export CSV</button>
    <button class="btn" id="refreshBtn">Refresh</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th class="left" style="width:24px;"></th>
          <th class="left" data-sort="t">Ticker</th>
          <th class="left" data-sort="sector">Sector</th>
          <th data-sort="price">Price</th>
          <th data-sort="chg">Chg</th>
          <th data-sort="vol">Vol(M)</th>
          <th data-sort="rvol">RVol</th>
          <th data-sort="rsi">RSI</th>
          <th data-sort="macd">MACD</th>
          <th data-sort="trend">Trend</th>
          <th data-sort="rs">RS</th>
          <th data-sort="offHigh">Off 52wH</th>
          <th data-sort="marketCap">Mkt Cap</th>
          <th data-sort="pe">P/E</th>
          <th data-sort="analystRec">Rec</th>
          <th data-sort="nextEarnings">Next Earn</th>
          <th data-sort="score">Score</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>

  <footer>
    Score blends day-change momentum, relative volume, RSI sweet-spot (55–72), MACD, trend alignment, and relative strength.<br>
    Not a live feed guarantee — reflects the last scanner run. Not investment advice.
  </footer>

</div>

<script>
const DATA_URL = 'https://raw.githubusercontent.com/Romaita/stock-scanner/main/scanner_output.json';
const REFRESH_MS = 60000;

let allStocks = [];
let watchlist = new Set();
let sortKey = 'score';
let sortDir = -1;

const $ = id => document.getElementById(id);

function ratingFor(score){
  if(score >= 90) return {label:'Strong Buy', cls:'strongbuy'};
  if(score >= 70) return {label:'Buy', cls:'buy'};
  return {label:'Hold', cls:'hold'};
}

function scoreColor(score){
  if(score >= 90) return 'var(--green)';
  if(score >= 70) return 'var(--blue)';
  return 'var(--amber)';
}

function fmtChg(v){
  const sign = v > 0 ? '+' : '';
  const cls = v > 0.05 ? 'up' : v < -0.05 ? 'down' : 'flat';
  return `<span class="${cls}">${sign}${v.toFixed(1)}%</span>`;
}

function fmtTrend(t){
  return `<span class="trend-${t} ${t==='up'?'up':t==='down'?'down':'flat'}">${t}</span>`;
}

function fmtMarketCap(v){
  if(v == null) return '–';
  if(v >= 1e12) return (v/1e12).toFixed(2) + 'T';
  if(v >= 1e9) return (v/1e9).toFixed(1) + 'B';
  if(v >= 1e6) return (v/1e6).toFixed(0) + 'M';
  return v.toString();
}

function fmtRec(v){
  if(v == null) return '<span class="flat">–</span>';
  const cls = v > 0.3 ? 'up' : v < -0.3 ? 'down' : 'flat';
  const label = v > 0.5 ? 'Strong Buy' : v > 0.1 ? 'Buy' : v < -0.5 ? 'Strong Sell' : v < -0.1 ? 'Sell' : 'Neutral';
  return `<span class="${cls}">${label}</span>`;
}

function fmtEarnings(v){
  if(!v) return '–';
  try{
    const d = new Date(v);
    const days = Math.round((d - new Date()) / 86400000);
    if(days < 0) return '–';
    return `${d.toLocaleDateString(undefined,{month:'short',day:'numeric'})} (${days}d)`;
  }catch(e){ return '–'; }
}

async function loadData(){
  $('statusText').textContent = 'connecting…';
  $('statusDot').className = 'dot';
  try{
    const res = await fetch(DATA_URL + '?t=' + Date.now());
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    allStocks = json.stocks || [];
    const t = new Date(json.generated_at);
    $('statusText').textContent = `Connected ✓  updated ${t.toLocaleTimeString()}`;
    $('statusDot').className = 'dot live';
    populateSectors();
    render();
  }catch(e){
    $('statusText').textContent = 'connection failed — retrying';
    $('statusDot').className = 'dot err';
    console.error(e);
  }
}

function populateSectors(){
  const sel = $('sectorFilter');
  const current = sel.value;
  const sectors = [...new Set(allStocks.map(s => s.sector))].sort();
  sel.innerHTML = '<option value="">All</option>' + sectors.map(s => `<option value="${s}">${s}</option>`).join('');
  sel.value = current;
}

function getFiltered(){
  const sector = $('sectorFilter').value;
  const minRvol = parseFloat($('rvolFilter').value);
  const minChg = parseFloat($('chgFilter').value);
  const wlOnly = $('watchlistOnly').checked;
  const q = $('searchBox').value.trim().toUpperCase();

  return allStocks.filter(s => {
    if(sector && s.sector !== sector) return false;
    if(s.rvol < minRvol) return false;
    if(Math.abs(s.chg) < minChg) return false;
    if(wlOnly && !watchlist.has(s.t)) return false;
    if(q && !s.t.includes(q)) return false;
    return true;
  });
}

function sortStocks(list){
  return [...list].sort((a,b) => {
    let av = a[sortKey], bv = b[sortKey];
    if(typeof av === 'string') return sortDir * av.localeCompare(bv);
    return sortDir * ((av ?? 0) - (bv ?? 0));
  });
}

function renderPicks(){
  const top3 = [...allStocks].sort((a,b) => b.score - a.score).slice(0,3);
  $('picksRow').innerHTML = top3.map((s,i) => {
    const r = ratingFor(s.score);
    return `
      <div class="pick-card">
        <div class="pick-rank">#${i+1} pick · strong setup</div>
        <div class="pick-ticker">${s.t}</div>
        <div class="pick-sector">${s.sector}</div>
        <div class="pick-price-row">
          <span class="pick-price">$${s.price.toFixed(2)}</span>
          ${fmtChg(s.chg)}
        </div>
        <div class="pick-score-row">
          <span class="pick-score">Score ${s.score}/100</span>
          <span class="badge ${r.cls}">${r.label}</span>
        </div>
      </div>`;
  }).join('');
}

function renderTable(){
  const filtered = sortStocks(getFiltered());
  $('matchCount').textContent = `${filtered.length} match${filtered.length===1?'':'es'}`;

  $('tableBody').innerHTML = filtered.map(s => {
    const r = ratingFor(s.score);
    const starOn = watchlist.has(s.t) ? 'on' : '';
    return `
      <tr>
        <td class="star ${starOn}" data-ticker="${s.t}">★</td>
        <td class="ticker left">${s.t}</td>
        <td class="sector">${s.sector}</td>
        <td>$${s.price.toFixed(2)}</td>
        <td>${fmtChg(s.chg)}</td>
        <td>${s.vol.toFixed(2)}</td>
        <td>${s.rvol.toFixed(1)}x</td>
        <td>${s.rsi}</td>
        <td class="${s.macd>0?'up':s.macd<0?'down':'flat'}">${s.macd>0?'+':''}${s.macd.toFixed(1)}</td>
        <td>${fmtTrend(s.trend)}</td>
        <td>${s.rs}</td>
        <td class="${s.offHigh>=-5?'up':'flat'}">${s.offHigh.toFixed(1)}%</td>
        <td>${fmtMarketCap(s.marketCap)}</td>
        <td>${s.pe != null ? s.pe.toFixed(1) : '–'}</td>
        <td>${fmtRec(s.analystRec)}</td>
        <td>${fmtEarnings(s.nextEarnings)}</td>
        <td class="score-cell">
          <div class="score-bar-wrap">
            <span class="rating" style="color:${scoreColor(s.score)};background:${scoreColor(s.score)}22;">${r.label}</span>
            <span>${s.score}</span>
          </div>
        </td>
      </tr>`;
  }).join('');

  document.querySelectorAll('.star').forEach(el => {
    el.addEventListener('click', () => {
      const t = el.dataset.ticker;
      watchlist.has(t) ? watchlist.delete(t) : watchlist.add(t);
      renderTable();
    });
  });
}

function render(){
  renderPicks();
  renderTable();
}

function exportCSV(){
  const filtered = sortStocks(getFiltered());
  const headers = ['Ticker','Sector','Price','Chg%','Vol(M)','RVol','RSI','MACD','Trend','RS','OffHigh%','MktCap','PE','AnalystRec','NextEarnings','Score','Rating'];
  const rows = filtered.map(s => [
    s.t, s.sector, s.price, s.chg, s.vol, s.rvol, s.rsi, s.macd, s.trend, s.rs, s.offHigh,
    s.marketCap ?? '', s.pe ?? '', s.analystRec ?? '', s.nextEarnings ?? '',
    s.score, ratingFor(s.score).label
  ]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `scanner_export_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

// wire up controls
$('sectorFilter').addEventListener('change', renderTable);
$('rvolFilter').addEventListener('input', e => {
  $('rvolVal').textContent = parseFloat(e.target.value).toFixed(1) + 'x';
  renderTable();
});
$('chgFilter').addEventListener('input', e => {
  const v = parseFloat(e.target.value);
  $('chgVal').textContent = v === 0 ? 'any' : v.toFixed(1) + '%';
  renderTable();
});
$('searchBox').addEventListener('input', renderTable);
$('watchlistOnly').addEventListener('change', renderTable);
$('exportBtn').addEventListener('click', exportCSV);
$('refreshBtn').addEventListener('click', loadData);

document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.sort;
    if(sortKey === key) sortDir *= -1;
    else { sortKey = key; sortDir = -1; }
    document.querySelectorAll('th[data-sort]').forEach(h => h.classList.remove('active'));
    th.classList.add('active');
    renderTable();
  });
});

loadData();
setInterval(loadData, REFRESH_MS);
</script>
</body>
</html>
