// app/static/app.js
// BetValue Finder フロントエンドロジック

document.addEventListener('DOMContentLoaded', function() {
    console.log('BetValue Finder initialized');
    
    // DOM要素の取得
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
        loadingOverlay: document.getElementById('loading-overlay')
    };

    // 必須要素のチェック
    if (!elements.analyzeBtn || !elements.pasteInput) {
        console.error('Required elements not found');
        alert('Page loading failed. Please reload.');
        return;
    }

    // テーマ切替
    let currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);

    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', () => {
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', currentTheme);
            localStorage.setItem('theme', currentTheme);
            elements.themeToggle.textContent = currentTheme === 'light' ? '🌙' : '☀️';
        });
    }

    // 設定の保存
    if (elements.sportSelect) {
        const savedSport = localStorage.getItem('sport') || 'mlb';
        elements.sportSelect.value = savedSport;
        elements.sportSelect.addEventListener('change', (e) => {
            localStorage.setItem('sport', e.target.value);
        });
    }

    if (elements.rakebackSelect) {
        const savedRakeback = localStorage.getItem('rakeback') || '0.015';
        elements.rakebackSelect.value = savedRakeback;
        elements.rakebackSelect.addEventListener('change', (e) => {
            localStorage.setItem('rakeback', e.target.value);
        });
    }

    // クリアボタン
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', () => {
            if (elements.pasteInput) elements.pasteInput.value = '';
            if (elements.resultsSection) elements.resultsSection.classList.remove('show');
            if (elements.resultsContainer) elements.resultsContainer.innerHTML = '';
        });
    }

    // ローディング表示
    function showLoading(text = 'Loading...') {
        if (elements.loadingOverlay) {
            const loadingText = elements.loadingOverlay.querySelector('.loading-text');
            if (loadingText) {
                loadingText.textContent = text;
            }
            elements.loadingOverlay.classList.add('show');
        }
    }

    function hideLoading() {
        if (elements.loadingOverlay) {
            elements.loadingOverlay.classList.remove('show');
        }
    }

    // エラー表示
    function showError(message) {
        console.error(message);
        
        if (elements.errorToast) {
            elements.errorToast.textContent = message;
            elements.errorToast.classList.add('show');
            
            setTimeout(() => {
                elements.errorToast.classList.remove('show');
            }, 5000);
        } else {
            alert(message);
        }
    }

    // 判定ボタン
    if (elements.analyzeBtn) {
        elements.analyzeBtn.addEventListener('click', async () => {
            console.log('Analyze button clicked');
            
            const text = elements.pasteInput ? elements.pasteInput.value.trim() : '';
            
            if (!text) {
                showError('Please enter handicap data');
                return;
            }
            
            // ローディング開始
            if (elements.analyzeBtn) {
                elements.analyzeBtn.classList.add('loading');
                elements.analyzeBtn.disabled = true;
            }
            showLoading('Fetching odds data...');
            
            try {
                const response = await fetch('/analyze_paste', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        sport: elements.sportSelect ? elements.sportSelect.value : 'mlb',
                        rakeback: elements.rakebackSelect ? parseFloat(elements.rakebackSelect.value) : 0.015,
                        jp_odds: 1.9,
                        date: null  // 自動判定
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'An error occurred');
                }
                
                const results = await response.json();
                displayResults(results);
                
            } catch (error) {
                console.error('Error:', error);
                showError(error.message || 'Communication error occurred');
            } finally {
                if (elements.analyzeBtn) {
                    elements.analyzeBtn.classList.remove('loading');
                    elements.analyzeBtn.disabled = false;
                }
                hideLoading();
            }
        });
    }

    // 結果表示
    function displayResults(results) {
        if (!elements.resultsContainer) {
            console.error('Results container not found');
            return;
        }
        
        elements.resultsContainer.innerHTML = '';
        
        if (!results || results.length === 0) {
            elements.resultsContainer.innerHTML = '<p class="no-results">No results found</p>';
            if (elements.resultsSection) {
                elements.resultsSection.classList.add('show');
            }
            return;
        }
        
        // 試合ごとにグループ化
        const gameGroups = groupByGame(results);
        
        gameGroups.forEach(game => {
            const card = createGameCard(game);
            elements.resultsContainer.appendChild(card);
        });
        
        if (elements.resultsSection) {
            elements.resultsSection.classList.add('show');
            // スクロール
            setTimeout(() => {
                elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
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
                    game_datetime: result.game_datetime,
                    time_until_game: result.time_until_game,
                    sides: []
                });
            }
            
            games.get(gameKey).sides.push(result);
        });
        
        return Array.from(games.values());
    }

    // ゲームカード作成
    function createGameCard(game) {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        // タイトル
        const title = document.createElement('div');
        title.className = 'game-title';
        title.innerHTML = `
            <h3>${game.team_a_jp} vs ${game.team_b_jp}</h3>
            ${game.time_until_game ? `<span class="time-until">${game.time_until_game}</span>` : ''}
        `;
        card.appendChild(title);
        
        // 各サイドの結果
        const sidesContainer = document.createElement('div');
        sidesContainer.className = 'sides-container';
        
        game.sides.forEach(side => {
            if (side.error) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'side-error';
                errorDiv.textContent = side.error;
                sidesContainer.appendChild(errorDiv);
            } else if (side.verdict) {
                const sideElement = createSideResult(side);
                sidesContainer.appendChild(sideElement);
            }
        });
        
        card.appendChild(sidesContainer);
        
        // 両側比較（両方成功した場合）
        const validSides = game.sides.filter(s => !s.error && s.verdict);
        if (validSides.length === 2) {
            const comparison = createComparison(validSides);
            card.appendChild(comparison);
        }
        
        return card;
    }

    // サイド結果作成
    function createSideResult(result) {
        const container = document.createElement('div');
        container.className = `side-result verdict-${result.verdict || 'minus'}`;
        
        // ヘッダー
        const header = document.createElement('div');
        header.className = 'side-header';
        
        const teamName = document.createElement('span');
        teamName.className = 'team-name';
        teamName.textContent = `${result.fav_team_jp} (${result.jp_line || '-'})`;
        
        const verdict = document.createElement('span');
        verdict.className = `verdict-badge ${result.verdict}`;
        verdict.textContent = formatVerdict(result.verdict);
        
        header.appendChild(teamName);
        header.appendChild(verdict);
        container.appendChild(header);
        
        // 統計
        const stats = document.createElement('div');
        stats.className = 'side-stats';
        
        const ev = document.createElement('div');
        ev.className = 'stat';
        ev.innerHTML = `<span class="label">EV:</span> <span class="value ${result.ev_pct_rake >= 0 ? 'positive' : 'negative'}">${formatEV(result.ev_pct_rake)}</span>`;
        stats.appendChild(ev);
        
        const prob = document.createElement('div');
        prob.className = 'stat';
        prob.innerHTML = `<span class="label">Win%:</span> <span class="value">${formatProb(result.fair_prob)}</span>`;
        stats.appendChild(prob);
        
        const odds = document.createElement('div');
        odds.className = 'stat';
        odds.innerHTML = `<span class="label">Odds:</span> <span class="value">${formatOdds(result.fair_odds)}</span>`;
        stats.appendChild(odds);
        
        container.appendChild(stats);
        return container;
    }

    // 両側比較
    function createComparison(sides) {
        const comparison = document.createElement('div');
        comparison.className = 'comparison';
        
        const side1EV = sides[0].ev_pct_rake || -100;
        const side2EV = sides[1].ev_pct_rake || -100;
        
        let message = '';
        let className = '';
        
        if (side1EV > 0 && side2EV > 0) {
            message = '✅ Both sides positive EV';
            className = 'both-positive';
        } else if (side1EV > side2EV && side1EV > 0) {
            message = `⭐ ${sides[0].fav_team_jp} side is better`;
            className = 'recommendation';
        } else if (side2EV > side1EV && side2EV > 0) {
            message = `⭐ ${sides[1].fav_team_jp} side is better`;
            className = 'recommendation';
        } else {
            message = '⚠️ Both sides negative EV';
            className = 'warning';
        }
        
        comparison.className += ' ' + className;
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

    function formatVerdict(verdict) {
        const map = {
            'clear_plus': 'BEST',
            'plus': 'GOOD',
            'fair': 'FAIR',
            'minus': 'PASS'
        };
        return map[verdict] || verdict;
    }

    // デバッグモード
    if (window.location.hash === '#debug') {
        if (elements.pasteInput) {
            elements.pasteInput.value = 'Yankees<0.1>\nRed Sox\n\nDodgers\nPadres<1.5>';
        }
    }

    console.log('Initialization complete');
});