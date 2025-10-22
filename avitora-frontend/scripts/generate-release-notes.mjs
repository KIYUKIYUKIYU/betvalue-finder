#!/usr/bin/env node

/**
 * ============================================
 * AVITORA Frontend - Release Notes Generator
 * ============================================
 * 目的: リリースノートとCHANGELOGの自動生成
 * 実行: node scripts/generate-release-notes.mjs <version> [options]
 *
 * 例:
 * node scripts/generate-release-notes.mjs 0.1.0 \
 *   --highlights "Auth, Dashboard, Games完了" \
 *   --fixes "TS型不一致3件修正, A11y/レイアウトHotfix" \
 *   --qa "FINAL_QA_REPORT=PASS, DSv1違反0"
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// ============================================
// コマンドライン引数パース
// ============================================
const args = process.argv.slice(2);

if (args.length === 0 || args[0] === '--help') {
  console.log(`
使用方法: node scripts/generate-release-notes.mjs <version> [options]

オプション:
  --highlights <text>    主要なハイライト（カンマ区切り）
  --fixes <text>         修正内容（カンマ区切り）
  --qa <text>           QA結果サマリー
  --help                このヘルプを表示

例:
  node scripts/generate-release-notes.mjs 0.1.0 \\
    --highlights "認証, ダッシュボード, 試合一覧完了" \\
    --fixes "TypeScript型エラー修正, A11y改善" \\
    --qa "FINAL_QA_REPORT=PASS, DSv1違反0件"
  `);
  process.exit(0);
}

const version = args[0];
let highlights = '';
let fixes = '';
let qaResults = '';

for (let i = 1; i < args.length; i++) {
  if (args[i] === '--highlights') {
    highlights = args[++i];
  } else if (args[i] === '--fixes') {
    fixes = args[++i];
  } else if (args[i] === '--qa') {
    qaResults = args[++i];
  }
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('📝 AVITORA Frontend - Release Notes Generator');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
console.log(`バージョン: v${version}`);
console.log('');

// ============================================
// Gitコミット情報の取得
// ============================================
async function getGitInfo() {
  try {
    // 最新のタグを取得
    const { stdout: latestTag } = await execAsync('git describe --tags --abbrev=0 2>/dev/null || echo ""');
    const previousTag = latestTag.trim();

    // コミット範囲の決定
    const commitRange = previousTag ? `${previousTag}..HEAD` : 'HEAD';

    // コミット履歴の取得
    const { stdout: commits } = await execAsync(`git log ${commitRange} --pretty=format:"%h|%s|%an|%ad" --date=short`);

    return {
      previousTag: previousTag || '初回リリース',
      commits: commits.split('\n').filter(Boolean).map(line => {
        const [hash, subject, author, date] = line.split('|');
        return { hash, subject, author, date };
      })
    };
  } catch (error) {
    console.error('⚠️  Git情報の取得に失敗しました:', error.message);
    return { previousTag: '初回リリース', commits: [] };
  }
}

// ============================================
// リリースノート生成
// ============================================
async function generateReleaseNotes() {
  const gitInfo = await getGitInfo();
  const today = new Date().toISOString().split('T')[0];

  // ハイライトをリスト化
  const highlightsList = highlights
    ? highlights.split(',').map(h => `- ${h.trim()}`).join('\n')
    : '- （記入してください）';

  // 修正内容をリスト化
  const fixesList = fixes
    ? fixes.split(',').map(f => `- ${f.trim()}`).join('\n')
    : '- （記入してください）';

  // コミット履歴を整形
  const commitsList = gitInfo.commits.length > 0
    ? gitInfo.commits.map(c => `- \`${c.hash}\` ${c.subject} (${c.author}, ${c.date})`).join('\n')
    : '- コミット履歴なし';

  const releaseNotes = `# Release Notes - AVITORA Frontend v${version}

**リリース日:** ${today}
**前回バージョン:** ${gitInfo.previousTag}

---

## 🎯 概要

AVITORA Frontend v${version} をリリースしました。このリリースでは以下の主要な改善が含まれています。

---

## ✨ ハイライト

${highlightsList}

---

## 🐛 バグ修正

${fixesList}

---

## 🧪 QA結果

${qaResults || '（記入してください）'}

---

## 📊 技術スタック

| カテゴリ | 技術 |
|----------|------|
| **フレームワーク** | Next.js 15.1.6 (App Router) |
| **UI** | React 19.0.0 |
| **言語** | TypeScript 5.x |
| **スタイル** | Tailwind CSS 3.4.1 (Design System v1) |
| **状態管理** | Zustand 5.0.2 |
| **HTTP** | Axios 1.7.9 |
| **フォーム** | React Hook Form 7.54.2 + Zod 3.24.1 |

---

## 📦 含まれるコミット

${commitsList}

---

## 🚀 デプロイ手順

### 1. 環境変数の設定

\`\`\`bash
# 本番API URLを設定
NEXT_PUBLIC_API_BASE_URL=https://api.avitora.com
\`\`\`

### 2. ビルド確認

\`\`\`bash
npm run build
npm run start
\`\`\`

### 3. デプロイ実行

\`\`\`bash
# Vercel（推奨）
vercel --prod

# または Railway
railway up --environment production

# または Fly.io
fly deploy --config fly.production.toml
\`\`\`

---

## 📝 ドキュメント

- **CHANGELOG:** [CHANGELOG.md](./CHANGELOG.md)
- **デプロイガイド:** [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **QAレポート:** [reports/FINAL_QA_REPORT.md](./reports/FINAL_QA_REPORT.md)
- **UIポリッシュバックログ:** [UI_POLISH_BACKLOG.md](./UI_POLISH_BACKLOG.md)

---

## ⚠️ 既知の問題

### 低優先度（非ブロッキング）

36件のUIポリッシュアイテムが特定されています：
- 17件 - border-radius最適化
- 19件 - shadow-card追加
- 詳細: [UI_POLISH_BACKLOG.md](./UI_POLISH_BACKLOG.md)

---

## 🔄 ロールバック手順

問題が発生した場合:

\`\`\`bash
# Vercel
vercel ls --prod  # デプロイ一覧を表示
vercel rollback <deployment-url>

# Railway
railway rollback

# Fly.io
fly releases
fly releases rollback <version>
\`\`\`

---

## 📞 サポート

問題が発生した場合は以下の手順で報告してください:

1. [UI_POLISH_BACKLOG.md](./UI_POLISH_BACKLOG.md) で既知の問題を確認
2. GitHub Issueを作成（該当する場合）
3. 緊急の場合はチームに直接連絡

---

## 👥 貢献者

- **開発:** Claude Code
- **QA:** Claude Code
- **Design System:** Based on Design System v1 specification

---

**Status:** ✅ Production Ready
**Next Action:** Deploy to production

---

**生成日時:** ${new Date().toISOString()}
**生成ツール:** scripts/generate-release-notes.mjs
`;

  return releaseNotes;
}

// ============================================
// CHANGELOG更新
// ============================================
function updateChangelog(version, highlights, fixes, qaResults) {
  const today = new Date().toISOString().split('T')[0];
  const changelogPath = 'CHANGELOG.md';

  let changelog = '';
  if (existsSync(changelogPath)) {
    changelog = readFileSync(changelogPath, 'utf-8');
  } else {
    changelog = `# Changelog

All notable changes to the AVITORA Frontend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

`;
  }

  const highlightsList = highlights
    ? highlights.split(',').map(h => `- ${h.trim()}`).join('\n')
    : '';

  const fixesList = fixes
    ? fixes.split(',').map(f => `- ${f.trim()}`).join('\n')
    : '';

  const newEntry = `## [${version}] - ${today}

### Added

${highlightsList}

### Fixed

${fixesList}

### Quality Assurance

${qaResults || '- QA結果を記入してください'}

---

`;

  // ## [Unreleased] セクションの後に挿入
  if (changelog.includes('## [Unreleased]')) {
    changelog = changelog.replace(
      /## \[Unreleased\]\n\n/,
      `## [Unreleased]\n\n${newEntry}`
    );
  } else {
    // [Unreleased] セクションがない場合は先頭に追加
    const lines = changelog.split('\n');
    const insertIndex = lines.findIndex(line => line.startsWith('##'));
    if (insertIndex !== -1) {
      lines.splice(insertIndex, 0, newEntry);
      changelog = lines.join('\n');
    } else {
      changelog += '\n' + newEntry;
    }
  }

  return changelog;
}

// ============================================
// メイン処理
// ============================================
async function main() {
  try {
    // リリースノート生成
    console.log('📝 リリースノートを生成中...');
    const releaseNotes = await generateReleaseNotes();
    const releaseNotesPath = `RELEASE_NOTES_${version}.md`;
    writeFileSync(releaseNotesPath, releaseNotes);
    console.log(`✅ リリースノートを作成: ${releaseNotesPath}`);
    console.log('');

    // CHANGELOG更新
    console.log('📝 CHANGELOGを更新中...');
    const updatedChangelog = updateChangelog(version, highlights, fixes, qaResults);
    writeFileSync('CHANGELOG.md', updatedChangelog);
    console.log('✅ CHANGELOGを更新: CHANGELOG.md');
    console.log('');

    // サマリー表示
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ リリースノート生成完了');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('');
    console.log('生成ファイル:');
    console.log(`  - ${releaseNotesPath}`);
    console.log('  - CHANGELOG.md (更新)');
    console.log('');
    console.log('次のステップ:');
    console.log('  1. リリースノートを確認・編集');
    console.log('  2. git add CHANGELOG.md ' + releaseNotesPath);
    console.log(`  3. git commit -m "docs: add release notes for v${version}"`);
    console.log('  4. git push');
    console.log('');
  } catch (error) {
    console.error('❌ エラー:', error.message);
    process.exit(1);
  }
}

main();
