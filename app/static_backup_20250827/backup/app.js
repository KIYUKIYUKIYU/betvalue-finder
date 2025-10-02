// app/static/app.js
// フロントエンドロジック - 改善版（エラー耐性強化）

// DOMが完全に読み込まれてから実行
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM読み込み完了');
    
    // DOM要素の取得（nullチェック付き）
    const elements = {
        themeToggle: document.getElementById('theme-toggle'),
        sportSelect: document.getElementById('sport-select'),
        rakebackSelect: document.getElementById('rakeback-select'),
        dateInput: document.getElementById('date-input'),
        pasteInput: document.getElementById('paste-input'),
        clearBtn: document.getElementById('clear-btn'),
        analyzeBtn: document.getElementById('analyze-btn'),
        resultsSection: document.getElementById('results-section'),
        resultsContainer: document.getElementById('results-container'),
        errorToast: document.getElementById('error-toast'),
        loadingOverlay: document.getElementById('loading-overlay'),
        // 履歴関連
        historyBtn: document.getElementById('history-btn'),
        historyModal: document.getElementById('history-modal'),
        historyList: document.getElementById('history-list'),
        closeHistory: document.getElementById('close-history'),
        clearHistory: document.getElementById('clear-history')
    };

    // 必須要素のチェック
    if (!elements.analyzeBtn || !elements.pasteInput) {
        console.error('必須要素が見つかりません');
        alert('ページの読み込みに失敗しました。リロードしてください。');
        return;
    }

    // 履歴管理クラス
    class HistoryManager {
        constructor() {
            this.maxItems = 50;
            this.storageKey = 'betvalue_history';
        }
        
        load() {
            try {
                const data = localStorage.getItem(this.storageKey);
                return data ? JSON.parse(data) : [];
            } catch (e) {
                console.error('履歴の読み込みエラー:', e);
                return [];
            }
        }
        
        save(history) {
            try {
                localStorage.setItem(this.storageKey, JSON.stringify(history));
            } catch (e) {
                console.error('履歴の保存エラー:', e);
            }
        }
        
        add(item) {
            const history = this.load();
            // 新しいアイテムを先頭に追加
            history.unshift({
                ...item,
                timestamp: new Date().toISOString()
            });
            // 最大件数を超えたら古いものを削除
            if (history.length > this.maxItems) {
                history.splice(this.maxItems);
            }
            this.save(history);
        }
        
        clear() {
            localStorage.removeItem(this.storageKey);
        }
        
        getRecent(count = 10) {
            const history = this.load();
            return history.slice(0, count);
        }
    }
    
    const historyManager = new HistoryManager();
let currentTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', currentTheme);

// 今日の日付を設定（安全な方法）
try {
    const dateInput = document.getElementById('date-input');
    if (dateInput) {
        const today = new Date();
        const dateStr = today.toISOString().split('T')[0];
        dateInput.value = dateStr;
    }
} catch (e) {
    console.log('Date input not found');
}

// 保存された設定の復元
const savedSport = localStorage.getItem('sport') || 'mlb';
const savedRakeback = localStorage.getItem('rakeback') || '0';
elements.sportSelect.value = savedSport;
elements.rakebackSelect.value = savedRakeback;

// テーマ切替（存在する場合のみ）
if (elements.themeToggle) {
    elements.themeToggle.addEventListener('click', () => {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
    });
}

// 設定の保存（存在する場合のみ）
if (elements.sportSelect) {
    elements.sportSelect.addEventListener('change', (e) => {
        localStorage.setItem('sport', e.target.value);
    });
}

if (elements.rakebackSelect) {
    elements.rakebackSelect.addEventListener('change', (e) => {
        localStorage.setItem('rakeback', e.target.value);
    });
}

// クリアボタン（存在する場合のみ）
if (elements.clearBtn) {
    elements.clearBtn.addEventListener('click', () => {
        if (elements.pasteInput) elements.pasteInput.value = '';
        if (elements.resultsSection) elements.resultsSection.classList.remove('show');
        if (elements.resultsContainer) elements.resultsContainer.innerHTML = '';
    });
}

// ローディング表示制御（安全版）
function showLoading(text = 'オッズデータ取得中...') {
    if (elements.loadingOverlay) {
        const loadingText = elements.loadingOverlay.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = text;
        }
        elements.loadingOverlay.classList.add('show');
    }
    // loadingOverlayがなくてもエラーにしない
}

function hideLoading() {
    if (elements.loadingOverlay && elements.loadingOverlay.classList) {
        elements.loadingOverlay.classList.remove('show');
    }
    // loadingOverlayがなくてもエラーにしない
}

// 判定ボタン（必ず動くように修正）
if (elements.analyzeBtn) {
    elements.analyzeBtn.addEventListener('click', async () => {
        console.log('判定ボタンがクリックされました');  // デバッグ用
        
        const text = elements.pasteInput ? elements.pasteInput.value.trim() : '';
        // 日付は手動指定時のみ送信、自動判定時はnull
        const selectedDate = (elements.dateInput && elements.dateInput.value && !elements.dateInput.disabled) 
            ? elements.dateInput.value 
            : null;
        
        if (!text) {
            showError('ハンデを入力してください');
            return;
        }
        
        // ローディング状態（存在する場合のみ）
        if (elements.analyzeBtn.classList) {
            elements.analyzeBtn.classList.add('loading');
        }
        const loadingMessage = selectedDate 
            ? `${selectedDate}のオッズデータを取得中...`
            : `オッズデータを自動検索中...`;
        showLoading(loadingMessage);
        
        try {
            const response = await fetch('/analyze_paste', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    sport: elements.sportSelect ? elements.sportSelect.value : 'mlb',
                    rakeback: elements.rakebackSelect ? parseFloat(elements.rakebackSelect.value) : 0,
                    jp_odds: 1.9,
                    date: selectedDate
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                const errorCode = response.headers.get('X-Error-Code');
                throw { message: error.detail || 'エラーが発生しました', code: errorCode };
            }
            
            const results = await response.json();
            displayResults(results, selectedDate);
            
        } catch (error) {
            console.error('Error:', error);
            const errorMessage = error.message || error.toString() || '通信エラーが発生しました';
            const errorCode = error.code || null;
            showError(errorMessage, errorCode);
        } finally {
            if (elements.analyzeBtn.classList) {
                elements.analyzeBtn.classList.remove('loading');
            }
            hideLoading();
        }
    });
} else {
    console.error('判定ボタンが見つかりません');
}

// 結果表示（両側判定対応・安全版）
function displayResults(results, date) {
    if (!elements.resultsContainer) {
        console.error('結果コンテナが見つかりません');
        return;
    }
    
    elements.resultsContainer.innerHTML = '';
    
    if (!results || results.length === 0) {
        elements.resultsContainer.innerHTML = '<p class="card-error">結果がありません</p>';
        if (elements.resultsSection) {
            elements.resultsSection.classList.add('show');
        }
        return;
    }
    
    // 日付表示
    const dateHeader = document.createElement('div');
    dateHeader.className = 'date-header';
    dateHeader.style.textAlign = 'center';
    dateHeader.style.marginBottom = '16px';
    dateHeader.style.color = 'var(--text-secondary)';
    dateHeader.innerHTML = date ? `${date} の試合結果` : `試合結果（自動判定）`;
    elements.resultsContainer.appendChild(dateHeader);
    
    // 試合ごとにグループ化（両側判定のため）
    const gameGroups = groupByGame(results);
    
    gameGroups.forEach(game => {
        const card = createBothSidesCard(game);
        elements.resultsContainer.appendChild(card);
    });
    
    if (elements.resultsSection) {
        elements.resultsSection.classList.add('show');
    }
    
    // スクロール（エラーが起きても続行）
    setTimeout(() => {
        try {
            if (elements.resultsSection) {
                elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } catch (e) {
            console.log('スクロールエラー:', e);
        }
    }, 100);
}

// 試合ごとにグループ化
function groupByGame(results) {
    const games = new Map();
    
    results.forEach(result => {
        const gameKey = `${result.team_a}_vs_${result.team_b}`;
        
        if (!games.has(gameKey)) {
            games.set(gameKey, {
                team_a: result.team_a,
                team_b: result.team_b,
                team_a_jp: result.team_a_jp,
                team_b_jp: result.team_b_jp,
                sides: []
            });
        }
        
        games.get(gameKey).sides.push(result);
    });
    
    return Array.from(games.values());
}

// 両側判定カード作成
function createBothSidesCard(game) {
    const card = document.createElement('div');
    card.className = 'result-card both-sides';
    
    // 試合タイトル
    const title = document.createElement('div');
    title.className = 'game-title';
    title.textContent = `${game.team_a_jp} vs ${game.team_b_jp}`;
    card.appendChild(title);
    
    // 両側の結果コンテナ
    const sidesContainer = document.createElement('div');
    sidesContainer.className = 'sides-container';
    
    // 各サイドの結果を表示
    game.sides.forEach(side => {
        if (side.error) {
            // エラーの場合
            const errorDiv = document.createElement('div');
            errorDiv.className = 'card-error';
            errorDiv.textContent = side.error;
            sidesContainer.appendChild(errorDiv);
        } else if (side.fav_team_jp && side.verdict) {
            // 正常な結果
            const sideResult = createSideResult(side);
            sidesContainer.appendChild(sideResult);
        }
    });
    
    // 両側の判定がある場合、どちらが有利か表示
    if (game.sides.length === 2 && !game.sides[0].error && !game.sides[1].error) {
        const comparison = createComparison(game.sides);
        sidesContainer.appendChild(comparison);
    }
    
    card.appendChild(sidesContainer);
    return card;
}

// 片側の結果表示
function createSideResult(result) {
    const container = document.createElement('div');
    container.className = `side-result ${result.verdict || 'minus'}`;
    
    // ヘッダー
    const header = document.createElement('div');
    header.className = 'side-header';
    
    const teamInfo = document.createElement('div');
    const sideLabel = document.createElement('div');
    sideLabel.className = 'side-label';
    sideLabel.textContent = result.fav_team === result.team_a ? '出し側' : '貰い側';
    
    const teamName = document.createElement('div');
    teamName.className = 'side-team';
    teamName.textContent = `${result.fav_team_jp}（${result.jp_line || '-'}）`;
    
    teamInfo.appendChild(sideLabel);
    teamInfo.appendChild(teamName);
    
    const verdictBadge = document.createElement('span');
    verdictBadge.className = `verdict-badge ${result.verdict}`;
    verdictBadge.textContent = formatVerdict(result.verdict);
    
    header.appendChild(teamInfo);
    header.appendChild(verdictBadge);
    container.appendChild(header);
    
    // 統計情報
    const stats = document.createElement('div');
    stats.className = 'card-stats';
    
    // EV%
    const evStat = createStat('EV（レーキ後）', formatEV(result.ev_pct_rake), result.ev_pct_rake >= 0);
    stats.appendChild(evStat);
    
    // 公正勝率
    const probStat = createStat('公正勝率', formatProb(result.fair_prob));
    stats.appendChild(probStat);
    
    // 公正オッズ
    const oddsStat = createStat('公正オッズ', formatOdds(result.fair_odds));
    stats.appendChild(oddsStat);
    
    // ピナクル値
    const pinStat = createStat('ピナクル値', formatPinnacle(result.pinnacle_line));
    stats.appendChild(pinStat);
    
    container.appendChild(stats);
    return container;
}

// 統計項目作成
function createStat(label, value, isPositive = null) {
    const stat = document.createElement('div');
    stat.className = 'stat-item';
    
    const statLabel = document.createElement('span');
    statLabel.className = 'stat-label';
    statLabel.textContent = label;
    
    const statValue = document.createElement('span');
    statValue.className = 'stat-value';
    if (isPositive !== null) {
        statValue.className += isPositive ? ' positive' : ' negative';
    }
    statValue.textContent = value;
    
    stat.appendChild(statLabel);
    stat.appendChild(statValue);
    return stat;
}

// 両側比較
function createComparison(sides) {
    const comparison = document.createElement('div');
    comparison.style.marginTop = '16px';
    comparison.style.padding = '12px';
    comparison.style.backgroundColor = 'var(--bg-secondary)';
    comparison.style.borderRadius = '8px';
    comparison.style.textAlign = 'center';
    
    const side1EV = sides[0].ev_pct_rake || -100;
    const side2EV = sides[1].ev_pct_rake || -100;
    
    let message = '';
    if (side1EV > side2EV && side1EV > 0) {
        message = `⭐ ${sides[0].fav_team_jp}側が有利`;
    } else if (side2EV > side1EV && side2EV > 0) {
        message = `⭐ ${sides[1].fav_team_jp}側が有利`;
    } else if (side1EV > 0 && side2EV > 0) {
        message = '✅ 両側とも期待値プラス';
    } else {
        message = '⚠️ 両側とも期待値マイナス';
    }
    
    comparison.textContent = message;
    return comparison;
}

// フォーマット関数
function formatEV(value) {
    if (value == null) return '-';
    return value >= 0 ? `+${value.toFixed(1)}%` : `${value.toFixed(1)}%`;
}

function formatProb(value) {
    if (value == null) return '-';
    return `${(value * 100).toFixed(1)}%`;
}

function formatOdds(value) {
    if (value == null) return '-';
    return value.toFixed(3);
}

function formatPinnacle(value) {
    if (value == null) return '-';
    return value.toFixed(2);
}

function formatVerdict(verdict) {
    const verdictMap = {
        'clear_plus': 'BEST',
        'plus': 'GOOD',
        'fair': 'FAIR',
        'minus': 'PASS'
    };
    return verdictMap[verdict] || verdict;
}

// エラー表示（安全版）
function showError(message) {
    // まずalertで確実に表示
    alert(message);
    
    // エラートーストがあれば表示
    if (elements.errorToast) {
        elements.errorToast.textContent = message;
        elements.errorToast.classList.add('show');
        
        setTimeout(() => {
            if (elements.errorToast) {
                elements.errorToast.classList.remove('show');
            }
        }, 3000);
    }
}

// サンプルデータ入力（デバッグ用）
if (window.location.hash === '#debug') {
    if (elements.pasteInput) {
        elements.pasteInput.value = `ヤンキース<0.1>
レッドソックス

タイガース
アストロズ<1.2>

パドレス<1半>
フィリーズ`;
    }
}

    // 履歴表示機能
    if (elements.historyBtn) {
        elements.historyBtn.addEventListener('click', () => {
            showHistory();
        });
    }
    
    if (elements.closeHistory) {
        elements.closeHistory.addEventListener('click', () => {
            if (elements.historyModal) {
                elements.historyModal.classList.remove('show');
            }
        });
    }
    
    if (elements.clearHistory) {
        elements.clearHistory.addEventListener('click', () => {
            if (confirm('履歴をすべて削除しますか？')) {
                historyManager.clear();
                showHistory(); // リフレッシュ
            }
        });
    }
    
    function showHistory() {
        if (!elements.historyModal || !elements.historyList) return;
        
        const history = historyManager.getRecent(20);
        
        if (history.length === 0) {
            elements.historyList.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">履歴がありません</p>';
        } else {
            elements.historyList.innerHTML = history.map(item => {
                const date = new Date(item.timestamp);
                const timeStr = date.toLocaleString('ja-JP', {
                    month: 'numeric',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                // 主要な結果を抽出
                const mainResults = item.results.filter(r => r.verdict).slice(0, 2);
                const resultHtml = mainResults.map(r => `
                    <span class="history-verdict ${r.verdict}">
                        ${r.fav_team_jp || r.team_a_jp} ${r.jp_line || ''}: ${r.ev_pct_rake}%
                    </span>
                `).join('');
                
                return `
                    <div class="history-item" data-input="${encodeURIComponent(item.input)}">
                        <div class="history-time">${timeStr}</div>
                        <div class="history-teams">
                            ${item.results[0].team_a_jp} vs ${item.results[0].team_b_jp}
                        </div>
                        <div class="history-result">${resultHtml}</div>
                    </div>
                `;
            }).join('');
            
            // 履歴アイテムクリックで再入力
            setTimeout(() => {
                document.querySelectorAll('.history-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        const input = decodeURIComponent(e.currentTarget.dataset.input);
                        if (elements.pasteInput) {
                            elements.pasteInput.value = input;
                        }
                        if (elements.historyModal) {
                            elements.historyModal.classList.remove('show');
                        }
                    });
                });
            }, 100);
        }
        
        elements.historyModal.classList.add('show');
    }
    
    // モーダル外クリックで閉じる
    if (elements.historyModal) {
        elements.historyModal.addEventListener('click', (e) => {
            if (e.target === elements.historyModal) {
                elements.historyModal.classList.remove('show');
            }
        });
    }
    console.log('BetValue Finder JavaScript loaded successfully');
    console.log('判定ボタン:', elements.analyzeBtn ? 'OK' : 'NOT FOUND');
    console.log('入力エリア:', elements.pasteInput ? 'OK' : 'NOT FOUND');
    
}); // DOMContentLoaded終了