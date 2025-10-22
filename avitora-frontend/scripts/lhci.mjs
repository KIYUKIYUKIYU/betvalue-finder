#!/usr/bin/env node
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BASE_URL = 'http://localhost:3000';
const PAGES = [
  { path: '/', name: 'Landing Page' },
  { path: '/auth/signup', name: 'Signup Page' },
  { path: '/dashboard', name: 'Dashboard (Auth Required)' },
  { path: '/dashboard/games', name: 'Games Page' },
  { path: '/dashboard/settings', name: 'Settings Page' },
  { path: '/dashboard/subscription', name: 'Subscription Page' },
];

const THRESHOLDS = {
  performance: 85,
  accessibility: 90,
  'best-practices': 95,
  seo: 95,
};

async function runLighthouse(url, name) {
  console.log(`\n🔍 Auditing: ${name} (${url})`);

  let chrome;
  try {
    chrome = await chromeLauncher.launch({ chromeFlags: ['--headless'] });

    const options = {
      logLevel: 'error',
      output: 'html',
      onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      port: chrome.port,
    };

    const runnerResult = await lighthouse(url, options);

    // Save HTML report
    const reportsDir = path.join(process.cwd(), 'reports', 'LIGHTHOUSE_REPORT');
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    const sanitizedName = name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const reportPath = path.join(reportsDir, `${sanitizedName}.html`);
    fs.writeFileSync(reportPath, runnerResult.report);

    // Extract scores
    const categories = runnerResult.lhr.categories;
    const scores = {
      performance: Math.round(categories.performance.score * 100),
      accessibility: Math.round(categories.accessibility.score * 100),
      'best-practices': Math.round(categories['best-practices'].score * 100),
      seo: Math.round(categories.seo.score * 100),
    };

    // Extract top 3 improvements
    const audits = runnerResult.lhr.audits;
    const improvements = Object.values(audits)
      .filter(audit => audit.score !== null && audit.score < 1 && audit.details)
      .sort((a, b) => {
        const impactOrder = { high: 0, medium: 1, low: 2 };
        return (impactOrder[a.details.type] || 3) - (impactOrder[b.details.type] || 3);
      })
      .slice(0, 3)
      .map(audit => ({
        title: audit.title,
        description: audit.description,
        score: Math.round((audit.score || 0) * 100),
      }));

    return {
      name,
      url,
      scores,
      improvements,
      reportPath: path.relative(process.cwd(), reportPath),
    };
  } catch (error) {
    console.error(`Error auditing ${name}:`, error.message);
    return {
      name,
      url,
      error: error.message,
    };
  } finally {
    if (chrome) {
      await chrome.kill();
    }
  }
}

async function main() {
  console.log('🚀 Starting Lighthouse CI\n');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Pages: ${PAGES.length}\n`);

  const results = [];

  for (const page of PAGES) {
    const result = await runLighthouse(`${BASE_URL}${page.path}`, page.name);
    results.push(result);

    if (!result.error) {
      console.log(`  Performance: ${result.scores.performance}`);
      console.log(`  Accessibility: ${result.scores.accessibility}`);
      console.log(`  Best Practices: ${result.scores['best-practices']}`);
      console.log(`  SEO: ${result.scores.seo}`);
    }
  }

  // Generate summary report
  let summary = '# Lighthouse CI Report\n\n';
  summary += `**Date:** ${new Date().toISOString()}\n`;
  summary += `**Base URL:** ${BASE_URL}\n`;
  summary += `**Pages Audited:** ${PAGES.length}\n\n`;

  // Overall status
  const allPassed = results.every(r => {
    if (r.error) return false;
    return (
      r.scores.performance >= THRESHOLDS.performance &&
      r.scores.accessibility >= THRESHOLDS.accessibility &&
      r.scores['best-practices'] >= THRESHOLDS['best-practices'] &&
      r.scores.seo >= THRESHOLDS.seo
    );
  });

  summary += `## Status: ${allPassed ? '✅ PASSED' : '⚠️ NEEDS IMPROVEMENT'}\n\n`;

  // Thresholds
  summary += '## Thresholds\n\n';
  summary += '| Category | Threshold |\n';
  summary += '|----------|----------|\n';
  summary += `| Performance | ${THRESHOLDS.performance} |\n`;
  summary += `| Accessibility | ${THRESHOLDS.accessibility} |\n`;
  summary += `| Best Practices | ${THRESHOLDS['best-practices']} |\n`;
  summary += `| SEO | ${THRESHOLDS.seo} |\n\n`;

  // Results by page
  summary += '## Results by Page\n\n';

  results.forEach(result => {
    summary += `### ${result.name}\n\n`;
    summary += `**URL:** ${result.url}\n\n`;

    if (result.error) {
      summary += `❌ **Error:** ${result.error}\n\n`;
      return;
    }

    summary += '| Category | Score | Status |\n';
    summary += '|----------|-------|--------|\n';

    Object.entries(result.scores).forEach(([category, score]) => {
      const threshold = THRESHOLDS[category];
      const status = score >= threshold ? '✅' : '❌';
      const categoryName = category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' ');
      summary += `| ${categoryName} | ${score} | ${status} |\n`;
    });

    summary += '\n';

    if (result.improvements && result.improvements.length > 0) {
      summary += '**Top Improvements:**\n\n';
      result.improvements.forEach((improvement, idx) => {
        summary += `${idx + 1}. **${improvement.title}** (Score: ${improvement.score})\n`;
        summary += `   - ${improvement.description}\n\n`;
      });
    }

    summary += `**Full Report:** [${result.reportPath}](../${result.reportPath})\n\n`;
  });

  // Recommendations
  summary += '## Recommendations\n\n';

  const failedPages = results.filter(r => {
    if (r.error) return true;
    return Object.entries(r.scores).some(([category, score]) => score < THRESHOLDS[category]);
  });

  if (failedPages.length === 0) {
    summary += 'All pages meet the performance thresholds. Great work!\n\n';
    summary += '**Optional Improvements:**\n';
    summary += '- Consider implementing service workers for offline support\n';
    summary += '- Add resource hints (preconnect, prefetch) for external resources\n';
    summary += '- Implement lazy loading for below-the-fold images\n';
  } else {
    summary += `${failedPages.length} page(s) need improvement:\n\n`;
    failedPages.forEach(page => {
      summary += `- **${page.name}**\n`;
      if (page.error) {
        summary += `  - Error: ${page.error}\n`;
      } else {
        Object.entries(page.scores).forEach(([category, score]) => {
          if (score < THRESHOLDS[category]) {
            summary += `  - ${category}: ${score} (threshold: ${THRESHOLDS[category]})\n`;
          }
        });
      }
    });
  }

  // Save summary
  const summaryPath = path.join(process.cwd(), 'reports', 'LIGHTHOUSE_SUMMARY.md');
  fs.writeFileSync(summaryPath, summary);

  console.log(`\n✅ Lighthouse CI complete`);
  console.log(`📊 Summary: reports/LIGHTHOUSE_SUMMARY.md`);
  console.log(`📁 Reports: reports/LIGHTHOUSE_REPORT/\n`);

  process.exit(allPassed ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
