const $ = id => document.getElementById(id);
const defaultSettings={theme:'dark',accent:'purple',region:'Europa Pn.-Wsch. (EUNE)',matches:'30',liveRefresh:'5',compact:false};
const savedSettings=(()=>{try{return {...defaultSettings,...JSON.parse(localStorage.getItem('lpvSettings')||'{}')}}catch{return {...defaultSettings}}})();
const state = { player: null, matches: [], version: null, favorites: [], region: '', chartPoints: [], championMap: {}, itemMap: {}, liveFetchedAt: 0, localLive: null, localFetchedAt: 0, liveInsights:{}, defaultApiAvailable:false, settings:savedSettings };
const queueGroups = { Ranked:[420,440], Normal:[400,430,490], ARAM:[450], Arena:[1700,1750] };
const spellNames = {1:'SummonerBoost',3:'SummonerExhaust',4:'SummonerFlash',6:'SummonerHaste',7:'SummonerHeal',11:'SummonerSmite',12:'SummonerTeleport',14:'SummonerDot',21:'SummonerBarrier',32:'SummonerSnowball'};
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const number = value => new Intl.NumberFormat('pl-PL').format(value || 0);
const asset = (type,id) => state.version ? `https://ddragon.leagueoflegends.com/cdn/${state.version}/img/${type}/${encodeURIComponent(id)}.png` : '';

window.addEventListener('pywebviewready', async () => {
  const data = await window.pywebview.api.bootstrap();
  data.regions.forEach(region => {$('region').add(new Option(region,region));$('settingRegion').add(new Option(region,region))});
  state.favorites = data.favorites;
  state.defaultApiAvailable = Boolean(data.default_api_available);
  if(data.api_key)$('apiKey').value=data.api_key;
  $('apiKeyStatus').textContent=data.api_key_saved?'Używany jest Twój zapamiętany klucz.':data.api_key?'Wczytano Twój klucz z lokalnego config.json.':data.default_api_available?'Domyślne API jest aktywne. Własny klucz jest opcjonalny.':'Dodaj własny klucz Riot API.';
  applySettings();
  renderFavorites();
});

$('searchBtn').addEventListener('click', search);
$('riotId').addEventListener('keydown', event => { if (event.key === 'Enter') search(); });
$('modalClose').addEventListener('click', () => $('modal').classList.add('hidden'));
$('modal').addEventListener('click', event => { if (event.target === $('modal')) $('modal').classList.add('hidden'); });
$('modalContent').addEventListener('click', event => {
  const participant=event.target.closest('[data-player-riot-id]');
  if(participant)openParticipantProfile(participant.dataset.playerRiotId);
});
$('modalContent').addEventListener('keydown', event => {
  const participant=event.target.closest('[data-player-riot-id]');
  if(participant&&(event.key==='Enter'||event.key===' ')){
    event.preventDefault();
    openParticipantProfile(participant.dataset.playerRiotId);
  }
});
$('favoriteBtn').addEventListener('click', toggleFavorite);
$('refreshLiveBtn').addEventListener('click', async()=>{await refreshLiveGame();await refreshLocalLiveStats();await refreshLiveInsights()});
$('chartMetric').addEventListener('change',renderChart);
$('compareBtn').addEventListener('click',comparePlayers);
$('compareRiotId').addEventListener('keydown',event=>{if(event.key==='Enter')comparePlayers()});
$('saveSettingsBtn').addEventListener('click',saveSettings);
$('toggleApiKey').addEventListener('click',()=>{const input=$('apiKey'),visible=input.type==='text';input.type=visible?'password':'text';$('toggleApiKey').textContent=visible?'Pokaż':'Ukryj'});
['queueFilter','resultFilter','championFilter'].forEach(id => $(id).addEventListener(id==='championFilter'?'input':'change', renderHistory));
document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('favoritesSelect').addEventListener('change', () => {
  const index = Number($('favoritesSelect').value);
  if (!Number.isInteger(index) || !state.favorites[index]) return;
  const favorite = state.favorites[index];
  $('riotId').value = favorite.riot_id; $('region').value = favorite.region;
  if ($('apiKey').value.trim()||state.defaultApiAvailable) search();
});

async function search(){
  if(!$('apiKey').value.trim()&&!state.defaultApiAvailable){showTab('settings');showError('Dodaj klucz Riot API w Ustawieniach.');return;}
  hideError(); $('loader').classList.remove('hidden'); $('searchBtn').disabled=true;
  try {
    const result = await window.pywebview.api.search($('riotId').value,$('region').value,$('apiKey').value,Number($('matchCount').value));
    if(!result.ok){if(result.api_key_invalid)requestNewApiKey(result.error);else showError(result.error);return;}
    state.player=result.player; state.matches=result.player.matches; state.version=result.ddragon_version; state.championMap=result.champion_map||{}; state.itemMap=result.item_map||{}; state.liveInsights={}; state.region=$('region').value; state.liveFetchedAt=Date.now();
    renderDashboard();
    $('apiKeyStatus').textContent=$('apiKey').value.trim()?'Twój klucz został zweryfikowany i zapisany lokalnie.':'Połączono przez domyślne API.';
  } catch(error){ showError(`Nie udało się uruchomić wyszukiwania: ${error}`); }
  finally { $('loader').classList.add('hidden'); $('searchBtn').disabled=false; }
}

function renderDashboard(){
  $('emptyState').classList.add('hidden'); $('dashboard').classList.remove('hidden');
  document.querySelector('.profile-strip').classList.remove('hidden');
  $('playerName').textContent=state.player.riot_id; $('playerLevel').textContent=`Poziom ${state.player.level}`;
  $('profileIcon').src=asset('profileicon',state.player.profile_icon_id);
  renderRank('RANKED_SOLO_5x5','solo'); renderRank('RANKED_FLEX_SR','flex');
  updateFavoriteButton(); renderHistory(); renderChart(); renderStats(); renderLiveGame();
}

function championName(id){return state.championMap[String(id)]||`Champion ${id}`}
function spellIcon(id){const name=spellNames[id];return name?asset('spell',name):''}
function liveDuration(){
  if(state.localLive)return Math.max(0,(state.localLive.game_time||0)+Math.floor((Date.now()-state.localFetchedAt)/1000));
  const game=state.player?.live_game;if(!game)return 0;
  return Math.max(0,(game.game_length||0)+Math.floor((Date.now()-state.liveFetchedAt)/1000));
}
function formatClock(seconds){return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`}

function renderLiveGame(){
  if(state.localLive){renderLocalLiveStats();return;}
  const game=state.player?.live_game,content=$('liveGameContent');
  if(!game){content.innerHTML='<div class="live-empty"><strong>Gracz nie jest teraz w meczu</strong><span>Użyj „Odśwież”, aby sprawdzić ponownie.</span></div>';return;}
  const teams=[100,200];
  content.innerHTML=`<div class="live-header"><div><div class="live-indicator">● MECZ NA ŻYWO</div><strong>${esc(game.game_mode)} · ${esc(game.queue_id||'Tryb niestandardowy')}</strong></div><div id="liveClock" class="live-clock">${formatClock(liveDuration())}</div></div><div class="live-teams">${teams.map((teamId,index)=>`<section class="live-team ${index?'red':'blue'}"><h4>${index?'CZERWONA':'NIEBIESKA'} DRUŻYNA</h4>${game.participants.filter(p=>p.team_id===teamId).map(p=>{const champ=championName(p.champion_id),target=p.puuid===state.player.puuid;return `<div class="live-player ${target?'target':''}"><img src="${asset('champion',champ)}" alt=""><div><strong>${esc(p.riot_id)}${target?' · SZUKANY GRACZ':''}</strong><small>${esc(champ)}${p.bot?' · Bot':''}</small>${renderLiveInsight(state.liveInsights[p.puuid])}</div><div class="live-spells">${[p.spell1_id,p.spell2_id].map(id=>spellIcon(id)?`<img src="${spellIcon(id)}" title="Spell ${id}">`:'').join('')}</div></div>`}).join('')}</section>`).join('')}</div>`;
}

function renderLocalLiveStats(){
  const live=state.localLive,content=$('liveGameContent'),teams=['ORDER','CHAOS'];
  content.innerHTML=`<div class="live-header"><div><div class="live-indicator">● LIVE STATS · TEN KOMPUTER</div><strong>${esc(live.game_mode)} · statystyki odświeżane co 5 sekund</strong></div><div><div id="liveClock" class="live-clock">${formatClock(liveDuration())}</div><div class="live-gold">${number(live.current_gold)} GOLD</div></div></div><div class="live-teams">${teams.map((team,index)=>`<section class="live-team ${index?'red':'blue'}"><h4>${index?'CZERWONA':'NIEBIESKA'} DRUŻYNA</h4>${live.players.filter(p=>p.team===team).map(p=>{const active=p.riot_id.toLowerCase()===live.active_riot_id.toLowerCase(),insight=liveInsightByRiotId(p.riot_id);return `<div class="live-stat-player ${active?'target':''}"><img class="live-champion" src="${asset('champion',p.champion)}" alt=""><div class="live-player-name"><strong>${esc(p.riot_id)}${active?' · TY':''}</strong><small>${esc(p.champion)} · ${esc(p.position||'Pozycja nieznana')} · lvl ${p.level}</small>${renderLiveInsight(insight)}</div><div class="live-score"><strong>${p.kills} / ${p.deaths} / ${p.assists}</strong><small>${p.cs} CS · ${p.vision} vision</small></div><div class="live-items">${p.items.map(id=>`<img src="${asset('item',id)}" data-item-id="${id}" alt="">`).join('')}</div>${p.is_dead?`<span class="dead-badge">Odrodzenie: ${p.respawn}s</span>`:''}</div>`}).join('')}</section>`).join('')}</div>`;
}

function renderLiveInsight(insight){
  if(!insight)return '<small class="live-insight loading">Analizowanie ostatnich gier…</small>';
  const result=insight.streak_result,streak=result==='—'?'Brak historii':`${insight.streak_count}${result}`;
  const mastery=insight.mastery_level?`M${insight.mastery_level} · ${number(insight.mastery_points)} pkt`:'Brak mastery';
  return `<small class="live-insight"><b class="${result==='W'?'streak-win':result==='L'?'streak-loss':''}">${streak}</b><span>${mastery}</span><span>${insight.champion_games}/${insight.sample_size} ostatnich gier</span></small>`;
}

function liveInsightByRiotId(riotId){
  const game=state.player?.live_game,participant=game?.participants.find(p=>String(p.riot_id).toLowerCase()===String(riotId).toLowerCase());
  return participant?state.liveInsights[participant.puuid]:null;
}

async function refreshLiveInsights(){
  const participants=state.player?.live_game?.participants||[];
  if(!participants.length)return;
  try{
    const payload=participants.map(p=>({puuid:p.puuid,champion_id:p.champion_id}));
    const result=await window.pywebview.api.live_player_insights(payload);
    if(!result.ok){if(result.api_key_invalid)requestNewApiKey(result.error);else showError(result.error);return;}
    state.liveInsights=Object.fromEntries(result.insights.map(item=>[item.puuid,item]));
    renderLiveGame();
  }catch(error){showError(`Nie udało się pobrać formy graczy: ${error}`)}
}

async function refreshLocalLiveStats(){
  if(!state.player)return;
  try{
    const result=await window.pywebview.api.local_live_stats(),local=result.live_stats;
    const searched=state.player.riot_id.trim().toLowerCase();
    state.localLive=local&&String(local.active_riot_id||'').trim().toLowerCase()===searched?local:null;
    state.localFetchedAt=Date.now();renderLiveGame();
  }catch(error){state.localLive=null}
}

async function refreshLiveGame(){
  if(!state.player)return;
  const button=$('refreshLiveBtn');button.disabled=true;button.textContent='Sprawdzanie…';
  try{const result=await window.pywebview.api.refresh_live_game();if(!result.ok){if(result.api_key_invalid)requestNewApiKey(result.error);else showError(result.error);return}state.player.live_game=result.live_game;state.liveFetchedAt=Date.now();renderLiveGame();}
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
  const metric=$('chartMetric').value;
  const calculators={kda:m=>kda(m),csmin:m=>m.duration_seconds?m.cs/(m.duration_seconds/60):0,damage:m=>m.damage||0,vision:m=>m.vision||0};
  const values=metric==='winrate'?matches.map((_,i)=>matches.slice(0,i+1).filter(m=>m.result==='Wygrana').length/(i+1)*100):matches.map(calculators[metric]||calculators.kda);
  const minimum=metric==='winrate'?100:metric==='damage'?1000:4,max=Math.max(minimum,...values)*1.12,pad={l:52,r:20,t:28,b:38},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
  ctx.strokeStyle='#272f48';ctx.fillStyle='#8e98b3';ctx.font='11px Segoe UI';ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=pad.t+ch*i/4,value=max*(1-i/4);ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();ctx.fillText(metric==='damage'?Math.round(value/1000)+'k':value.toFixed(metric==='winrate'?0:1),4,y+4)}
  const point=(v,i)=>({x:pad.l+(matches.length===1?cw/2:cw*i/(matches.length-1)),y:pad.t+ch*(1-v/max)});
  ctx.strokeStyle=getComputedStyle(document.body).getPropertyValue('--purple').trim()||'#806cff';ctx.lineWidth=3;ctx.beginPath();values.forEach((v,i)=>{const p=point(v,i);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y)});ctx.stroke();
  state.chartPoints=values.map((v,i)=>({...point(v,i),match:matches[i],metricValue:v,metric}));
  state.chartPoints.forEach(({x,y,match})=>{ctx.fillStyle=match.result==='Wygrana'?'#35d6a2':'#ff6382';ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill()});
  const wins=matches.filter(m=>m.result==='Wygrana').length;$('rankedSummary').textContent=`${wins} W · ${matches.length-wins} L · ${Math.round(wins/matches.length*100)}% WR`;
}

const chartTooltip=document.createElement('div');
chartTooltip.className='chart-tooltip hidden';
document.body.appendChild(chartTooltip);

const itemTooltip=document.createElement('div');
itemTooltip.className='item-tooltip hidden';
document.body.appendChild(itemTooltip);
let activeItemId='';

function showItemTooltip(event,itemId){
  const item=state.itemMap[String(itemId)];
  if(activeItemId!==String(itemId)){
    activeItemId=String(itemId);
    itemTooltip.innerHTML=item?`<div class="item-tooltip-head"><img src="${asset('item',itemId)}" alt=""><div><strong>${esc(item.name)}</strong><span>Item #${esc(itemId)}</span></div></div><p>${esc(item.description||item.plaintext||'Brak opisu dla tego itemu.')}</p><div class="item-gold"><span>${item.purchasable?`Koszt: ${number(item.total)} gold`:'Niedostępny w sklepie'}</span><span>Sprzedaż: ${number(item.sell)} gold</span></div>`:`<div class="item-tooltip-head"><img src="${asset('item',itemId)}" alt=""><div><strong>Nieznany item</strong><span>Item #${esc(itemId)}</span></div></div><p>Brak danych w aktualnej wersji Data Dragon. Item mógł zostać usunięty z gry.</p>`;
  }
  itemTooltip.classList.remove('hidden');
  const gap=16,tip=itemTooltip.getBoundingClientRect();
  itemTooltip.style.left=`${Math.max(gap,Math.min(window.innerWidth-tip.width-gap,event.clientX+gap))}px`;
  itemTooltip.style.top=`${Math.max(gap,Math.min(window.innerHeight-tip.height-gap,event.clientY+gap))}px`;
}

document.addEventListener('mousemove',event=>{
  const image=event.target.closest?.('img[data-item-id]');
  if(image){showItemTooltip(event,image.dataset.itemId)}else{itemTooltip.classList.add('hidden');activeItemId=''}
});

const formMatchTooltip=document.createElement('div');
formMatchTooltip.className='form-match-tooltip hidden';
document.body.appendChild(formMatchTooltip);
let activeFormMatch='';

document.addEventListener('mousemove',event=>{
  const dot=event.target.closest?.('[data-form-match-index]');
  if(!dot){formMatchTooltip.classList.add('hidden');activeFormMatch='';return;}
  const index=Number(dot.dataset.formMatchIndex),match=state.matches[index];if(!match)return;
  if(activeFormMatch!==String(index)){
    activeFormMatch=String(index);const won=match.result==='Wygrana';
    formMatchTooltip.innerHTML=`<div class="tooltip-head"><img src="${asset('champion',match.champion)}" alt=""><div><strong>${esc(match.champion)}</strong><span class="${won?'tooltip-win':'tooltip-loss'}">${esc(match.result)}</span></div></div><div class="tooltip-kda">${match.kills} / ${match.deaths} / ${match.assists}<span>${kda(match).toFixed(2)} KDA</span></div><div class="tooltip-stats"><span>${match.cs} CS</span><span>${number(match.damage)} DMG</span></div><div class="tooltip-meta">${esc(match.queue)} · ${esc(match.duration)}<br>${esc(match.date)}</div>`;
  }
  formMatchTooltip.classList.remove('hidden');const gap=14,tip=formMatchTooltip.getBoundingClientRect();formMatchTooltip.style.left=`${Math.max(gap,Math.min(window.innerWidth-tip.width-gap,event.clientX+gap))}px`;formMatchTooltip.style.top=`${Math.max(gap,Math.min(window.innerHeight-tip.height-gap,event.clientY+gap))}px`;
});

function chartPointAt(event){
  const canvas=$('kdaChart'),rect=canvas.getBoundingClientRect();
  const x=(event.clientX-rect.left)*(canvas.width/(window.devicePixelRatio||1))/rect.width;
  const y=(event.clientY-rect.top)*(canvas.height/(window.devicePixelRatio||1))/rect.height;
  let nearest=null,distance=Infinity;
  state.chartPoints.forEach(point=>{const d=Math.hypot(point.x-x,point.y-y);if(d<distance){nearest=point;distance=d}});
  return distance<=14?nearest:null;
}

function showChartTooltip(event,match,point){
  const won=match.result==='Wygrana';
  const metricLabels={kda:'KDA',csmin:'CS/min',damage:'Obrażenia',vision:'Vision',winrate:'Win rate'};
  const metricValue=point.metric==='damage'?number(Math.round(point.metricValue)):point.metric==='winrate'?`${Math.round(point.metricValue)}%`:point.metricValue.toFixed(2);
  chartTooltip.innerHTML=`<div class="tooltip-head"><img src="${asset('champion',match.champion)}" alt=""><div><strong>${esc(match.champion)}</strong><span class="${won?'tooltip-win':'tooltip-loss'}">${esc(match.result)}</span></div></div><div class="tooltip-kda">${metricLabels[point.metric]} <span>${metricValue}</span></div><div class="tooltip-stats"><span>${match.kills}/${match.deaths}/${match.assists}</span><span>${match.cs||0} CS</span></div><div class="tooltip-meta">${esc(match.queue)} · ${esc(match.duration)}<br>${esc(match.date)}</div><div class="tooltip-hint">Kliknij, aby zobaczyć szczegóły</div>`;
  chartTooltip.classList.remove('hidden');
  const gap=16,tip=chartTooltip.getBoundingClientRect();
  chartTooltip.style.left=`${Math.min(window.innerWidth-tip.width-gap,event.clientX+gap)}px`;
  chartTooltip.style.top=`${Math.max(gap,Math.min(window.innerHeight-tip.height-gap,event.clientY-tip.height/2))}px`;
}

function hideChartTooltip(){chartTooltip.classList.add('hidden')}

$('kdaChart').addEventListener('mousemove',event=>{
  const point=chartPointAt(event);
  $('kdaChart').style.cursor=point?'pointer':'default';
  point?showChartTooltip(event,point.match,point):hideChartTooltip();
});
$('kdaChart').addEventListener('mouseleave',hideChartTooltip);
$('kdaChart').addEventListener('click',event=>{const point=chartPointAt(event);if(point)openDetails(point.match)});

function renderStats(){
  const games=state.matches.length,wins=state.matches.filter(m=>m.result==='Wygrana').length;
  const avg=fn=>games?state.matches.reduce((s,m)=>s+fn(m),0)/games:0;
  $('metricWinrate').textContent=`${Math.round(wins/games*100)||0}%`;$('metricKda').textContent=avg(kda).toFixed(2);
  $('metricCs').textContent=avg(m=>(m.duration_seconds?m.cs/(m.duration_seconds/60):0)).toFixed(1);$('metricDamage').textContent=number(Math.round(avg(m=>m.damage||0)));
  const champs={};state.matches.forEach(m=>{const s=champs[m.champion]??={games:0,wins:0,kills:0,deaths:0,assists:0};s.games++;s.wins+=m.result==='Wygrana';s.kills+=m.kills;s.deaths+=m.deaths;s.assists+=m.assists});
  $('championStats').innerHTML=Object.entries(champs).sort((a,b)=>b[1].games-a[1].games).slice(0,10).map(([name,s])=>`<div class="champ-stat" data-champion="${esc(name)}"><span class="champ-main"><img src="${asset('champion',name)}">${esc(name)}</span><span>${s.games} gier</span><span>${s.wins} W / ${s.games-s.wins} L</span><span>${Math.round(s.wins/s.games*100)}% WR</span><span>${((s.kills+s.assists)/Math.max(1,s.deaths)).toFixed(2)} KDA</span></div>`).join('');
  document.querySelectorAll('[data-champion]').forEach(row=>row.addEventListener('click',()=>openChampionDetails(row.dataset.champion)));
  renderRoleStats();renderFormStats();
}

function renderRoleStats(){
  const labels={TOP:'Top',JUNGLE:'Jungle',MIDDLE:'Mid',BOTTOM:'ADC',UTILITY:'Support',UNKNOWN:'Nieznana'};
  const roles={};state.matches.forEach(m=>{const key=m.position||'UNKNOWN',s=roles[key]??={games:0,wins:0,kda:0};s.games++;s.wins+=m.result==='Wygrana';s.kda+=kda(m)});
  $('roleStats').innerHTML=Object.entries(roles).sort((a,b)=>b[1].games-a[1].games).map(([role,s])=>`<div class="role-row"><strong>${labels[role]||role}</strong><span>${s.games} gier</span><span>${Math.round(s.wins/s.games*100)}% WR</span><span>${(s.kda/s.games).toFixed(2)} KDA</span></div>`).join('')||'<span class="subtext">Brak danych o pozycjach.</span>';
}

function renderFormStats(){
  if(!state.matches.length){$('formStats').innerHTML='<span class="subtext">Brak meczów do analizy.</span>';return;}
  const first=state.matches[0]?.result,current=state.matches.findIndex(m=>m.result!==first),streak=current<0?state.matches.length:current;
  const last10=state.matches.slice(0,10),wins=last10.filter(m=>m.result==='Wygrana').length;
  $('formStats').innerHTML=`<div class="form-hero"><strong>${streak} ${first==='Wygrana'?'zwycięstwa':'porażki'} z rzędu</strong><span>Ostatnie ${last10.length} gier: ${wins} W / ${last10.length-wins} L · ${last10.length?Math.round(wins/last10.length*100):0}% WR</span></div><div class="form-sequence">${[...last10].reverse().map(m=>`<span class="form-dot ${m.result==='Wygrana'?'win':'loss'}" data-form-match-index="${state.matches.indexOf(m)}">${m.result==='Wygrana'?'W':'L'}</span>`).join('')}</div>`;
}

function openChampionDetails(champion){
  const games=state.matches.filter(m=>m.champion===champion),wins=games.filter(m=>m.result==='Wygrana').length,avg=fn=>games.reduce((s,m)=>s+fn(m),0)/Math.max(1,games.length);
  $('modalContent').innerHTML=`<div class="modal-title"><div class="eyebrow">CHAMPION ANALYSIS</div><h2>${esc(champion)}</h2><p>${games.length} gier w pobranej historii</p></div><div class="champion-detail-grid"><article><span>WIN RATE</span><strong>${Math.round(wins/games.length*100)}%</strong></article><article><span>ŚREDNIE KDA</span><strong>${avg(kda).toFixed(2)}</strong></article><article><span>CS / MIN</span><strong>${avg(m=>m.duration_seconds?m.cs/(m.duration_seconds/60):0).toFixed(1)}</strong></article><article><span>DMG / MIN</span><strong>${number(Math.round(avg(m=>m.duration_seconds?m.damage/(m.duration_seconds/60):0)))}</strong></article></div><div class="match-list">${games.map(m=>`<div class="match-row ${m.result==='Wygrana'?'win':'loss'}"><div class="result-bar"></div><img class="champ-icon" src="${asset('champion',champion)}"><div class="result">${esc(m.result)}</div><div><strong>${m.kills}/${m.deaths}/${m.assists}</strong><div class="subtext">${m.cs} CS · ${number(m.damage)} DMG</div></div><div class="kda">${kda(m).toFixed(2)} KDA</div><div class="queue">${esc(m.queue)}</div><div class="date">${esc(m.date)}</div></div>`).join('')}</div>`;
  $('modal').classList.remove('hidden');
}

async function openDetails(match){
  const teams=[...new Set(match.participants.map(p=>p.team_id))].slice(0,2);
  const premades=detectPremades(match);
  $('modalContent').innerHTML=`<div class="modal-title"><div class="eyebrow">${esc(match.result.toUpperCase())}</div><h2>${esc(match.champion)} · ${match.kills} / ${match.deaths} / ${match.assists}</h2><p>${esc(match.queue)} · ${esc(match.duration)} · ${esc(match.date)}</p><small class="premade-explanation">Każdy gracz ma kolorowe obramowanie. Tylko powtarzający się kolor w tej samej drużynie oznacza możliwe premade — jest to estymacja.</small></div><div class="teams">${teams.map((id,i)=>{const players=match.participants.filter(p=>p.team_id===id),won=players[0]?.win;return `<section class="team"><h4 style="color:${won?'#35d6a2':'#ff6382'}">DRUŻYNA ${i+1} · ${won?'ZWYCIĘSTWO':'PORAŻKA'}</h4>${players.map(p=>{const canOpen=String(p.riot_id||'').includes('#'),premade=premades.get(p.puuid),colorIndex=premade?premade.group:4+match.participants.indexOf(p),iconTitle=premade?`Możliwe premade z: ${premade.withNames.join(', ')} · ${premade.games} wspólne gry`:'Brak wykrytej grupy premade';return `<div class="participant ${canOpen?'clickable':''}" ${canOpen?`data-player-riot-id="${esc(p.riot_id)}" role="button" tabindex="0" title="Otwórz profil ${esc(p.riot_id)}"`:''}><img class="player-color-icon player-color-${colorIndex}" src="${asset('champion',p.champion)}" title="${esc(iconTitle)}"><div><strong>${esc(p.riot_id)}</strong>${canOpen?'<span class="open-profile-hint">Zobacz profil →</span>':''}<small>${esc(p.champion)} · ${p.kills}/${p.deaths}/${p.assists} · ${p.cs} CS · ${number(p.damage)} DMG</small><span class="participant-rank" data-rank-puuid="${esc(p.puuid||'')}">${p.puuid?'Pobieranie aktualnej rangi…':'Ranga niedostępna'}</span></div><div class="items">${p.items.map(id=>`<img src="${asset('item',id)}" data-item-id="${id}">`).join('')}</div></div>`}).join('')}</section>`}).join('')}</div>`;
  $('modal').classList.remove('hidden');
  const puuids=match.participants.map(p=>p.puuid).filter(Boolean);
  if(!puuids.length)return;
  const result=await window.pywebview.api.participant_ranks(puuids);
  if(!result.ok){document.querySelectorAll('.participant-rank').forEach(node=>node.textContent='Nie udało się pobrać rangi');if(result.api_key_invalid)requestNewApiKey(result.error);return;}
  document.querySelectorAll('[data-rank-puuid]').forEach(node=>{node.textContent=formatRanks(result.ranks[node.dataset.rankPuuid]||[])});
}

function detectPremades(match){
  const result=new Map(),parent=new Map(),edgeCounts=new Map();
  const find=id=>{if(parent.get(id)!==id)parent.set(id,find(parent.get(id)));return parent.get(id)};
  const join=(a,b)=>{const ra=find(a),rb=find(b);if(ra!==rb)parent.set(rb,ra)};
  match.participants.filter(p=>p.puuid).forEach(p=>parent.set(p.puuid,p.puuid));
  for(const teamId of new Set(match.participants.map(p=>p.team_id))){
    const players=match.participants.filter(p=>p.team_id===teamId&&p.puuid);
    for(let a=0;a<players.length;a++)for(let b=a+1;b<players.length;b++){
      const first=players[a],second=players[b];
      const games=state.matches.filter(history=>{
        const one=history.participants?.find(p=>p.puuid===first.puuid);
        const two=history.participants?.find(p=>p.puuid===second.puuid);
        return one&&two&&one.team_id===two.team_id;
      }).length;
      if(games>=2){edgeCounts.set(`${first.puuid}|${second.puuid}`,games);join(first.puuid,second.puuid)}
    }
  }
  const roots=[...new Set([...parent].filter(([id])=>[...edgeCounts.keys()].some(key=>key.includes(id))).map(([id])=>find(id)))];
  roots.forEach((root,index)=>{
    const members=match.participants.filter(p=>p.puuid&&find(p.puuid)===root);
    if(members.length<2)return;
    for(const player of members){
      const partners=members.filter(other=>other.puuid!==player.puuid);
      const games=Math.max(...partners.map(other=>edgeCounts.get(`${player.puuid}|${other.puuid}`)||edgeCounts.get(`${other.puuid}|${player.puuid}`)||0));
      result.set(player.puuid,{group:index%4,games,withNames:partners.map(p=>p.riot_id)});
    }
  });
  return result;
}

function openParticipantProfile(riotId){
  riotId=String(riotId||'').trim();
  if(!riotId.includes('#'))return;
  $('modal').classList.add('hidden');
  $('riotId').value=riotId;
  $('region').value=state.region||state.settings.region;
  window.scrollTo({top:0,behavior:'smooth'});
  search();
}

function formatRanks(ranks){
  const format=rank=>`${title(rank.tier)} ${rank.rank} · ${rank.leaguePoints} LP`;
  const solo=ranks.find(rank=>rank.queueType==='RANKED_SOLO_5x5');
  const flex=ranks.find(rank=>rank.queueType==='RANKED_FLEX_SR');
  if(!solo&&!flex)return 'Aktualna ranga: Unranked';
  return [solo&&`Solo: ${format(solo)}`,flex&&`Flex: ${format(flex)}`].filter(Boolean).join(' · ');
}

function playerSummary(player){
  const games=player.matches||[],wins=games.filter(m=>m.result==='Wygrana').length;
  const avg=fn=>games.length?games.reduce((s,m)=>s+fn(m),0)/games.length:0;
  const solo=player.ranks.find(r=>r.queueType==='RANKED_SOLO_5x5');
  const champions={};games.forEach(m=>champions[m.champion]=(champions[m.champion]||0)+1);
  return {games,wins,wr:games.length?Math.round(wins/games.length*100):0,kda:avg(kda).toFixed(2),cs:avg(m=>m.duration_seconds?m.cs/(m.duration_seconds/60):0).toFixed(1),damage:Math.round(avg(m=>m.damage||0)),rank:solo?`${title(solo.tier)} ${solo.rank} · ${solo.leaguePoints} LP`:'Unranked',champions:Object.entries(champions).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([name])=>name)};
}

function compareCard(player){
  const s=playerSummary(player);
  return `<article class="compare-player"><div class="eyebrow">GRACZ</div><h2>${esc(player.riot_id)}</h2><div class="compare-metric"><span>Solo/Duo</span><strong>${esc(s.rank)}</strong></div><div class="compare-metric"><span>Win rate (${s.games} gier)</span><strong>${s.wr}%</strong></div><div class="compare-metric"><span>Średnie KDA</span><strong>${s.kda}</strong></div><div class="compare-metric"><span>CS / min</span><strong>${s.cs}</strong></div><div class="compare-metric"><span>Średnie obrażenia</span><strong>${number(s.damage)}</strong></div><div class="compare-champs">${s.champions.map(name=>`<img src="${asset('champion',name)}" title="${esc(name)}">`).join('')}</div></article>`;
}

async function comparePlayers(){
  if(!state.player){$('compareContent').textContent='Najpierw wyszukaj główny profil gracza.';return;}
  const riotId=$('compareRiotId').value.trim();if(!riotId)return;
  const button=$('compareBtn');button.disabled=true;button.textContent='Pobieranie…';
  try{const result=await window.pywebview.api.compare_player(riotId,state.region,$('apiKey').value,20);if(!result.ok){if(result.api_key_invalid)requestNewApiKey(result.error);else showError(result.error);return}$('compareContent').className='compare-grid';$('compareContent').innerHTML=`${compareCard(state.player)}<div class="compare-vs">VS</div>${compareCard(result.player)}`;}
  catch(error){showError(`Nie udało się porównać graczy: ${error}`)}finally{button.disabled=false;button.textContent='Porównaj'}
}

function applySettings(){
  const s=state.settings;
  document.body.classList.toggle('light-theme',s.theme==='light');
  document.body.classList.toggle('accent-blue',s.accent==='blue');
  document.body.classList.toggle('accent-green',s.accent==='green');
  document.body.classList.toggle('compact-history',Boolean(s.compact));
  $('settingTheme').value=s.theme;$('settingAccent').value=s.accent;$('settingRegion').value=s.region;$('settingMatches').value=s.matches;$('settingLiveRefresh').value=s.liveRefresh;$('settingCompact').checked=Boolean(s.compact);
  if([...$('region').options].some(o=>o.value===s.region))$('region').value=s.region;
  $('matchCount').value=s.matches;
}

function saveSettings(){
  state.settings={theme:$('settingTheme').value,accent:$('settingAccent').value,region:$('settingRegion').value,matches:$('settingMatches').value,liveRefresh:$('settingLiveRefresh').value,compact:$('settingCompact').checked};
  localStorage.setItem('lpvSettings',JSON.stringify(state.settings));applySettings();
  const button=$('saveSettingsBtn');button.textContent='Zapisano ✓';setTimeout(()=>button.textContent='Zapisz ustawienia',1400);
}

async function toggleFavorite(){
  if(!state.player)return;const result=await window.pywebview.api.toggle_favorite(state.player.riot_id,state.region);
  if(!result.ok){showError(result.error);return}state.favorites=result.favorites;renderFavorites();updateFavoriteButton();
}
function renderFavorites(){$('favoritesSelect').innerHTML='<option value="">'+(state.favorites.length?'Wybierz gracza…':'Brak zapisanych graczy')+'</option>'+state.favorites.map((f,i)=>`<option value="${i}">${esc(f.riot_id)} · ${esc(f.region)}</option>`).join('')}
function updateFavoriteButton(){const saved=state.favorites.some(f=>f.riot_id.toLowerCase()===state.player.riot_id.toLowerCase()&&f.region===state.region);$('favoriteBtn').textContent=saved?'★ Usuń':'☆ Dodaj'}
function showTab(id){
  if(!state.player&&!['settings','compare'].includes(id))return;
  if(['settings','compare'].includes(id)){$('emptyState').classList.add('hidden');$('dashboard').classList.remove('hidden')}
  document.querySelector('.profile-strip').classList.toggle('hidden',!state.player);
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.tab===id));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===id));if(id==='ranked')setTimeout(renderChart,50);if(id==='live'&&state.player){refreshLiveGame().then(refreshLiveInsights);refreshLocalLiveStats()}
}
function showError(message){$('errorBox').textContent=message;$('errorBox').classList.remove('hidden')}
function requestNewApiKey(message){$('apiKey').value='';$('apiKey').type='password';$('toggleApiKey').textContent='Pokaż';$('apiKeyStatus').textContent='Domyślne API lub zapisany klucz nie działa. Możesz wkleić własny klucz.';showTab('settings');showError(`${message} Wklej własny klucz w Ustawieniach.`);setTimeout(()=>$('apiKey').focus(),80)}
function hideError(){$('errorBox').classList.add('hidden')}
function kda(match){return (match.kills+match.assists)/Math.max(1,match.deaths)}
function title(value){const s=String(value||'').toLowerCase();return s.charAt(0).toUpperCase()+s.slice(1)}
window.addEventListener('resize',()=>{if(state.player&&$('ranked').classList.contains('active'))renderChart()});
setInterval(()=>{const clock=$('liveClock');if(clock)clock.textContent=formatClock(liveDuration())},1000);
setInterval(async()=>{if(state.player&&$('live').classList.contains('active')){await refreshLiveGame();await refreshLiveInsights()}},60000);
async function pollLocalLive(){if(state.player&&$('live').classList.contains('active'))await refreshLocalLiveStats();setTimeout(pollLocalLive,Math.max(3,Number(state.settings.liveRefresh)||5)*1000)}
pollLocalLive();
