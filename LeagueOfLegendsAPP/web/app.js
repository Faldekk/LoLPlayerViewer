const $ = id => document.getElementById(id);
const state = { player: null, matches: [], version: null, favorites: [], region: '', chartPoints: [], championMap: {}, liveFetchedAt: 0 };
const queueGroups = { Ranked:[420,440], Normal:[400,430,490], ARAM:[450], Arena:[1700,1750] };
const spellNames = {1:'SummonerBoost',3:'SummonerExhaust',4:'SummonerFlash',6:'SummonerHaste',7:'SummonerHeal',11:'SummonerSmite',12:'SummonerTeleport',14:'SummonerDot',21:'SummonerBarrier',32:'SummonerSnowball'};
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const number = value => new Intl.NumberFormat('pl-PL').format(value || 0);
const asset = (type,id) => state.version ? `https://ddragon.leagueoflegends.com/cdn/${state.version}/img/${type}/${encodeURIComponent(id)}.png` : '';

window.addEventListener('pywebviewready', async () => {
  const data = await window.pywebview.api.bootstrap();
  data.regions.forEach(region => $('region').add(new Option(region, region)));
  state.favorites = data.favorites;
  renderFavorites();
});

$('searchBtn').addEventListener('click', search);
$('riotId').addEventListener('keydown', event => { if (event.key === 'Enter') search(); });
$('modalClose').addEventListener('click', () => $('modal').classList.add('hidden'));
$('modal').addEventListener('click', event => { if (event.target === $('modal')) $('modal').classList.add('hidden'); });
$('favoriteBtn').addEventListener('click', toggleFavorite);
$('refreshLiveBtn').addEventListener('click', refreshLiveGame);
['queueFilter','resultFilter','championFilter'].forEach(id => $(id).addEventListener(id==='championFilter'?'input':'change', renderHistory));
document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('favoritesSelect').addEventListener('change', () => {
  const index = Number($('favoritesSelect').value);
  if (!Number.isInteger(index) || !state.favorites[index]) return;
  const favorite = state.favorites[index];
  $('riotId').value = favorite.riot_id; $('region').value = favorite.region;
  if ($('apiKey').value.trim()) search();
});

async function search(){
  hideError(); $('loader').classList.remove('hidden'); $('searchBtn').disabled=true;
  try {
    const result = await window.pywebview.api.search($('riotId').value,$('region').value,$('apiKey').value,Number($('matchCount').value));
    if(!result.ok){ showError(result.error); return; }
    state.player=result.player; state.matches=result.player.matches; state.version=result.ddragon_version; state.championMap=result.champion_map||{}; state.region=$('region').value; state.liveFetchedAt=Date.now();
    renderDashboard();
  } catch(error){ showError(`Nie udało się uruchomić wyszukiwania: ${error}`); }
  finally { $('loader').classList.add('hidden'); $('searchBtn').disabled=false; }
}

function renderDashboard(){
  $('emptyState').classList.add('hidden'); $('dashboard').classList.remove('hidden');
  $('playerName').textContent=state.player.riot_id; $('playerLevel').textContent=`Poziom ${state.player.level}`;
  $('profileIcon').src=asset('profileicon',state.player.profile_icon_id);
  renderRank('RANKED_SOLO_5x5','solo'); renderRank('RANKED_FLEX_SR','flex');
  updateFavoriteButton(); renderHistory(); renderChart(); renderStats(); renderLiveGame();
}

function championName(id){return state.championMap[String(id)]||`Champion ${id}`}
function spellIcon(id){const name=spellNames[id];return name?asset('spell',name):''}
function liveDuration(){
  const game=state.player?.live_game;if(!game)return 0;
  return Math.max(0,(game.game_length||0)+Math.floor((Date.now()-state.liveFetchedAt)/1000));
}
function formatClock(seconds){return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`}

function renderLiveGame(){
  const game=state.player?.live_game,content=$('liveGameContent');
  if(!game){content.innerHTML='<div class="live-empty"><strong>Gracz nie jest teraz w meczu</strong><span>Użyj „Odśwież”, aby sprawdzić ponownie.</span></div>';return;}
  const teams=[100,200];
  content.innerHTML=`<div class="live-header"><div><div class="live-indicator">● MECZ NA ŻYWO</div><strong>${esc(game.game_mode)} · ${esc(game.queue_id||'Tryb niestandardowy')}</strong></div><div id="liveClock" class="live-clock">${formatClock(liveDuration())}</div></div><div class="live-teams">${teams.map((teamId,index)=>`<section class="live-team ${index?'red':'blue'}"><h4>${index?'CZERWONA':'NIEBIESKA'} DRUŻYNA</h4>${game.participants.filter(p=>p.team_id===teamId).map(p=>{const champ=championName(p.champion_id),target=p.puuid===state.player.puuid;return `<div class="live-player ${target?'target':''}"><img src="${asset('champion',champ)}" alt=""><div><strong>${esc(p.riot_id)}${target?' · SZUKANY GRACZ':''}</strong><small>${esc(champ)}${p.bot?' · Bot':''}</small></div><div class="live-spells">${[p.spell1_id,p.spell2_id].map(id=>spellIcon(id)?`<img src="${spellIcon(id)}" title="Spell ${id}">`:'').join('')}</div></div>`}).join('')}</section>`).join('')}</div>`;
}

async function refreshLiveGame(){
  if(!state.player)return;
  const button=$('refreshLiveBtn');button.disabled=true;button.textContent='Sprawdzanie…';
  try{const result=await window.pywebview.api.refresh_live_game();if(!result.ok){showError(result.error);return}state.player.live_game=result.live_game;state.liveFetchedAt=Date.now();renderLiveGame();}
  catch(error){showError(`Nie udało się sprawdzić meczu: ${error}`)}
  finally{button.disabled=false;button.textContent='Odśwież'}
}

function renderRank(queue,prefix){
  const rank=state.player.ranks.find(item=>item.queueType===queue);
  if(!rank){ $(`${prefix}Rank`).textContent='Bez rangi'; $(`${prefix}Stats`).textContent='Brak rozegranych gier'; return; }
  const games=rank.wins+rank.losses, wr=games?Math.round(rank.wins/games*100):0;
  $(`${prefix}Rank`).textContent=`${title(rank.tier)} ${rank.rank} · ${rank.leaguePoints} LP`;
  $(`${prefix}Stats`).textContent=`${rank.wins} W / ${rank.losses} L · ${wr}% zwycięstw`;
}

function filteredMatches(){
  const q=$('queueFilter').value,r=$('resultFilter').value,c=$('championFilter').value.trim().toLowerCase();
  return state.matches.filter(match => {
    if(queueGroups[q]&&!queueGroups[q].includes(match.queue_id)) return false;
    if(r==='Wygrane'&&match.result!=='Wygrana') return false;
    if(r==='Przegrane'&&match.result!=='Przegrana') return false;
    return !c||match.champion.toLowerCase().includes(c);
  });
}

function renderHistory(){
  const matches=filteredMatches();
  $('matchList').innerHTML=matches.map((match,index)=>`<article class="match-row ${match.result==='Wygrana'?'win':'loss'}" data-index="${state.matches.indexOf(match)}">
    <div class="result-bar"></div><img class="champ-icon" src="${asset('champion',match.champion)}" alt="">
    <div><div class="result">${esc(match.result)}</div><div class="subtext">${esc(match.duration)}</div></div>
    <div><div class="champ-name">${esc(match.champion)}</div><div class="subtext">${match.cs||0} CS · ${number(match.damage)} DMG</div></div>
    <div><div class="kda">${match.kills} / ${match.deaths} / ${match.assists}</div><div class="subtext">${kda(match).toFixed(2)} KDA</div></div>
    <div class="queue">${esc(match.queue)}</div><div class="date">${esc(match.date)}</div></article>`).join('') || '<div class="empty-state"><p>Brak meczów spełniających filtry.</p></div>';
  document.querySelectorAll('.match-row').forEach(row=>row.addEventListener('click',()=>openDetails(state.matches[Number(row.dataset.index)])));
}

function renderChart(){
  const matches=state.matches.filter(m=>[420,440].includes(m.queue_id)).reverse(), canvas=$('kdaChart'), box=canvas.parentElement;
  const scale=window.devicePixelRatio||1,w=box.clientWidth-40,h=box.clientHeight-40; canvas.width=w*scale; canvas.height=h*scale;
  const ctx=canvas.getContext('2d'); ctx.scale(scale,scale); ctx.clearRect(0,0,w,h);
  state.chartPoints=[];
  if(!matches.length){ctx.fillStyle='#8e98b3';ctx.font='14px Segoe UI';ctx.fillText('Brak gier rankingowych w pobranym zestawie.',25,40);hideChartTooltip();return;}
  const values=matches.map(kda),max=Math.max(4,...values)*1.12,pad={l:42,r:20,t:28,b:38},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
  ctx.strokeStyle='#272f48';ctx.fillStyle='#8e98b3';ctx.font='11px Segoe UI';ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=pad.t+ch*i/4;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();ctx.fillText((max*(1-i/4)).toFixed(1),4,y+4)}
  const point=(v,i)=>({x:pad.l+(matches.length===1?cw/2:cw*i/(matches.length-1)),y:pad.t+ch*(1-v/max)});
  ctx.strokeStyle='#806cff';ctx.lineWidth=3;ctx.beginPath();values.forEach((v,i)=>{const p=point(v,i);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y)});ctx.stroke();
  state.chartPoints=values.map((v,i)=>({...point(v,i),match:matches[i]}));
  state.chartPoints.forEach(({x,y,match})=>{ctx.fillStyle=match.result==='Wygrana'?'#35d6a2':'#ff6382';ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill()});
  const wins=matches.filter(m=>m.result==='Wygrana').length;$('rankedSummary').textContent=`${wins} W · ${matches.length-wins} L · ${Math.round(wins/matches.length*100)}% WR`;
}

const chartTooltip=document.createElement('div');
chartTooltip.className='chart-tooltip hidden';
document.body.appendChild(chartTooltip);

function chartPointAt(event){
  const canvas=$('kdaChart'),rect=canvas.getBoundingClientRect();
  const x=(event.clientX-rect.left)*(canvas.width/(window.devicePixelRatio||1))/rect.width;
  const y=(event.clientY-rect.top)*(canvas.height/(window.devicePixelRatio||1))/rect.height;
  let nearest=null,distance=Infinity;
  state.chartPoints.forEach(point=>{const d=Math.hypot(point.x-x,point.y-y);if(d<distance){nearest=point;distance=d}});
  return distance<=14?nearest:null;
}

function showChartTooltip(event,match){
  const won=match.result==='Wygrana';
  chartTooltip.innerHTML=`<div class="tooltip-head"><img src="${asset('champion',match.champion)}" alt=""><div><strong>${esc(match.champion)}</strong><span class="${won?'tooltip-win':'tooltip-loss'}">${esc(match.result)}</span></div></div><div class="tooltip-kda">${match.kills} / ${match.deaths} / ${match.assists} <span>${kda(match).toFixed(2)} KDA</span></div><div class="tooltip-stats"><span>${match.cs||0} CS</span><span>${number(match.damage)} DMG</span></div><div class="tooltip-meta">${esc(match.queue)} · ${esc(match.duration)}<br>${esc(match.date)}</div><div class="tooltip-hint">Kliknij, aby zobaczyć szczegóły</div>`;
  chartTooltip.classList.remove('hidden');
  const gap=16,tip=chartTooltip.getBoundingClientRect();
  chartTooltip.style.left=`${Math.min(window.innerWidth-tip.width-gap,event.clientX+gap)}px`;
  chartTooltip.style.top=`${Math.max(gap,Math.min(window.innerHeight-tip.height-gap,event.clientY-tip.height/2))}px`;
}

function hideChartTooltip(){chartTooltip.classList.add('hidden')}

$('kdaChart').addEventListener('mousemove',event=>{
  const point=chartPointAt(event);
  $('kdaChart').style.cursor=point?'pointer':'default';
  point?showChartTooltip(event,point.match):hideChartTooltip();
});
$('kdaChart').addEventListener('mouseleave',hideChartTooltip);
$('kdaChart').addEventListener('click',event=>{const point=chartPointAt(event);if(point)openDetails(point.match)});

function renderStats(){
  const games=state.matches.length,wins=state.matches.filter(m=>m.result==='Wygrana').length;
  const avg=fn=>games?state.matches.reduce((s,m)=>s+fn(m),0)/games:0;
  $('metricWinrate').textContent=`${Math.round(wins/games*100)||0}%`;$('metricKda').textContent=avg(kda).toFixed(2);
  $('metricCs').textContent=avg(m=>(m.duration_seconds?m.cs/(m.duration_seconds/60):0)).toFixed(1);$('metricDamage').textContent=number(Math.round(avg(m=>m.damage||0)));
  const champs={};state.matches.forEach(m=>{const s=champs[m.champion]??={games:0,wins:0,kills:0,deaths:0,assists:0};s.games++;s.wins+=m.result==='Wygrana';s.kills+=m.kills;s.deaths+=m.deaths;s.assists+=m.assists});
  $('championStats').innerHTML=Object.entries(champs).sort((a,b)=>b[1].games-a[1].games).slice(0,10).map(([name,s])=>`<div class="champ-stat"><span class="champ-main"><img src="${asset('champion',name)}">${esc(name)}</span><span>${s.games} gier</span><span>${s.wins} W / ${s.games-s.wins} L</span><span>${Math.round(s.wins/s.games*100)}% WR</span><span>${((s.kills+s.assists)/Math.max(1,s.deaths)).toFixed(2)} KDA</span></div>`).join('');
}

function openDetails(match){
  const teams=[...new Set(match.participants.map(p=>p.team_id))].slice(0,2);
  $('modalContent').innerHTML=`<div class="modal-title"><div class="eyebrow">${esc(match.result.toUpperCase())}</div><h2>${esc(match.champion)} · ${match.kills} / ${match.deaths} / ${match.assists}</h2><p>${esc(match.queue)} · ${esc(match.duration)} · ${esc(match.date)}</p></div><div class="teams">${teams.map((id,i)=>{const players=match.participants.filter(p=>p.team_id===id),won=players[0]?.win;return `<section class="team"><h4 style="color:${won?'#35d6a2':'#ff6382'}">DRUŻYNA ${i+1} · ${won?'ZWYCIĘSTWO':'PORAŻKA'}</h4>${players.map(p=>`<div class="participant"><img src="${asset('champion',p.champion)}"><div><strong>${esc(p.riot_id)}</strong><small>${esc(p.champion)} · ${p.kills}/${p.deaths}/${p.assists} · ${p.cs} CS · ${number(p.damage)} DMG</small></div><div class="items">${p.items.map(id=>`<img src="${asset('item',id)}">`).join('')}</div></div>`).join('')}</section>`}).join('')}</div>`;
  $('modal').classList.remove('hidden');
}

async function toggleFavorite(){
  if(!state.player)return;const result=await window.pywebview.api.toggle_favorite(state.player.riot_id,state.region);
  if(!result.ok){showError(result.error);return}state.favorites=result.favorites;renderFavorites();updateFavoriteButton();
}
function renderFavorites(){$('favoritesSelect').innerHTML='<option value="">'+(state.favorites.length?'Wybierz gracza…':'Brak zapisanych graczy')+'</option>'+state.favorites.map((f,i)=>`<option value="${i}">${esc(f.riot_id)} · ${esc(f.region)}</option>`).join('')}
function updateFavoriteButton(){const saved=state.favorites.some(f=>f.riot_id.toLowerCase()===state.player.riot_id.toLowerCase()&&f.region===state.region);$('favoriteBtn').textContent=saved?'★ Usuń':'☆ Dodaj'}
function showTab(id){document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.tab===id));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===id));if(id==='ranked')setTimeout(renderChart,50);if(id==='live'&&state.player)refreshLiveGame()}
function showError(message){$('errorBox').textContent=message;$('errorBox').classList.remove('hidden')}
function hideError(){$('errorBox').classList.add('hidden')}
function kda(match){return (match.kills+match.assists)/Math.max(1,match.deaths)}
function title(value){const s=String(value||'').toLowerCase();return s.charAt(0).toUpperCase()+s.slice(1)}
window.addEventListener('resize',()=>{if(state.player&&$('ranked').classList.contains('active'))renderChart()});
setInterval(()=>{const clock=$('liveClock');if(clock)clock.textContent=formatClock(liveDuration())},1000);
setInterval(()=>{if(state.player&&$('live').classList.contains('active'))refreshLiveGame()},60000);
