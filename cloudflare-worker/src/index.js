const RIOT_HOSTS = new Set([
  'br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1',
  'ph2', 'ru', 'sg2', 'th2', 'tr1', 'tw2', 'vn2',
  'americas', 'asia', 'europe', 'sea'
]);

const ALLOWED_PATHS = [
  /^\/riot\/account\/v1\/accounts\/by-riot-id\/[^/]+\/[^/?]+$/,
  /^\/lol\/summoner\/v4\/summoners\/by-puuid\/[^/?]+$/,
  /^\/lol\/league\/v4\/entries\/by-puuid\/[^/?]+$/,
  /^\/lol\/spectator\/v5\/active-games\/by-summoner\/[^/?]+$/,
  /^\/lol\/match\/v5\/matches\/by-puuid\/[^/]+\/ids\?start=\d+&count=\d+$/,
  /^\/lol\/match\/v5\/matches\/[^/?]+$/,
  /^\/lol\/champion-mastery\/v4\/champion-masteries\/by-puuid\/[^/]+\/by-champion\/\d+$/
];

function json(body, status = 400) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.pathname !== '/v1/riot') {
      return json({ error: 'Not found' }, 404);
    }
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const { success } = await env.RATE_LIMITER.limit({ key: ip });
    if (!success) return json({ error: 'Too many requests' }, 429);

    const host = (url.searchParams.get('host') || '').toLowerCase();
    const path = url.searchParams.get('path') || '';
    if (!RIOT_HOSTS.has(host) || !ALLOWED_PATHS.some(pattern => pattern.test(path))) {
      return json({ error: 'Endpoint not allowed' }, 403);
    }
    if (!env.RIOT_API_KEY) return json({ error: 'Proxy is not configured' }, 503);

    const riotResponse = await fetch(`https://${host}.api.riotgames.com${path}`, {
      headers: {
        'X-Riot-Token': env.RIOT_API_KEY,
        'User-Agent': 'LoL-Player-Viewer-Proxy/1.0'
      }
    });
    const headers = new Headers({
      'content-type': riotResponse.headers.get('content-type') || 'application/json',
      'cache-control': 'no-store'
    });
    for (const name of ['retry-after', 'x-app-rate-limit', 'x-app-rate-limit-count']) {
      const value = riotResponse.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(riotResponse.body, { status: riotResponse.status, headers });
  }
};
