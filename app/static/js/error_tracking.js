// -*- coding: utf-8 -*-
/**
 * BetValue Finder - Frontend Error Tracking System
 * フロントエンドエラー・パフォーマンス追跡システム
 */

class FrontendErrorTracker {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.userId = this.getUserId();
        this.isInitialized = false;
        this.eventQueue = [];
        this.maxQueueSize = 50;
        this.batchInterval = 30000; // 30秒間隔でバッチ送信
        this.maxRetries = 3;

        this.setupErrorHandlers();
        this.setupPerformanceMonitoring();
        this.startBatchProcessor();

        this.isInitialized = true;
        console.log('🔧 BetValue Frontend Error Tracker initialized');
        console.log(`📊 Session ID: ${this.sessionId}`);
    }

    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substr(2, 9);
        return `session_${timestamp}_${random}`;
    }

    getUserId() {
        // LocalStorage または Cookie から取得
        let userId = localStorage.getItem('betvalue_user_id');
        if (!userId) {
            userId = `anon_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
            localStorage.setItem('betvalue_user_id', userId);
        }
        return userId;
    }

    setupErrorHandlers() {
        // JavaScript エラーハンドラー
        window.addEventListener('error', (event) => {
            this.logError({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent
            });
        });

        // Promise rejection エラー
        window.addEventListener('unhandledrejection', (event) => {
            this.logError({
                type: 'promise_rejection',
                message: event.reason?.message || String(event.reason),
                stack: event.reason?.stack,
                timestamp: new Date().toISOString(),
                url: window.location.href
            });
        });

        // Network エラー監視
        this.wrapFetch();

        // Console error も追跡
        this.wrapConsoleError();
    }

    wrapFetch() {
        const originalFetch = window.fetch;
        const tracker = this;

        window.fetch = async function(...args) {
            const startTime = Date.now();
            const url = args[0];
            const options = args[1] || {};
            const method = options.method || 'GET';

            try {
                const response = await originalFetch(...args);
                const duration = Date.now() - startTime;

                // API呼び出しログ
                tracker.logApiCall({
                    url: url,
                    method: method,
                    status: response.status,
                    duration: duration,
                    success: response.ok,
                    response_size: response.headers.get('Content-Length')
                });

                if (!response.ok && response.status >= 400) {
                    tracker.logError({
                        type: 'network_error',
                        message: `HTTP ${response.status} ${response.statusText}`,
                        url: url,
                        method: method,
                        status: response.status,
                        duration: duration
                    });
                }

                return response;
            } catch (error) {
                const duration = Date.now() - startTime;

                tracker.logError({
                    type: 'fetch_error',
                    message: error.message,
                    url: url,
                    method: method,
                    duration: duration,
                    stack: error.stack
                });

                throw error;
            }
        };
    }

    wrapConsoleError() {
        const originalError = console.error;
        const tracker = this;

        console.error = function(...args) {
            // 元のconsole.errorを実行
            originalError.apply(console, args);

            // エラートラッキングに記録
            tracker.logError({
                type: 'console_error',
                message: args.join(' '),
                timestamp: new Date().toISOString(),
                arguments: args.map(arg => String(arg))
            });
        };
    }

    setupPerformanceMonitoring() {
        // ページロード時間
        window.addEventListener('load', () => {
            setTimeout(() => {
                try {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    if (navigation) {
                        this.logPerformance({
                            type: 'page_load',
                            load_time: navigation.loadEventEnd - navigation.fetchStart,
                            dom_content_loaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
                            first_paint: this.getFirstPaint(),
                            url: window.location.href,
                            connection_type: this.getConnectionType()
                        });
                    }
                } catch (error) {
                    console.warn('Performance monitoring failed:', error);
                }
            }, 0);
        });

        // ユーザーアクション追跡
        this.setupUserActionTracking();

        // リソースエラー監視
        this.setupResourceErrorTracking();
    }

    setupUserActionTracking() {
        // クリックイベント
        document.addEventListener('click', (event) => {
            const target = event.target;
            this.logUserAction({
                type: 'click',
                element: target.tagName,
                id: target.id || null,
                classes: target.className || null,
                text: target.textContent?.substring(0, 50) || null,
                timestamp: new Date().toISOString(),
                page_url: window.location.href
            });
        }, { passive: true });

        // フォーム送信追跡
        document.addEventListener('submit', (event) => {
            const form = event.target;
            this.logUserAction({
                type: 'form_submit',
                form_id: form.id || null,
                form_action: form.action || null,
                form_method: form.method || 'GET',
                timestamp: new Date().toISOString(),
                page_url: window.location.href
            });
        });

        // ページ遷移追跡
        let lastUrl = window.location.href;
        const observer = new MutationObserver(() => {
            const currentUrl = window.location.href;
            if (currentUrl !== lastUrl) {
                this.logUserAction({
                    type: 'page_navigation',
                    from_url: lastUrl,
                    to_url: currentUrl,
                    timestamp: new Date().toISOString()
                });
                lastUrl = currentUrl;
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    setupResourceErrorTracking() {
        // 画像、CSS、JS などのリソース読み込みエラー
        window.addEventListener('error', (event) => {
            if (event.target !== window && event.target.src) {
                this.logError({
                    type: 'resource_error',
                    resource_url: event.target.src,
                    resource_type: event.target.tagName,
                    message: 'Resource failed to load',
                    timestamp: new Date().toISOString(),
                    page_url: window.location.href
                });
            }
        }, true);
    }

    getFirstPaint() {
        try {
            const paintEntries = performance.getEntriesByType('paint');
            const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
            return firstPaint ? firstPaint.startTime : null;
        } catch (error) {
            return null;
        }
    }

    getConnectionType() {
        try {
            return navigator.connection?.effectiveType || 'unknown';
        } catch (error) {
            return 'unknown';
        }
    }

    // ログ記録メソッド
    async logError(errorData) {
        const logEntry = this.createLogEntry('error', errorData);
        this.queueEvent(logEntry);
    }

    async logApiCall(apiData) {
        const logEntry = this.createLogEntry('api_call', apiData);
        this.queueEvent(logEntry);
    }

    async logPerformance(perfData) {
        const logEntry = this.createLogEntry('performance', perfData);
        this.queueEvent(logEntry);
    }

    async logUserAction(actionData) {
        // ユーザーアクションは頻度が高いので、重要でないものは間引き
        if (actionData.type === 'click' && Math.random() > 0.1) {
            return; // 10%のクリックのみ記録
        }

        const logEntry = this.createLogEntry('user_action', actionData);
        this.queueEvent(logEntry);
    }

    createLogEntry(level, data) {
        return {
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            level: level,
            user_agent: navigator.userAgent,
            page_url: window.location.href,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            ...data
        };
    }

    queueEvent(logEntry) {
        this.eventQueue.push(logEntry);

        // キューサイズ制限
        if (this.eventQueue.length > this.maxQueueSize) {
            this.eventQueue.shift(); // 古いイベントを削除
        }

        // 緊急度の高いエラーは即座に送信
        if (logEntry.type === 'javascript_error' || logEntry.type === 'fetch_error') {
            this.sendLogBatch([logEntry]);
        }
    }

    startBatchProcessor() {
        // 定期的なバッチ送信
        setInterval(() => {
            this.processBatch();
        }, this.batchInterval);

        // ページ離脱時の送信
        window.addEventListener('beforeunload', () => {
            this.processBatch();
        });

        // ページ非表示時の送信
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                this.processBatch();
            }
        });
    }

    processBatch() {
        if (this.eventQueue.length === 0) return;

        const eventsToSend = [...this.eventQueue];
        this.eventQueue = [];

        this.sendLogBatch(eventsToSend);
    }

    async sendLogBatch(events) {
        if (events.length === 0) return;

        try {
            const response = await fetch('/api/v1/log/frontend/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ logs: events })
            });

            if (response.ok) {
                console.debug(`📤 Sent ${events.length} log events to server`);
            } else {
                console.warn('Failed to send logs to server:', response.status);
                this.storeLogsLocally(events);
            }
        } catch (error) {
            console.warn('Failed to send logs to server:', error);
            this.storeLogsLocally(events);
        }
    }

    storeLogsLocally(events) {
        try {
            const key = 'betvalue_pending_logs';
            let pendingLogs = JSON.parse(localStorage.getItem(key) || '[]');

            pendingLogs = pendingLogs.concat(events);

            // 最大1000件まで保持
            if (pendingLogs.length > 1000) {
                pendingLogs = pendingLogs.slice(-1000);
            }

            localStorage.setItem(key, JSON.stringify(pendingLogs));
        } catch (error) {
            console.warn('Failed to store logs locally:', error);
        }
    }

    async flushLocalLogs() {
        try {
            const key = 'betvalue_pending_logs';
            const pendingLogs = JSON.parse(localStorage.getItem(key) || '[]');

            if (pendingLogs.length > 0) {
                await this.sendLogBatch(pendingLogs);
                localStorage.removeItem(key);
            }
        } catch (error) {
            console.warn('Failed to flush local logs:', error);
        }
    }

    // パブリックメソッド
    logCustomError(message, context = {}) {
        this.logError({
            type: 'custom_error',
            message: message,
            context: context,
            timestamp: new Date().toISOString()
        });
    }

    logCustomEvent(eventType, data = {}) {
        const logEntry = this.createLogEntry('custom_event', {
            type: eventType,
            data: data
        });
        this.queueEvent(logEntry);
    }

    // システム情報取得
    getSystemInfo() {
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            connection: navigator.connection ? {
                effectiveType: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt
            } : null
        };
    }
}

// グローバル初期化
let errorTracker;

// DOM準備完了後に初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        errorTracker = new FrontendErrorTracker();
    });
} else {
    errorTracker = new FrontendErrorTracker();
}

// グローバルアクセス用
window.BetValueErrorTracker = {
    getInstance: () => errorTracker,
    logError: (message, context) => errorTracker?.logCustomError(message, context),
    logEvent: (eventType, data) => errorTracker?.logCustomEvent(eventType, data)
};

// 5分間隔でローカルログをフラッシュ
setInterval(() => {
    if (errorTracker) {
        errorTracker.flushLocalLogs();
    }
}, 5 * 60 * 1000);

console.log('🚀 BetValue Frontend Error Tracking loaded and ready');