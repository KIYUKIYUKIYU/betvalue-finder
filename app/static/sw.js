// BetValue Finder Desktop PWA Service Worker
// 高性能キャッシュ + オフライン対応

const CACHE_NAME = 'betvalue-desktop-v1.0.1';
const API_CACHE_NAME = 'betvalue-api-v1.0.1';

// キャッシュするファイル（アプリシェル）
const STATIC_CACHE_FILES = [
  '/',
  '/static/index.html',
  '/static/style.css',
  '/static/app.js',
  '/static/manifest.json'
];

// キャッシュするAPI（分析結果）
const API_CACHE_PATTERNS = [
  /\/analyze_paste/,
  /\/evaluate_odds/,
  /\/api_status/,
  /\/health/
];

// TTL設定（ミリ秒）
const CACHE_TTL = {
  static: 24 * 60 * 60 * 1000,      // 静的ファイル: 24時間
  api: 5 * 60 * 1000,               // API結果: 5分
  analysis: 30 * 60 * 1000          // 分析結果: 30分
};

// Service Worker インストール
self.addEventListener('install', (event) => {
  console.log('🚀 BetValue Desktop Service Worker installing...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('📦 Caching app shell');
        return cache.addAll(STATIC_CACHE_FILES);
      })
      .then(() => {
        console.log('✅ App shell cached successfully');
        return self.skipWaiting(); // 即座にアクティベート
      })
  );
});

// Service Worker アクティベート
self.addEventListener('activate', (event) => {
  console.log('⚡ BetValue Desktop Service Worker activating...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // 古いキャッシュを削除
            if (cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME) {
              console.log('🗑️ Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker activated');
        return self.clients.claim(); // 即座に制御開始
      })
  );
});

// ネットワークリクエスト処理
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // APIリクエストの場合
  if (isApiRequest(url)) {
    event.respondWith(handleApiRequest(request));
  }
  // 静的ファイルの場合
  else if (isStaticFile(url)) {
    event.respondWith(handleStaticRequest(request));
  }
  // その他（通常通り）
  else {
    event.respondWith(fetch(request));
  }
});

// APIリクエスト判定
function isApiRequest(url) {
  return API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname)) ||
         url.pathname.startsWith('/api/');
}

// 静的ファイル判定
function isStaticFile(url) {
  return url.pathname.startsWith('/static/') ||
         url.pathname === '/' ||
         url.pathname.endsWith('.html') ||
         url.pathname.endsWith('.css') ||
         url.pathname.endsWith('.js');
}

// APIリクエスト処理（Cache First + Network Fallback）
async function handleApiRequest(request) {
  const cache = await caches.open(API_CACHE_NAME);
  const cacheKey = getCacheKey(request);

  try {
    // キャッシュチェック
    const cachedResponse = await cache.match(cacheKey);
    if (cachedResponse && !isExpired(cachedResponse)) {
      console.log('🎯 API Cache hit:', request.url);
      return cachedResponse;
    }

    // ネットワークから取得
    console.log('🌐 API Network fetch:', request.url);
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      // APIレスポンスをキャッシュ
      const responseToCache = networkResponse.clone();
      const headers = new Headers(responseToCache.headers);
      headers.set('sw-cached-at', Date.now().toString());

      const cachedResponse = new Response(responseToCache.body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers
      });

      cache.put(cacheKey, cachedResponse);
      console.log('📦 API response cached:', request.url);
    }

    return networkResponse;

  } catch (error) {
    console.log('❌ API Network failed, trying cache:', error);

    // ネットワークエラー時はキャッシュから（期限切れでも）
    const cachedResponse = await cache.match(cacheKey);
    if (cachedResponse) {
      console.log('🔄 Using expired cache for:', request.url);
      return cachedResponse;
    }

    // オフライン用のフォールバックレスポンス
    return new Response(JSON.stringify({
      error: 'オフラインです。ネットワーク接続を確認してください。',
      offline: true,
      cached_at: null
    }), {
      headers: { 'Content-Type': 'application/json' },
      status: 503
    });
  }
}

// 静的ファイル処理（Cache First）
async function handleStaticRequest(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    // キャッシュから取得
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('📄 Static cache hit:', request.url);

      // バックグラウンドで更新チェック
      updateStaticCache(request, cache);

      return cachedResponse;
    }

    // ネットワークから取得してキャッシュ
    console.log('🌐 Static network fetch:', request.url);
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
      console.log('📦 Static file cached:', request.url);
    }

    return networkResponse;

  } catch (error) {
    console.log('❌ Static file fetch failed:', error);

    // オフライン時のフォールバック
    if (request.url.endsWith('/') || request.url.includes('index.html')) {
      const fallbackResponse = await cache.match('/static/index.html');
      if (fallbackResponse) {
        return fallbackResponse;
      }
    }

    throw error;
  }
}

// キャッシュキー生成
function getCacheKey(request) {
  const url = new URL(request.url);

  // POSTリクエストの場合、ボディも含める
  if (request.method === 'POST') {
    return `${url.pathname}#${request.method}`;
  }

  return request.url;
}

// キャッシュ期限チェック
function isExpired(response) {
  const cachedAt = response.headers.get('sw-cached-at');
  if (!cachedAt) return true;

  const age = Date.now() - parseInt(cachedAt);
  return age > CACHE_TTL.api;
}

// 静的ファイルのバックグラウンド更新
async function updateStaticCache(request, cache) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
      console.log('🔄 Static file updated in background:', request.url);
    }
  } catch (error) {
    // バックグラウンド更新の失敗は無視
    console.log('⚠️ Background update failed:', request.url);
  }
}

// PWAインストールプロンプト対応
self.addEventListener('beforeinstallprompt', (event) => {
  console.log('💾 PWA install prompt available');
  event.preventDefault();
  // メインスレッドにイベントを送信
  self.clients.matchAll().then(clients => {
    clients.forEach(client => {
      client.postMessage({
        type: 'INSTALL_PROMPT_AVAILABLE'
      });
    });
  });
});

// メッセージハンドリング
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CACHE_STATS') {
    getCacheStats().then(stats => {
      event.ports[0].postMessage(stats);
    });
  }
});

// キャッシュ統計取得
async function getCacheStats() {
  const cacheNames = await caches.keys();
  const stats = {
    caches: cacheNames.length,
    totalSize: 0,
    entries: {}
  };

  for (const cacheName of cacheNames) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    stats.entries[cacheName] = keys.length;
  }

  return stats;
}

console.log('🚀 BetValue Desktop Service Worker loaded');