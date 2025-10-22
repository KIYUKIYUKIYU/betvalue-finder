#!/usr/bin/env node

/**
 * ============================================
 * AVITORA Frontend - UI Polish Ticket Generator
 * ============================================
 * 目的: UI_POLISH_BACKLOG.md からGitHub Issueテンプレートを生成
 * 実行: node scripts/create-ui-polish-tickets.mjs
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🎫 AVITORA Frontend - UI Polish Ticket Generator');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');

// ============================================
// UIポリッシュバックログの定義
// ============================================
const epics = [
  {
    id: 1,
    name: 'Shadow Consistency',
    description: 'Add shadow-card to all elevated components for depth perception',
    effort: '30 minutes',
    priority: 'Low',
    sprint: 2,
    tasks: [
      'Add shadow-card to usage-limit-exceeded modal',
      'Add shadow-card to user-banned modal',
      'Add shadow-card to elevated card components',
      'Verify shadow consistency in light mode',
      'Document shadow usage in design system'
    ],
    files: [
      'src/app/dashboard/layout.tsx (2 modals)',
      'src/components/dashboard/* (various cards)'
    ],
    acceptanceCriteria: [
      'All modal overlays have shadow-card',
      'All card-like components have consistent elevation',
      'Visual hierarchy clear through shadows'
    ]
  },
  {
    id: 2,
    name: 'Border Radius Upgrade',
    description: 'Upgrade border-radius from rounded-lg to rounded-2xl or rounded-3xl for card aesthetics',
    effort: '30 minutes',
    priority: 'Low',
    sprint: 2,
    tasks: [
      'Audit all rounded-lg usage',
      'Upgrade to rounded-2xl for cards',
      'Upgrade to rounded-3xl for hero sections',
      'Test responsive behavior',
      'Update design system documentation'
    ],
    files: [
      'Multiple Card component instances',
      'Modal dialogs',
      'Input wrappers'
    ],
    acceptanceCriteria: [
      'All card-like elements use rounded-2xl or rounded-3xl',
      'Modals use rounded-2xl',
      'Visual consistency across all components'
    ]
  },
  {
    id: 3,
    name: 'Spacing Standardization',
    description: 'Ensure consistent spacing across all forms and layouts',
    effort: '2 hours',
    priority: 'Low',
    sprint: 3,
    tasks: [
      'Audit all gap-* classes',
      'Create spacing matrix (component type → gap value)',
      'Apply consistent spacing to forms',
      'Apply consistent spacing to cards',
      'Test on mobile/tablet/desktop'
    ],
    files: [
      'All component files with gap-* usage'
    ],
    acceptanceCriteria: [
      'Consistent gap values across similar component types',
      'Spacing matrix documented in design system',
      'No spacing inconsistencies on any viewport'
    ]
  },
  {
    id: 4,
    name: 'Hover/Active State Consistency',
    description: 'All interactive elements have consistent hover/active states',
    effort: '1.5 hours',
    priority: 'Low',
    sprint: 3,
    tasks: [
      'Audit all interactive elements',
      'Define hover state patterns by element type',
      'Apply consistent transitions',
      'Add active states where missing',
      'Test keyboard navigation'
    ],
    files: [
      'All components with buttons/links'
    ],
    acceptanceCriteria: [
      'All buttons have hover:opacity-90 or hover:bg-*-600',
      'All links have hover:underline or hover:opacity-80',
      'Consistent transition-colors or transition-opacity',
      'Duration: 150ms (fast) or 300ms (smooth)'
    ]
  },
  {
    id: 5,
    name: 'Responsive Table Improvements',
    description: 'Improve table layouts on mobile/tablet',
    effort: '2 hours',
    priority: 'Low',
    sprint: 4,
    tasks: [
      'Test AnalysisResult table on various viewports',
      'Implement horizontal scroll for mobile',
      'Consider card layout alternative',
      'Add column visibility controls',
      'Test with real data'
    ],
    files: [
      'src/components/dashboard/AnalysisResult.tsx'
    ],
    acceptanceCriteria: [
      'Tables scroll horizontally on mobile',
      'Or: Convert to card layout on mobile',
      'Column hiding on tablet (if applicable)'
    ]
  }
];

// ============================================
// GitHub Issue テンプレート生成
// ============================================
function generateIssueTemplate(epic) {
  const tasksList = epic.tasks.map(task => `- [ ] ${task}`).join('\n');
  const acceptanceCriteriaList = epic.acceptanceCriteria.map(criterion => `- [ ] ${criterion}`).join('\n');
  const filesList = epic.files.map(file => `- ${file}`).join('\n');

  return `---
name: UI Polish - ${epic.name}
about: ${epic.description}
title: '[UI Polish] Epic ${epic.id}: ${epic.name}'
labels: 'ui-polish, low-priority, sprint-${epic.sprint}'
assignees: ''
---

## 概要

${epic.description}

**優先度:** ${epic.priority}
**工数:** ${epic.effort}
**スプリント:** ${epic.sprint}

---

## タスク

${tasksList}

---

## 受け入れ基準

${acceptanceCriteriaList}

---

## 影響するファイル

${filesList}

---

## テストチェックリスト

- [ ] Chrome desktop (latest)
- [ ] Firefox desktop (latest)
- [ ] Safari desktop (latest)
- [ ] Mobile (iOS)
- [ ] Mobile (Android)
- [ ] Tablet

---

## スクリーンショット

**Before:**
（スクリーンショットを追加）

**After:**
（スクリーンショットを追加）

---

## 関連

- Related to: UI_POLISH_BACKLOG.md Epic ${epic.id}
- Sprint: ${epic.sprint}
- Effort: ${epic.effort}

---

**生成日:** ${new Date().toISOString().split('T')[0]}
**生成ツール:** scripts/create-ui-polish-tickets.mjs
`;
}

// ============================================
// メイン処理
// ============================================
function main() {
  try {
    // 出力ディレクトリ作成
    const ticketsDir = '.github/ISSUE_TEMPLATE/ui-polish';
    if (!existsSync('.github')) mkdirSync('.github');
    if (!existsSync('.github/ISSUE_TEMPLATE')) mkdirSync('.github/ISSUE_TEMPLATE');
    if (!existsSync(ticketsDir)) mkdirSync(ticketsDir, { recursive: true });

    console.log(`📁 出力ディレクトリ: ${ticketsDir}`);
    console.log('');

    // Epicごとにテンプレート生成
    epics.forEach(epic => {
      const template = generateIssueTemplate(epic);
      const filename = `${ticketsDir}/epic-${epic.id}-${epic.name.toLowerCase().replace(/\s+/g, '-')}.md`;

      writeFileSync(filename, template);
      console.log(`✅ Epic ${epic.id}: ${epic.name}`);
      console.log(`   ファイル: ${filename}`);
      console.log(`   工数: ${epic.effort} | スプリント: ${epic.sprint}`);
      console.log('');
    });

    // サマリーMarkdown生成
    const summaryPath = '.github/ISSUE_TEMPLATE/ui-polish/README.md';
    const epicsList = epics.map(epic =>
      `### Epic ${epic.id}: ${epic.name}

- **優先度:** ${epic.priority}
- **工数:** ${epic.effort}
- **スプリント:** ${epic.sprint}
- **タスク数:** ${epic.tasks.length}
- **テンプレート:** [epic-${epic.id}-${epic.name.toLowerCase().replace(/\s+/g, '-')}.md](./epic-${epic.id}-${epic.name.toLowerCase().replace(/\s+/g, '-')}.md)

${epic.description}
`
    ).join('\n\n---\n\n');

    const summary = `# UI Polish Issues - AVITORA Frontend

このディレクトリには、UIポリッシュのためのGitHub Issueテンプレートが含まれています。

## 概要

**総Epic数:** ${epics.length}
**総工数:** ${epics.reduce((acc, epic) => {
  const hours = parseFloat(epic.effort.match(/[\d.]+/)?.[0] || 0);
  return acc + (epic.effort.includes('hour') ? hours : hours / 60);
}, 0).toFixed(1)} 時間
**対象スプリント:** Sprint ${Math.min(...epics.map(e => e.sprint))} - ${Math.max(...epics.map(e => e.sprint))}

---

## Epics

${epicsList}

---

## 使用方法

### GitHub Web UIで作成

1. GitHubリポジトリの「Issues」タブを開く
2. 「New Issue」をクリック
3. テンプレートから該当するEpicを選択
4. タイトルとラベルが自動入力されるので確認
5. 必要に応じて編集
6. 「Submit new issue」をクリック

### CLIで一括作成（GitHub CLI）

\`\`\`bash
# Epic 1 - Shadow Consistency
gh issue create --template .github/ISSUE_TEMPLATE/ui-polish/epic-1-shadow-consistency.md

# Epic 2 - Border Radius Upgrade
gh issue create --template .github/ISSUE_TEMPLATE/ui-polish/epic-2-border-radius-upgrade.md

# 全Epic一括作成
for file in .github/ISSUE_TEMPLATE/ui-polish/epic-*.md; do
  gh issue create --template "$file"
done
\`\`\`

---

## スプリント別推奨順序

### Sprint 2 (Week 1-2) - Quick Wins
- Epic 1: Shadow Consistency (30min)
- Epic 2: Border Radius Upgrade (30min)
- **合計:** 1時間

### Sprint 3 (Week 3-4) - Interaction Improvements
- Epic 3: Spacing Standardization (2h)
- Epic 4: Hover/Active State Consistency (1.5h)
- **合計:** 3.5時間

### Sprint 4 (Week 5-6) - Mobile Optimization
- Epic 5: Responsive Table Improvements (2h)
- **合計:** 2時間

---

**生成日:** ${new Date().toISOString().split('T')[0]}
**ソース:** UI_POLISH_BACKLOG.md
**生成ツール:** scripts/create-ui-polish-tickets.mjs
`;

    writeFileSync(summaryPath, summary);
    console.log(`✅ サマリー作成: ${summaryPath}`);
    console.log('');

    // 完了メッセージ
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ UIポリッシュチケット生成完了');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('');
    console.log(`生成件数: ${epics.length} Epic`);
    console.log(`出力先: ${ticketsDir}/`);
    console.log('');
    console.log('次のステップ:');
    console.log('  1. .github/ISSUE_TEMPLATE/ui-polish/ を確認');
    console.log('  2. GitHubにコミット＆プッシュ');
    console.log('  3. GitHub Web UIまたはCLIでIssue作成');
    console.log('');
    console.log('一括作成（GitHub CLI）:');
    console.log('  gh issue create --template .github/ISSUE_TEMPLATE/ui-polish/epic-1-shadow-consistency.md');
    console.log('');

  } catch (error) {
    console.error('❌ エラー:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();
