// BetValue Finder Desktop - Modern JavaScript
// リアルタイム処理可視化 + 個人使用向け機能強化

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 BetValue Finder Desktop initialized');

    // DOM要素の取得
    const elements = {
        // Header
        themeToggle: document.getElementById('theme-toggle'),

        // Status dashboard
        statusKeyVal: document.getElementById('status-key-val'),
        statusMlbVal: document.getElementById('status-mlb-val'),
        statusMlbRem: document.getElementById('status-mlb-remaining'),
        statusSocVal: document.getElementById('status-soccer-val'),
        statusSocRem: document.getElementById('status-soccer-remaining'),
        statusUpdated: document.getElementById('status-updated'),

        // Settings
        sportSelect: document.getElementById('sport-select'),
        rakebackSelect: document.getElementById('rakeback-select'),
        dateInput: document.getElementById('date-input'),
        autoDate: document.getElementById('auto-date'),

        // Input
        pasteInput: document.getElementById('paste-input'),
        clearBtn: document.getElementById('clear-btn'),
        sampleBtn: document.getElementById('sample-btn'),
        analyzeBtn: document.getElementById('analyze-btn'),

        // Progress bar
        progressContainer: document.getElementById('progress-container'),
        progressText: document.getElementById('progress-text'),
        progressPercentage: document.getElementById('progress-percentage'),
        progressFill: document.getElementById('progress-fill'),
        progressSteps: document.getElementById('progress-steps'),

        // Results
        resultsSection: document.getElementById('results-section'),
        resultsContainer: document.getElementById('results-container'),
        sortByEvBtn: document.getElementById('sort-by-ev'),
        exportTextBtn: document.getElementById('export-text'),

        // Toasts and overlays
        errorToast: document.getElementById('error-toast'),
        successToast: document.getElementById('success-toast'),
        loadingOverlay: document.getElementById('loading-overlay'),

        // Modal
        textExportModal: document.getElementById('text-export-modal'),
        exportedText: document.getElementById('exported-text'),
        closeModal: document.getElementById('close-modal'),
        copyText: document.getElementById('copy-text')
    };

    // 必須要素のチェック
    if (!elements.analyzeBtn || !elements.pasteInput) {
        console.error('Required elements not found');
        showError('ページの読み込みに失敗しました。再読み込みしてください。');
        return;
    }

    // グローバル状態
    let currentResults = [];
    let sortOrder = 'desc'; // EV順ソートの方向

    // ===========================================
    // テーマ管理
    // ===========================================

    let currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);

    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', () => {
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', currentTheme);
            localStorage.setItem('theme', currentTheme);
            showSuccess(`${currentTheme === 'light' ? 'ライト' : 'ダーク'}モードに切り替えました`);
        });
    }

    // ===========================================
    // 設定管理
    // ===========================================

    // 競技選択の保存・復元
    if (elements.sportSelect) {
        const savedSport = localStorage.getItem('sport') || 'mlb';
        elements.sportSelect.value = savedSport;
        elements.sportSelect.addEventListener('change', (e) => {
            localStorage.setItem('sport', e.target.value);
            showSuccess(`競技を${e.target.options[e.target.selectedIndex].text}に変更しました`);
        });
    }

    // レーキバック選択の保存・復元
    if (elements.rakebackSelect) {
        const savedRakeback = localStorage.getItem('rakeback') || '0';
        elements.rakebackSelect.value = savedRakeback;
        elements.rakebackSelect.addEventListener('change', (e) => {
            localStorage.setItem('rakeback', e.target.value);
            const percentage = (parseFloat(e.target.value) * 100).toFixed(1);
            showSuccess(`レーキバックを${percentage}%に設定しました`);
        });
    }

    // 自動日付の切替
    if (elements.autoDate && elements.dateInput) {
        const updateDateDisabled = () => {
            elements.dateInput.disabled = elements.autoDate.checked;
        };
        updateDateDisabled();
        elements.autoDate.addEventListener('change', updateDateDisabled);
    }

    // ===========================================
    // 入力管理
    // ===========================================

    // クリアボタン
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', () => {
            if (elements.pasteInput) {
                elements.pasteInput.value = '';
                elements.pasteInput.focus();
            }
            clearResults();
            showSuccess('入力をクリアしました');
        });
    }

    // サンプルボタン
    if (elements.sampleBtn) {
        const sampleData = `オリオールズ
レッドソックス<0.3>

ガーディアンズ<0.7>
レイズ

ブルージェイズ<0.7>
ツインズ`;

        elements.sampleBtn.addEventListener('click', () => {
            if (elements.pasteInput) {
                elements.pasteInput.value = sampleData;
            }
            showSuccess('サンプルデータを入力しました');
        });
    }

    // ===========================================
    // 分析処理
    // ===========================================

    // 競技推定関数
    function guessSportFromText(text) {
        const soccerHints = [
            "チェルシー", "フラム", "ホッフェンハイム", "フランクフルト", "マンチェスター",
            "バルセロナ", "レアル", "インテル", "ブンデス", "プレミア", "セリエ", "リバプール", "アーセナル"
        ];
        const mlbHints = [
            "ヤンキース", "レッドソックス", "ドジャース", "メッツ", "フィリーズ", "カブス", "ブレーブス", "エンゼルス"
        ];
        const npbHints = [
            "巨人", "阪神", "中日", "広島", "ヤクルト", "横浜", "ソフトバンク", "日本ハム", "ロッテ", "西武", "楽天", "オリックス"
        ];

        const s = (text || '').replace(/\\s/g, '');
        const hasSoccer = soccerHints.some(k => s.includes(k));
        const hasMlb = mlbHints.some(k => s.includes(k));
        const hasNpb = npbHints.some(k => s.includes(k));

        if (hasSoccer && !hasMlb && !hasNpb) return 'soccer';
        if (hasMlb && !hasSoccer && !hasNpb) return 'mlb';
        if (hasNpb && !hasMlb && !hasSoccer) return 'npb';

        return elements.sportSelect?.value || 'mlb';
    }

    // 分析実行
    elements.analyzeBtn.addEventListener('click', async (event) => {
        event.preventDefault();

        const inputText = elements.pasteInput.value.trim();

        if (!inputText) {
            showError('ハンデテキストを入力してください');
            return;
        }

        // 設定値の取得
        let sport = elements.sportSelect?.value || 'mlb';
        const rakeback = parseFloat(elements.rakebackSelect?.value || '0.015');

        // 自動競技推定
        const guessedSport = guessSportFromText(inputText);
        if (guessedSport !== sport) {
            sport = guessedSport;
            if (elements.sportSelect) {
                elements.sportSelect.value = sport;
            }
            showSuccess(`競技を自動で${sport.toUpperCase()}に設定しました`);
        }

        // 日付設定
        let dateValue = null;
        if (elements.autoDate && elements.dateInput) {
            if (!elements.autoDate.checked) {
                dateValue = elements.dateInput.value || null;
            }
        }

        // 分析開始（プログレスバー付き）
        setAnalyzeButtonLoading(true);
        showProgressBar(true);

        try {
            const requestPayload = {
                text: inputText,
                sport: sport,
                rakeback: rakeback,
                date: dateValue
            };

            console.log('🔍 Starting streaming analysis:', requestPayload);

            // SSE (Server-Sent Events) で分析実行
            const startTime = Date.now();
            const results = await analyzeWithProgress('/analyze_paste_stream', requestPayload);
            const responseTime = Date.now() - startTime;
            console.log('📊 Streaming analysis completed:', results);

            // 結果を保存して表示
            currentResults = results;
            renderResults(results);

            showSuccess(`分析完了！ ${responseTime}ms で処理されました`);

        } catch (error) {
            console.error('❌ Analysis error:', error);
            showError(`エラー: ${error.message}`);
        } finally {
            showLoading(false);
            setAnalyzeButtonLoading(false);
            showProgressBar(false);
        }
    });

    // ===========================================
    // 結果表示・管理
    // ===========================================

    function renderResults(results) {
        if (!elements.resultsContainer) return;

        elements.resultsContainer.innerHTML = '';

        if (!results || results.length === 0) {
            elements.resultsContainer.innerHTML = `
                <div class="no-results">
                    <h3>結果がありません</h3>
                    <p>入力されたハンデに該当する試合が見つかりませんでした。</p>
                </div>
            `;
            return;
        }

        // 結果サマリーを表示
        const summary = createResultsSummary(results);
        elements.resultsContainer.appendChild(summary);

        // 各試合カードを表示
        results.forEach((game, index) => {
            const card = createGameCard(game, index);
            elements.resultsContainer.appendChild(card);
        });

        if (elements.resultsSection) {
            elements.resultsSection.classList.add('show');
            setTimeout(() => {
                elements.resultsSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }, 300);
        }
    }

    function createResultsSummary(results) {
        const summary = document.createElement('div');
        summary.className = 'results-summary';

        // 統計を計算
        const totalGames = results.length;
        const successfulAnalysis = results.filter(game => !game.error).length;
        const gameStarted = results.filter(game => game.error_code === 'GAME_STARTED').length;
        const gamesCancelled = results.filter(game => game.error_code === 'GAME_CANCELLED').length;
        const noData = results.filter(game => game.error_code === 'NO_GAME_DATA' || game.error_code === 'PREGAME_NOT_FOUND').length;
        const otherErrors = totalGames - successfulAnalysis - gameStarted - gamesCancelled - noData;

        const recommendedGames = results.filter(game =>
            game.recommended_side && game.recommended_side !== 'none'
        ).length;

        summary.innerHTML = `
            <div style="background: var(--bg-card); border-radius: var(--radius-md); padding: 20px; margin-bottom: 24px; box-shadow: var(--shadow-sm); border: 1px solid var(--border-color);">
                <h3 style="margin: 0 0 16px 0; color: var(--text-primary); font-size: 1.1rem;">📊 解析サマリー</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--accent-color);">${totalGames}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">総試合数</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--success-color);">${successfulAnalysis}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">解析成功</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--warning-color);">${recommendedGames}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">推奨あり</div>
                    </div>
                    ${gameStarted > 0 ? `
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--status-live-color);">${gameStarted}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">開始済み</div>
                    </div>
                    ` : ''}
                    ${gamesCancelled > 0 ? `
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--status-cancelled-color);">${gamesCancelled}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">中止/延期</div>
                    </div>
                    ` : ''}
                    ${noData > 0 ? `
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--status-no-data-color);">${noData}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">データなし</div>
                    </div>
                    ` : ''}
                    ${otherErrors > 0 ? `
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--danger-color);">${otherErrors}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">その他エラー</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        return summary;
    }

    function createGameCard(game, index) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.dataset.index = index;

        // エラーがある場合
        if (game.error) {
            const statusIcon = getStatusIcon(game.error_code);
            const statusClass = getStatusClass(game.error_code);

            card.innerHTML = `
                <div class="game-title">
                    <h3>${game.team_a_jp || 'チームA'} vs ${game.team_b_jp || 'チームB'}</h3>
                </div>
                <div class="error-message ${statusClass}" style="padding: 16px; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.2em;">${statusIcon}</span>
                        <span>${game.error}</span>
                    </div>
                    ${getStatusDescription(game.error_code)}
                </div>
            `;
            card.classList.add('error', statusClass);
            return card;
        }

        // 推奨度によるカードクラス設定
        if (game.recommended_side && game.recommended_side !== 'none') {
            const recSideData = game.recommended_side === 'favorite' ?
                { ev: game.fav_ev_pct_rake, verdict: game.fav_verdict } :
                { ev: game.dog_ev_pct_rake, verdict: game.dog_verdict };

            if (recSideData.verdict) {
                card.classList.add(recSideData.verdict);
            }
        }

        // タイトルセクション
        const titleSection = createGameTitle(game);
        card.appendChild(titleSection);

        // 両側の結果
        const sidesContainer = createSidesContainer(game);
        card.appendChild(sidesContainer);

        // 推奨表示
        const recommendationSection = createRecommendation(game);
        if (recommendationSection) {
            card.appendChild(recommendationSection);
        }

        return card;
    }

    function createGameTitle(game) {
        const titleDiv = document.createElement('div');
        titleDiv.className = 'game-title';

        const favTeamDisplay = game.fav_team_jp || game.fav_team || 'N/A';
        const dogTeamDisplay = game.fav_team === game.team_a ?
            (game.team_b_jp || game.team_b) :
            (game.team_a_jp || game.team_a);

        // 大幅ハンデの警告
        const isLargeHandicap = game.pinnacle_line && Math.abs(game.pinnacle_line) >= 2.0;
        const warningBadge = isLargeHandicap ?
            '<span class="warning-badge">⚠️ 大幅ハンデ</span>' : '';

        titleDiv.innerHTML = `
            <h3>
                ${game.team_a_jp || game.team_a} vs ${game.team_b_jp || game.team_b}
                ${warningBadge}
            </h3>
            <div class="game-meta">
                ${game.game_time_jst ? `<div class="game-time">🕐 ${formatGameTime(game.game_time_jst)}</div>` : ''}
                <div>ライン: <strong>${game.jp_line || 'N/A'}</strong></div>
                <div>フェイバリット: <strong>${favTeamDisplay}</strong></div>
            </div>
        `;

        return titleDiv;
    }

    function createSidesContainer(game) {
        const container = document.createElement('div');
        container.className = 'sides-container';

        if (game.fav_team) {
            const favTeamDisplay = game.fav_team_jp || game.fav_team;
            const dogTeamDisplay = game.fav_team === game.team_a ?
                (game.team_b_jp || game.team_b) :
                (game.team_a_jp || game.team_a);

            // フェイバリット側
            const favSide = createSideResult(
                favTeamDisplay,
                'FAVORITE',
                `-${game.pinnacle_line || 0}`,
                game.fav_raw_odds,
                game.fav_fair_odds,
                game.fav_ev_pct,
                game.fav_ev_pct_rake,
                game.fav_verdict,
                game.recommended_side === 'favorite'
            );

            // アンダードッグ側
            const dogSide = createSideResult(
                dogTeamDisplay,
                'UNDERDOG',
                `+${game.pinnacle_line || 0}`,
                game.dog_raw_odds,
                game.dog_fair_odds,
                game.dog_ev_pct,
                game.dog_ev_pct_rake,
                game.dog_verdict,
                game.recommended_side === 'underdog'
            );

            container.appendChild(favSide);
            container.appendChild(dogSide);
        }

        return container;
    }

    function createSideResult(teamName, sideType, line, rawOdds, fairOdds, evPct, evPctRake, verdict, isRecommended) {
        const div = document.createElement('div');
        div.className = `side-result ${verdict || 'unknown'}`;
        if (isRecommended) {
            div.classList.add('recommended');
        }

        const verdictBadge = verdict ? `<div class="verdict-badge ${verdict}">${getVerdictLabel(verdict)}</div>` : '';
        const bestBadge = isRecommended ? '<div style="color: var(--success-color); font-weight: bold; margin-top: 8px;">✓ BEST CHOICE</div>' : '';

        div.innerHTML = `
            <h4>
                ${teamName}
                <span class="side-type">${sideType} ${line}</span>
            </h4>
            <div class="stats-grid">
                <div class="stat-row">
                    <span class="stat-label">生オッズ:</span>
                    <span class="stat-value">${rawOdds ? rawOdds.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">除去オッズ:</span>
                    <span class="stat-value">${fairOdds ? fairOdds.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">EV vs 1.9:</span>
                    <span class="stat-value ${getEvClass(evPct)}">${evPct !== null && evPct !== undefined ? evPct.toFixed(1) + '%' : 'N/A'}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">EV (rake):</span>
                    <span class="stat-value ${getEvClass(evPctRake)}">${evPctRake !== null && evPctRake !== undefined ? evPctRake.toFixed(1) + '%' : 'N/A'}</span>
                </div>
            </div>
            ${verdictBadge}
            ${bestBadge}
        `;

        return div;
    }

    function createRecommendation(game) {
        if (!game.recommended_side || game.recommended_side === 'none') {
            if (game.recommended_side === 'none') {
                const div = document.createElement('div');
                div.className = 'recommendation no-recommendation';
                div.style.backgroundColor = 'var(--warning-light)';
                div.style.color = 'var(--warning-color)';
                div.innerHTML = '⚠️ 両側とも推奨なし';
                return div;
            }
            return null;
        }

        const div = document.createElement('div');
        div.className = 'recommendation';

        const favTeamDisplay = game.fav_team_jp || game.fav_team;
        const dogTeamDisplay = game.fav_team === game.team_a ?
            (game.team_b_jp || game.team_b) :
            (game.team_a_jp || game.team_a);

        const recText = game.recommended_side === 'favorite'
            ? `🎯 推奨: ${favTeamDisplay}（フェイバリット）`
            : `🎯 推奨: ${dogTeamDisplay}（アンダードッグ）`;

        div.innerHTML = recText;
        return div;
    }

    // ===========================================
    // 結果操作（ソート・エクスポート）
    // ===========================================

    // EV順ソート
    if (elements.sortByEvBtn) {
        elements.sortByEvBtn.addEventListener('click', () => {
            if (currentResults.length === 0) {
                showError('ソートする結果がありません');
                return;
            }

            // EV値（レーキ込み）でソート
            const sortedResults = [...currentResults].sort((a, b) => {
                const getHighestEv = (game) => {
                    const favEv = game.fav_ev_pct_rake || -Infinity;
                    const dogEv = game.dog_ev_pct_rake || -Infinity;
                    return Math.max(favEv, dogEv);
                };

                const aHighestEv = getHighestEv(a);
                const bHighestEv = getHighestEv(b);

                return sortOrder === 'desc' ? bHighestEv - aHighestEv : aHighestEv - bHighestEv;
            });

            // ソート方向を切り替え
            sortOrder = sortOrder === 'desc' ? 'asc' : 'desc';

            renderResults(sortedResults);
            elements.sortByEvBtn.textContent = `EV順ソート ${sortOrder === 'desc' ? '↓' : '↑'}`;
            showSuccess(`期待値順（${sortOrder === 'desc' ? '降順' : '昇順'}）でソートしました`);
        });
    }

    // テキスト出力
    if (elements.exportTextBtn) {
        elements.exportTextBtn.addEventListener('click', () => {
            if (currentResults.length === 0) {
                showError('エクスポートする結果がありません');
                return;
            }

            const exportText = generateExportText(currentResults);

            if (elements.exportedText) {
                elements.exportedText.value = exportText;
            }

            if (elements.textExportModal) {
                elements.textExportModal.classList.add('show');
            }
        });
    }

    // モーダル閉じる
    if (elements.closeModal) {
        elements.closeModal.addEventListener('click', () => {
            if (elements.textExportModal) {
                elements.textExportModal.classList.remove('show');
            }
        });
    }

    // モーダル背景クリックで閉じる
    if (elements.textExportModal) {
        elements.textExportModal.addEventListener('click', (e) => {
            if (e.target === elements.textExportModal) {
                elements.textExportModal.classList.remove('show');
            }
        });
    }

    // テキストコピー
    if (elements.copyText) {
        elements.copyText.addEventListener('click', async () => {
            if (elements.exportedText) {
                try {
                    await navigator.clipboard.writeText(elements.exportedText.value);
                    showSuccess('テキストをクリップボードにコピーしました！');
                    elements.copyText.textContent = '✅ コピー済み';
                    setTimeout(() => {
                        elements.copyText.textContent = '📋 コピー';
                    }, 2000);
                } catch (err) {
                    console.error('Copy failed:', err);
                    // フォールバック: 選択状態にする
                    elements.exportedText.select();
                    showError('コピーに失敗しました。手動で選択してコピーしてください。');
                }
            }
        });
    }

    // ===========================================
    // ステータス表示関数
    // ===========================================

    function getStatusIcon(errorCode) {
        const icons = {
            'GAME_STARTED': '🔴',
            'GAME_CANCELLED': '⚫',
            'NO_GAME_DATA': '❓',
            'PREGAME_NOT_FOUND': '🟡',
            'NO_HANDICAP_ODDS': '📊',
            'NO_ODDS': '📊',
            'EVALUATION_ERROR': '⚠️',
            'NO_HANDICAP': '❌'
        };
        return icons[errorCode] || '❌';
    }

    function getStatusClass(errorCode) {
        const classes = {
            'GAME_STARTED': 'status-live',
            'GAME_CANCELLED': 'status-cancelled',
            'NO_GAME_DATA': 'status-no-data',
            'PREGAME_NOT_FOUND': 'status-warning',
            'NO_HANDICAP_ODDS': 'status-warning',
            'NO_ODDS': 'status-warning',
            'EVALUATION_ERROR': 'status-error',
            'NO_HANDICAP': 'status-error'
        };
        return classes[errorCode] || 'status-error';
    }

    function getStatusDescription(errorCode) {
        const descriptions = {
            'GAME_STARTED': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">試合がすでに開始されているため、プリゲームオッズは利用できません。</div>',
            'GAME_CANCELLED': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">試合が中止または延期されました。</div>',
            'NO_GAME_DATA': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">本日の試合データが取得できません。API接続を確認してください。</div>',
            'PREGAME_NOT_FOUND': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">プリゲーム状態の試合が見つかりません。チーム名やハンデ表記を確認してください。</div>',
            'NO_HANDICAP_ODDS': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">ハンディキャップオッズが提供されていません。</div>',
            'NO_ODDS': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">オッズデータが取得できません。</div>',
            'EVALUATION_ERROR': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">評価処理中にエラーが発生しました。</div>',
            'NO_HANDICAP': '<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">ハンディキャップが指定されていません。</div>'
        };
        return descriptions[errorCode] || '';
    }

    // ===========================================
    // ユーティリティ関数
    // ===========================================

    function clearResults() {
        currentResults = [];
        if (elements.resultsContainer) {
            elements.resultsContainer.innerHTML = '';
        }
        if (elements.resultsSection) {
            elements.resultsSection.classList.remove('show');
        }
    }

    function getVerdictLabel(verdict) {
        const labels = {
            'clear_plus': 'CLEAR+',
            'plus': 'PLUS',
            'fair': 'FAIR',
            'minus': 'MINUS'
        };
        return labels[verdict] || 'N/A';
    }

    function getEvClass(ev) {
        if (ev === null || ev === undefined) return '';
        if (ev >= 0) return 'positive';
        if (ev >= -3) return '';
        return 'negative';
    }

    function formatGameTime(timeStr) {
        try {
            // JSTタイムスタンプをフォーマット
            const date = new Date(timeStr);
            const now = new Date();
            const diffMs = date.getTime() - now.getTime();
            const diffHours = diffMs / (1000 * 60 * 60);

            if (diffMs < 0) {
                return `${timeStr} (終了済み)`;
            } else if (diffHours < 24) {
                return `${timeStr} (${diffHours.toFixed(1)}時間後)`;
            } else {
                return timeStr;
            }
        } catch (e) {
            return timeStr;
        }
    }

    function generateExportText(results) {
        let text = `=== BetValue Finder 分析結果 ===\\n`;
        text += `生成日時: ${new Date().toLocaleString('ja-JP')}\\n`;
        text += `分析件数: ${results.length}件\\n\\n`;

        results.forEach((game, index) => {
            text += `[${index + 1}] ${game.team_a_jp || game.team_a} vs ${game.team_b_jp || game.team_b}\\n`;

            if (game.error) {
                text += `   エラー: ${game.error}\\n\\n`;
                return;
            }

            if (game.game_time_jst) {
                text += `   開始時刻: ${game.game_time_jst}\\n`;
            }

            text += `   ライン: ${game.jp_line || 'N/A'}\\n`;

            const favTeamDisplay = game.fav_team_jp || game.fav_team;
            const dogTeamDisplay = game.fav_team === game.team_a ?
                (game.team_b_jp || game.team_b) :
                (game.team_a_jp || game.team_a);

            if (game.fav_team) {
                text += `\\n   [フェイバリット] ${favTeamDisplay} (-${game.pinnacle_line || 0})\\n`;
                text += `     生オッズ: ${game.fav_raw_odds ? game.fav_raw_odds.toFixed(3) : 'N/A'}\\n`;
                text += `     EV (rake): ${game.fav_ev_pct_rake !== null ? game.fav_ev_pct_rake.toFixed(1) + '%' : 'N/A'}\\n`;
                text += `     判定: ${getVerdictLabel(game.fav_verdict)}\\n`;

                text += `\\n   [アンダードッグ] ${dogTeamDisplay} (+${game.pinnacle_line || 0})\\n`;
                text += `     生オッズ: ${game.dog_raw_odds ? game.dog_raw_odds.toFixed(3) : 'N/A'}\\n`;
                text += `     EV (rake): ${game.dog_ev_pct_rake !== null ? game.dog_ev_pct_rake.toFixed(1) + '%' : 'N/A'}\\n`;
                text += `     判定: ${getVerdictLabel(game.dog_verdict)}\\n`;
            }

            if (game.recommended_side && game.recommended_side !== 'none') {
                const recTeam = game.recommended_side === 'favorite' ? favTeamDisplay : dogTeamDisplay;
                text += `\\n   🎯 推奨: ${recTeam}\\n`;
            } else if (game.recommended_side === 'none') {
                text += `\\n   ⚠️ 推奨なし\\n`;
            }

            text += `\\n`;
        });

        text += `=== 出力終了 ===`;
        return text;
    }

    function setAnalyzeButtonLoading(loading) {
        if (!elements.analyzeBtn) return;

        if (loading) {
            elements.analyzeBtn.classList.add('loading');
            elements.analyzeBtn.disabled = true;
        } else {
            elements.analyzeBtn.classList.remove('loading');
            elements.analyzeBtn.disabled = false;
        }
    }

    function showLoading(show) {
        if (!elements.loadingOverlay) return;

        if (show) {
            elements.loadingOverlay.classList.add('show');
        } else {
            elements.loadingOverlay.classList.remove('show');
        }
    }

    function showError(message) {
        if (!elements.errorToast) return;

        elements.errorToast.textContent = message;
        elements.errorToast.classList.add('show');

        setTimeout(() => {
            elements.errorToast.classList.remove('show');
        }, 5000);
    }

    function showSuccess(message) {
        if (!elements.successToast) return;

        elements.successToast.textContent = message;
        elements.successToast.classList.add('show');

        setTimeout(() => {
            elements.successToast.classList.remove('show');
        }, 3000);
    }

    function showToast(message, type = 'info') {
        // 汎用トースト関数
        if (type === 'error') {
            showError(message);
        } else if (type === 'success') {
            showSuccess(message);
        } else if (type === 'warning') {
            // 警告用（既存のsuccessToastを使用してオレンジ色で表示）
            if (!elements.successToast) return;

            elements.successToast.textContent = message;
            elements.successToast.classList.add('show', 'warning');

            setTimeout(() => {
                elements.successToast.classList.remove('show', 'warning');
            }, 4000);
        } else {
            showSuccess(message);
        }
    }

    // ===========================================
    // APIステータス監視
    // ===========================================

    async function fetchApiStatus() {
        try {
            const startTime = performance.now();
            const response = await fetch('/api_status');
            const endTime = performance.now();
            const responseTime = Math.round(endTime - startTime);

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const status = await response.json();

            // API Key
            if (elements.statusKeyVal) {
                elements.statusKeyVal.textContent = status.api_key_configured ?
                    (status.api_key_masked || 'SET') : 'NOT SET';
                elements.statusKeyVal.style.color = status.api_key_configured ?
                    'var(--success-color)' : 'var(--danger-color)';
            }

            // MLB
            if (elements.statusMlbVal) {
                const ok = status.mlb && status.mlb.ok;
                elements.statusMlbVal.textContent = ok ? 'OK' : 'NG';
                elements.statusMlbVal.style.color = ok ? 'var(--success-color)' : 'var(--danger-color)';
            }
            if (elements.statusMlbRem) {
                const remaining = status.mlb && status.mlb.remaining ? status.mlb.remaining : '';
                elements.statusMlbRem.textContent = remaining ? `remaining: ${remaining}` : '';
            }

            // Soccer
            if (elements.statusSocVal) {
                const ok = status.soccer && status.soccer.ok;
                elements.statusSocVal.textContent = ok ? 'OK' : 'NG';
                elements.statusSocVal.style.color = ok ? 'var(--success-color)' : 'var(--danger-color)';
            }
            if (elements.statusSocRem) {
                const remaining = status.soccer && status.soccer.remaining ? status.soccer.remaining : '';
                elements.statusSocRem.textContent = remaining ? `remaining: ${remaining}` : '';
            }

            // 更新時刻
            if (elements.statusUpdated) {
                const now = new Date().toLocaleTimeString('ja-JP');
                elements.statusUpdated.textContent = `更新: ${now} (${responseTime}ms)`;
            }

        } catch (error) {
            console.error('Status fetch error:', error);
            if (elements.statusKeyVal) {
                elements.statusKeyVal.textContent = 'ERROR';
                elements.statusKeyVal.style.color = 'var(--danger-color)';
            }
            if (elements.statusUpdated) {
                elements.statusUpdated.textContent = `エラー: ${new Date().toLocaleTimeString('ja-JP')}`;
            }
        }
    }

    // 初回ステータス取得
    fetchApiStatus();

    // 60秒間隔でステータス更新
    setInterval(fetchApiStatus, 60000);

    // ===== プログレスバー関数 =====

    // プログレスバーの表示/非表示
    function showProgressBar(show) {
        if (elements.progressContainer) {
            elements.progressContainer.style.display = show ? 'block' : 'none';
            if (!show) {
                resetProgressBar();
            }
        }
    }

    // プログレスバーのリセット
    function resetProgressBar() {
        updateProgress(0, '準備中...');
        resetProgressSteps();
    }

    // プログレスの更新
    function updateProgress(percentage, message) {
        if (elements.progressFill) {
            elements.progressFill.style.width = `${percentage}%`;
        }
        if (elements.progressPercentage) {
            elements.progressPercentage.textContent = `${percentage}%`;
        }
        if (elements.progressText) {
            elements.progressText.textContent = message;
        }
    }

    // プログレスステップの更新
    function updateProgressStep(stepName, status) {
        if (elements.progressSteps) {
            const stepElement = elements.progressSteps.querySelector(`[data-step="${stepName}"]`);
            if (stepElement) {
                stepElement.classList.remove('active', 'completed');
                if (status === 'active') {
                    stepElement.classList.add('active');
                } else if (status === 'completed') {
                    stepElement.classList.add('completed');
                }
            }
        }
    }

    // すべてのプログレスステップをリセット
    function resetProgressSteps() {
        if (elements.progressSteps) {
            const steps = elements.progressSteps.querySelectorAll('.progress-step');
            steps.forEach(step => {
                step.classList.remove('active', 'completed');
            });
        }
    }

    // フェッチを使用したプログレス付き分析
    async function analyzeWithProgress(endpoint, payload) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        return new Promise((resolve, reject) => {
            let buffer = '';

            async function processStream() {
                try {
                    while (true) {
                        const { done, value } = await reader.read();

                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });

                        // SSE イベントを処理
                        const lines = buffer.split('\n\n');
                        buffer = lines.pop() || ''; // 未完了の行をバッファに保持

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const jsonData = line.slice(6);
                                try {
                                    const data = JSON.parse(jsonData);

                                    if (data.error) {
                                        reject(new Error(data.error));
                                        return;
                                    }

                                    if (data.step) {
                                        updateProgress(data.progress, data.message);
                                        updateProgressStep(data.step, 'active');

                                        // 前のステップを完了状態にする
                                        const steps = ['parse', 'teams', 'odds', 'calculate'];
                                        const currentIndex = steps.indexOf(data.step);
                                        for (let i = 0; i < currentIndex; i++) {
                                            updateProgressStep(steps[i], 'completed');
                                        }
                                    }

                                    if (data.step === 'complete') {
                                        updateProgressStep('calculate', 'completed');
                                        resolve(data.results);
                                        return;
                                    }

                                } catch (error) {
                                    console.error('Progress parsing error:', error);
                                    reject(error);
                                    return;
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.error('Stream processing error:', error);
                    reject(error);
                }
            }

            processStream();
        });
    }

    // グローバルに関数を公開
    window.showProgressBar = showProgressBar;
    window.updateProgress = updateProgress;
    window.updateProgressStep = updateProgressStep;

    console.log('✅ BetValue Finder Desktop ready');
});
