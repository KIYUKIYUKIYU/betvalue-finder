// app/static/app.js
// BetValue Finder フロントエンドロジック - 両側評価対応版

document.addEventListener('DOMContentLoaded', function() {
    console.log('BetValue Finder initialized');
    
    // DOM要素の取得
    const elements = {
        themeToggle: document.getElementById('theme-toggle'),
        sportSelect: document.getElementById('sport-select'),
        rakebackSelect: document.getElementById('rakeback-select'),
        dateInput: document.getElementById('date-input'),
        autoDate: document.getElementById('auto-date'),
        pasteInput: document.getElementById('paste-input'),
        clearBtn: document.getElementById('clear-btn'),
        analyzeBtn: document.getElementById('analyze-btn'),
        resultsSection: document.getElementById('results-section'),
        resultsContainer: document.getElementById('results-container'),
        errorToast: document.getElementById('error-toast'),
        loadingOverlay: document.getElementById('loading-overlay'),
        // status
        statusKeyVal: document.getElementById('status-key-val'),
        statusMlbVal: document.getElementById('status-mlb-val'),
        statusMlbRem: document.getElementById('status-mlb-remaining'),
        statusSocVal: document.getElementById('status-soccer-val'),
        statusSocRem: document.getElementById('status-soccer-remaining'),
        statusUpdated: document.getElementById('status-updated')
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
        elements.themeToggle.textContent = currentTheme === 'light' ? '🌙' : '☀️';
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
    
    // 自動日付の切替: チェックONでdate入力を無効化
    if (elements.autoDate && elements.dateInput) {
        const updateDateDisabled = () => {
            elements.dateInput.disabled = !!elements.autoDate.checked;
        };
        updateDateDisabled();
        elements.autoDate.addEventListener('change', updateDateDisabled);
    }

    // クリアボタン
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', () => {
            if (elements.pasteInput) {
                elements.pasteInput.value = '';
                elements.pasteInput.focus();
            }
            if (elements.resultsContainer) {
                elements.resultsContainer.innerHTML = '';
            }
            if (elements.resultsSection) {
                elements.resultsSection.classList.remove('show');
            }
        });
    }
    
    // 簡易スポーツ推定（保険）
    function guessSportFromText(text) {
        const soccerHints = [
            "チェルシー","フラム","ホッフェンハイム","フランクフルト","マンチェスター",
            "バルセロナ","レアル","インテル","ブンデス","プレミア","セリエ","リバプール","アーセナル"
        ];
        const mlbHints = [
            "ヤンキース","レッドソックス","ドジャース","メッツ","フィリーズ","カブス","ブレーブス","エンゼルス"
        ];
        const s = (text || '').replace(/\s/g, '');
        const hasSoccer = soccerHints.some(k => s.includes(k));
        const hasMlb = mlbHints.some(k => s.includes(k));
        if (hasSoccer && !hasMlb) return 'soccer';
        if (hasMlb && !hasSoccer) return 'mlb';
        return elements.sportSelect?.value || 'mlb';
    }

    // 分析ボタン
    elements.analyzeBtn.addEventListener('click', async (event) => {
        event.preventDefault(); // Prevent any form submission behavior
        
        const inputText = elements.pasteInput.value.trim();
        
        if (!inputText) {
            showError('テキストを入力してください');
            return;
        }
        
        let sport = elements.sportSelect?.value || 'mlb';
        const rakeback = parseFloat(elements.rakebackSelect?.value || '0.015');
        // 入力内容からの保険的な推定
        sport = guessSportFromText(inputText);
        if (elements.sportSelect) elements.sportSelect.value = sport;

        // 日付: 自動ONならnull、OFFなら入力値
        let dateValue = null;
        if (elements.autoDate && elements.dateInput) {
            if (!elements.autoDate.checked) {
                dateValue = elements.dateInput.value || null;
            }
        }
        
        // ローディング表示
        showLoading(true);
        elements.analyzeBtn.disabled = true;
        
        try {
            const requestPayload = {
                text: inputText,
                sport: sport,
                rakeback: rakeback,
                jp_odds: 1.9,
                date: dateValue
            };
            
            // ネットワークデバッグ情報
            console.log('Sending request:', requestPayload);
            console.log('Request URL:', '/analyze_paste');
            console.log('Request headers:', {'Content-Type': 'application/json'});
            console.log('Request body:', JSON.stringify(requestPayload));

            const response = await fetch('/analyze_paste', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestPayload)
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                const errorText = await response.text();
                console.log('Error response text:', errorText);
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = {detail: errorText};
                }
                throw new Error(errorData.detail || 'Analysis failed');
            }
            
            const results = await response.json();
            console.log('Analysis results:', results);
            
            // 結果を表示
            renderResults(results);
            
        } catch (error) {
            console.error('Analysis error:', error);
            showError(`エラー: ${error.message}`);
        } finally {
            showLoading(false);
            elements.analyzeBtn.disabled = false;
        }
    });
    
    // 結果を表示する関数（新バージョン - 両側評価対応）
    function renderResults(results) {
        if (!elements.resultsContainer) return;
        
        elements.resultsContainer.innerHTML = '';
        
        if (!results || results.length === 0) {
            elements.resultsContainer.innerHTML = '<p class="no-results">結果がありません</p>';
            return;
        }
        
        results.forEach(game => {
            const card = createGameCard(game);
            elements.resultsContainer.appendChild(card);
        });
        
        if (elements.resultsSection) {
            elements.resultsSection.classList.add('show');
            setTimeout(() => {
                elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }
    
    // ゲームカード作成関数（両側評価版）
    function createGameCard(game) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.style.marginBottom = '20px';
        card.style.padding = '15px';
        card.style.backgroundColor = '#fff';
        card.style.borderRadius = '8px';
        card.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
        
        // エラーがある場合
        if (game.error) {
            card.innerHTML = `
                <div class="game-title" style="margin-bottom: 10px;">
                    <h3 style="margin: 0;">${game.team_a_jp} vs ${game.team_b_jp}</h3>
                </div>
                <div class="error-message" style="color: #f44336; padding: 10px; background: #ffebee; border-radius: 4px;">
                    ${game.error}
                </div>
            `;
            return card;
        }
        
        // タイトル
        const title = document.createElement('div');
        title.className = 'game-title';
        title.style.marginBottom = '15px';
        title.style.borderBottom = '1px solid #e0e0e0';
        title.style.paddingBottom = '10px';
        
        const favTeamDisplay = game.fav_team_jp || game.fav_team || 'N/A';
        const dogTeamDisplay = game.fav_team === game.team_a ? game.team_b_jp : game.team_a_jp;
        
        // 大幅ハンデの警告
        const isLargeHandicap = game.pinnacle_line && Math.abs(game.pinnacle_line) >= 2.0;
        const warningText = isLargeHandicap ? 
            '<div style="color: #ff9800; font-size: 0.8em; margin-top: 5px;">⚠️ 大幅ハンデ（補間データ使用の可能性）</div>' : '';
        
        title.innerHTML = `
            <h3 style="margin: 0 0 5px 0; color: #333;">
                ${game.team_a_jp} vs ${game.team_b_jp}
                ${game.game_time_jst ? `<span style="font-size: 0.7em; color: #666; margin-left: 10px;">📅 ${game.game_time_jst}</span>` : ''}
            </h3>
            <div style="font-size: 0.9em; color: #666;">
                <span>ライン: <strong>${game.jp_line || 'N/A'}</strong></span>
                <span style="margin-left: 15px;">フェイバリット: <strong>${favTeamDisplay}</strong></span>
            </div>
            ${warningText}
        `;
        card.appendChild(title);
        
        // 両側の結果コンテナ
        const sidesContainer = document.createElement('div');
        sidesContainer.className = 'sides-container';
        sidesContainer.style.display = 'grid';
        sidesContainer.style.gridTemplateColumns = '1fr 1fr';
        sidesContainer.style.gap = '15px';
        sidesContainer.style.marginBottom = '15px';
        
        // フェイバリット側
        if (game.fav_team) {
            const favDiv = createSideDiv(
                favTeamDisplay,
                'FAVORITE',
                `-${game.pinnacle_line || 0}`,
                null, // 勝率表示を除去
                game.fav_raw_odds,    // 生ピナクルオッズ
                game.fav_fair_odds,   // マージン除去オッズ（参考用）
                game.fav_ev_pct,      // レーキ無しEV
                game.fav_ev_pct_rake, // レーキ込みEV
                game.fav_verdict,
                game.recommended_side === 'favorite'
            );
            sidesContainer.appendChild(favDiv);
        }
        
        // アンダードッグ側
        if (game.fav_team) {
            const dogDiv = createSideDiv(
                dogTeamDisplay,
                'UNDERDOG',
                `+${game.pinnacle_line || 0}`,
                null, // 勝率表示を除去
                game.dog_raw_odds,    // 生ピナクルオッズ
                game.dog_fair_odds,   // マージン除去オッズ（参考用）
                game.dog_ev_pct,      // レーキ無しEV
                game.dog_ev_pct_rake, // レーキ込みEV
                game.dog_verdict,
                game.recommended_side === 'underdog'
            );
            sidesContainer.appendChild(dogDiv);
        }
        
        card.appendChild(sidesContainer);
        
        // 推奨表示
        if (game.recommended_side && game.recommended_side !== 'none') {
            const recommendDiv = document.createElement('div');
            recommendDiv.className = 'recommendation';
            recommendDiv.style.padding = '10px';
            recommendDiv.style.backgroundColor = '#e8f5e9';
            recommendDiv.style.borderRadius = '4px';
            recommendDiv.style.textAlign = 'center';
            recommendDiv.style.fontWeight = 'bold';
            recommendDiv.style.color = '#2e7d32';
            
            const recText = game.recommended_side === 'favorite' 
                ? `🎯 推奨: ${favTeamDisplay}（フェイバリット）`
                : `🎯 推奨: ${dogTeamDisplay}（アンダードッグ）`;
            
            recommendDiv.innerHTML = recText;
            card.appendChild(recommendDiv);
        } else if (game.recommended_side === 'none') {
            const noRecDiv = document.createElement('div');
            noRecDiv.style.padding = '10px';
            noRecDiv.style.backgroundColor = '#fff3e0';
            noRecDiv.style.borderRadius = '4px';
            noRecDiv.style.textAlign = 'center';
            noRecDiv.style.color = '#e65100';
            noRecDiv.innerHTML = '⚠️ 両側とも推奨なし';
            card.appendChild(noRecDiv);
        }
        
        return card;
    }
    
    // 各サイドの表示を作成（2-way表示対応）
    function createSideDiv(teamName, sideType, line, fairProb, rawOdds, fairOdds, evPct, evPctRake, verdict, isRecommended) {
        const div = document.createElement('div');
        div.className = `side-result ${verdict || 'unknown'}`;
        div.style.padding = '12px';
        div.style.borderRadius = '6px';
        div.style.border = isRecommended ? '2px solid #4CAF50' : '1px solid #e0e0e0';
        div.style.backgroundColor = isRecommended ? '#f1f8e9' : '#fafafa';
        
        // Verdictに応じた色設定
        const verdictColors = {
            'clear_plus': '#4CAF50',
            'plus': '#8BC34A',
            'fair': '#FFC107',
            'minus': '#F44336'
        };
        
        const verdictLabels = {
            'clear_plus': 'CLEAR+',
            'plus': 'PLUS',
            'fair': 'FAIR',
            'minus': 'MINUS'
        };
        
        const verdictColor = verdictColors[verdict] || '#9E9E9E';
        const verdictLabel = verdictLabels[verdict] || 'N/A';
        
        // EV%の表示色（レーキ込みベース）
        const evColor = evPctRake >= 0 ? '#4CAF50' : (evPctRake >= -3 ? '#FFC107' : '#F44336');
        const evColorPlain = evPct >= 0 ? '#4CAF50' : (evPct >= -3 ? '#FFC107' : '#F44336');
        
        div.innerHTML = `
            <div>
                <h4 style="margin: 0 0 10px 0; color: #333; font-size: 1.1em;">
                    ${teamName}
                    <span style="font-size: 0.75em; color: #666; margin-left: 5px;">
                        (${sideType} ${line})
                    </span>
                </h4>
                <div style="display: grid; gap: 6px; font-size: 0.9em;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666;">生オッズ:</span>
                        <strong style="color: #1976D2;">${rawOdds ? rawOdds.toFixed(3) : 'N/A'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666;">除去オッズ:</span>
                        <strong style="color: #757575;">${fairOdds ? fairOdds.toFixed(3) : 'N/A'} <span style="font-size: 0.8em;">(参考)</span></strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666;">EV vs 1.9:</span>
                        <strong style="color: ${evColorPlain};">
                            ${evPct !== null && evPct !== undefined ? evPct.toFixed(1) + '%' : 'N/A'}
                        </strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666;">EV (rake):</span>
                        <strong style="color: ${evColor};">
                            ${evPctRake !== null && evPctRake !== undefined ? evPctRake.toFixed(1) + '%' : 'N/A'}
                        </strong>
                    </div>
                    <div style="margin-top: 8px; text-align: center;">
                        <span style="
                            background-color: ${verdictColor}; 
                            color: white; 
                            padding: 4px 12px; 
                            border-radius: 4px; 
                            font-size: 0.85em;
                            font-weight: bold;
                        ">
                            ${verdictLabel}
                        </span>
                    </div>
                </div>
                ${isRecommended ? '<div style="margin-top: 8px; text-align: center; color: #4CAF50; font-weight: bold;">✓ BEST</div>' : ''}
            </div>
        `;
        
        return div;
    }
    
    // エラー表示
    function showError(message) {
        if (!elements.errorToast) return;
        
        elements.errorToast.textContent = message;
        elements.errorToast.classList.add('show');
        
        setTimeout(() => {
            elements.errorToast.classList.remove('show');
        }, 3000);
    }
    
    // ローディング表示
    function showLoading(show) {
        if (!elements.loadingOverlay) return;
        
        if (show) {
            elements.loadingOverlay.classList.add('show');
        } else {
            elements.loadingOverlay.classList.remove('show');
        }
    }
    
    // サンプルデータの設定
    const sampleData = `オリオールズ
レッドソックス<0.3>

ガーディアンズ<0.7>
レイズ

ブルージェイズ<0.7>
ツインズ`;
    
    // サンプルボタンがあれば設定
    const sampleBtn = document.getElementById('sample-btn');
    if (sampleBtn) {
        sampleBtn.addEventListener('click', () => {
            if (elements.pasteInput) {
                elements.pasteInput.value = sampleData;
            }
        });
    }
    
    console.log('BetValue Finder ready');

    // ===== APIステータス取得 =====
    async function fetchApiStatus() {
        try {
            const res = await fetch('/api_status');
            if (!res.ok) throw new Error('status HTTP ' + res.status);
            const s = await res.json();
            // key
            if (elements.statusKeyVal) {
                elements.statusKeyVal.textContent = s.api_key_configured ? (s.api_key_masked || 'SET') : 'NOT SET';
                elements.statusKeyVal.style.color = s.api_key_configured ? '#2e7d32' : '#c62828';
            }
            // mlb
            if (elements.statusMlbVal) {
                const ok = s.mlb && s.mlb.ok;
                elements.statusMlbVal.textContent = ok ? 'OK' : 'NG';
                elements.statusMlbVal.style.color = ok ? '#2e7d32' : '#c62828';
            }
            if (elements.statusMlbRem) {
                const r = s.mlb && s.mlb.remaining ? s.mlb.remaining : '';
                elements.statusMlbRem.textContent = r ? `remaining: ${r}` : '\u00A0';
            }
            // soccer
            if (elements.statusSocVal) {
                const ok = s.soccer && s.soccer.ok;
                elements.statusSocVal.textContent = ok ? 'OK' : 'NG';
                elements.statusSocVal.style.color = ok ? '#2e7d32' : '#c62828';
            }
            if (elements.statusSocRem) {
                const r = s.soccer && s.soccer.remaining ? s.soccer.remaining : '';
                elements.statusSocRem.textContent = r ? `remaining: ${r}` : '\u00A0';
            }
            if (elements.statusUpdated) {
                const ts = new Date().toLocaleString();
                elements.statusUpdated.textContent = `更新: ${ts}`;
            }
        } catch (e) {
            if (elements.statusKeyVal) {
                elements.statusKeyVal.textContent = 'ERROR';
                elements.statusKeyVal.style.color = '#c62828';
            }
        }
    }
    fetchApiStatus();
    setInterval(fetchApiStatus, 60000);
});
