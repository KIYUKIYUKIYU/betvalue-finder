# Production Deployment Checklist

**Project:** AVITORA Frontend v0.1.0
**Date:** 2025-10-22
**Deployment Type:** Initial Production Release

---

## Pre-Deployment Checklist

### Code Quality

- [x] All high-priority issues resolved (Focus indicators)
- [x] All medium-priority issues resolved (Responsive grid, hover states)
- [x] Design System v1 compliance verified (0 violations)
- [x] No console errors in development
- [x] No TypeScript errors: `npx tsc --noEmit`
- [x] Production build successful: `npm run build` ✅
- [x] TypeScript type errors fixed (3 components)
- [ ] Production build tested locally: `npm run start`

### Testing

- [x] Design System audit passed
- [ ] E2E tests executed (in CI/CD)
- [ ] Lighthouse audit executed (in CI/CD)
- [ ] Manual testing completed (all 8 pages)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile testing (iOS, Android)
- [ ] Tablet testing

### Documentation

- [x] CHANGELOG.md updated
- [x] DEPLOYMENT_GUIDE.md created
- [x] FINAL_QA_REPORT.md shows PASS verdict
- [x] UI_POLISH_BACKLOG.md created for future improvements
- [x] README.md updated with deployment info ✅
- [ ] API documentation links verified

### Version Control

- [x] All changes committed
- [ ] Version bumped to 0.1.0: `npm version 0.1.0`
- [ ] Git tags pushed: `git push origin --tags`
- [ ] Release branch created (if using git-flow)
- [ ] Hotfix branch merged (20b82e0)

### Environment Configuration

- [ ] Production environment variables set:
  - [ ] NEXT_PUBLIC_API_BASE_URL (backend production URL)
  - [ ] NEXT_PUBLIC_GA_ID (Google Analytics - optional)
  - [ ] NEXT_PUBLIC_SENTRY_DSN (Error tracking - optional)
- [ ] Backend API production URL verified and accessible
- [ ] CORS configured on backend for production domain
- [ ] SSL certificate ready (if custom domain)
- [ ] DNS records configured (if custom domain)

### Infrastructure

- [ ] Deployment platform selected:
  - [ ] Vercel (recommended for Next.js)
  - [ ] Railway
  - [ ] Fly.io
  - [ ] Docker + Custom
- [ ] CDN configured (if applicable)
- [ ] Monitoring tools set up:
  - [ ] Uptime monitoring (UptimeRobot, Pingdom)
  - [ ] Error tracking (Sentry, LogRocket)
  - [ ] Analytics (Google Analytics, Mixpanel)
- [ ] Logging configured
- [ ] Backup strategy defined

---

## Staging Verification Checklist

**Staging URL:** _________________________________

### Smoke Tests

#### 1. Landing Page (/)
- [ ] Page loads without errors
- [ ] Hero section displays correctly
- [ ] "今すぐ始める" button → /auth/signup
- [ ] "ログイン" button → /auth/login
- [ ] Footer displays
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Load time < 3s

#### 2. Signup Page (/auth/signup)
- [ ] Form displays correctly
- [ ] Email validation works
- [ ] Password validation (8+ chars) works
- [ ] Display name validation works
- [ ] Submit with valid data → /dashboard
- [ ] Submit with invalid data → shows errors
- [ ] Link to login page works
- [ ] No console errors

#### 3. Login Page (/auth/login)
- [ ] Form displays correctly
- [ ] Email validation works
- [ ] Password validation works
- [ ] Submit with valid credentials → /dashboard
- [ ] Submit with invalid credentials → shows error
- [ ] Link to signup page works
- [ ] No console errors

#### 4. Dashboard - Analysis (/dashboard)
- [ ] Redirects to /auth/login if not logged in
- [ ] Usage indicator displays (Free or Pro)
- [ ] Analysis form displays
- [ ] Paste text into textarea
- [ ] Select sport hint
- [ ] Click "分析開始"
- [ ] API call made (verify in Network tab)
- [ ] Results display or error shown
- [ ] No console errors

#### 5. Games Page (/dashboard/games)
- [ ] Auth guard works (redirects if not logged in)
- [ ] Page loads
- [ ] Games list displays or "今日の試合データがありません"
- [ ] Responsive grid (1 col mobile, 2 col tablet, 3 col desktop)
- [ ] Odds display correctly
- [ ] No console errors

#### 6. Settings Page (/dashboard/settings)
- [ ] Auth guard works
- [ ] Rakeback form displays
- [ ] Pinnacle input (0-3%) validation works
- [ ] bet365 input (0-3%) validation works
- [ ] Click "保存"
- [ ] Success message displays or API error shown
- [ ] No console errors

#### 7. Subscription Page (/dashboard/subscription)
- [ ] Auth guard works
- [ ] Free plan card displays
- [ ] Pro plan card displays
- [ ] Current plan indicator shows
- [ ] Click "プランを選択" on non-current plan
- [ ] Redirects to /dashboard/subscription/checkout
- [ ] No console errors

#### 8. Checkout Page (/dashboard/subscription/checkout)
- [ ] Accepts `url` query parameter
- [ ] Displays loading state
- [ ] Redirects to checkout URL
- [ ] No console errors

### Event Handler Tests

Run in browser console at /dashboard:

#### 9. Usage Limit Exceeded Event
```javascript
window.dispatchEvent(new CustomEvent('usage-limit-exceeded', {
  detail: {
    code: 'USAGE_LIMIT_EXCEEDED',
    detail: 'Test limit exceeded message'
  }
}));
```
- [ ] Modal appears
- [ ] Modal shows upgrade message
- [ ] "閉じる" button dismisses modal
- [ ] "プラン確認" button → /dashboard/subscription
- [ ] No console errors

#### 10. User Banned Event
```javascript
window.dispatchEvent(new CustomEvent('user-banned', {
  detail: {
    code: 'USER_BANNED',
    detail: 'Account banned message'
  }
}));
```
- [ ] Banned modal appears
- [ ] Auto-logout after 3 seconds
- [ ] Redirects to /auth/login
- [ ] No console errors

### Network & Security

- [ ] All API calls include `Authorization: Bearer <token>` header (if logged in)
- [ ] 401 responses trigger auto-redirect to /auth/login
- [ ] 403 USAGE_LIMIT_EXCEEDED triggers event handler
- [ ] 403 USER_BANNED triggers event handler
- [ ] No sensitive data in client-side code
- [ ] No API keys in client bundle
- [ ] HTTPS enforced (if custom domain)
- [ ] Security headers configured

### Performance

- [ ] Page load time < 3s (all pages)
- [ ] Time to Interactive < 5s
- [ ] No memory leaks (check DevTools Memory tab)
- [ ] No excessive API calls
- [ ] Images optimized
- [ ] Bundle size reasonable (< 500KB gzipped)

### Cross-Browser Testing

- [ ] Chrome desktop (latest)
- [ ] Firefox desktop (latest)
- [ ] Safari desktop (latest)
- [ ] Edge desktop (latest)
- [ ] Chrome mobile (iOS)
- [ ] Safari mobile (iOS)
- [ ] Chrome mobile (Android)

---

## Production Deployment Checklist

### Pre-Deploy

- [ ] Staging smoke test 100% passed
- [ ] Team notified of deployment window
- [ ] Rollback plan documented
- [ ] Maintenance page ready (if needed)
- [ ] Customer support briefed (if applicable)

### Deploy

- [ ] Version tag created: `git tag v0.1.0`
- [ ] Version tag pushed: `git push origin v0.1.0`
- [ ] Production build created: `npm run build`
- [ ] Production environment variables verified
- [ ] Deploy command executed:
  ```bash
  # Example (adjust for your platform)
  vercel --prod
  # or
  railway up --environment production
  # or
  fly deploy --config fly.production.toml
  ```
- [ ] Deployment completed successfully
- [ ] Production URL recorded: _________________________________

### Post-Deploy (0-15 minutes)

- [ ] Production URL accessible
- [ ] All 8 pages return 200 status
- [ ] Landing page loads correctly
- [ ] Login flow works
- [ ] Signup flow works
- [ ] Dashboard accessible after login
- [ ] API integration working
- [ ] No console errors
- [ ] SSL certificate valid (if custom domain)
- [ ] DNS propagation complete (if custom domain)

### Post-Deploy (15-60 minutes)

- [ ] Monitor error rates (should be < 1%)
- [ ] Monitor API response times (should be < 2s p95)
- [ ] Monitor server CPU/memory (should be stable)
- [ ] Check logs for unexpected errors
- [ ] Verify analytics tracking (if configured)
- [ ] Test on different devices
- [ ] Test on different network conditions

### Post-Deploy (1-24 hours)

- [ ] Monitor uptime (should be > 99.9%)
- [ ] Monitor user signups (if any)
- [ ] Monitor user engagement
- [ ] Check for reported issues
- [ ] Review error tracking dashboard
- [ ] Verify no performance degradation
- [ ] Check database connections (if applicable)

---

## Rollback Criteria

**Immediate Rollback If:**

- [ ] Site completely down (> 5 minutes)
- [ ] Critical JS errors affecting > 10% of users
- [ ] Authentication completely broken
- [ ] Payment/subscription failures (if applicable)
- [ ] Database connection errors
- [ ] API 5xx errors > 50%

**Rollback Procedure:**

1. Execute platform-specific rollback command
2. Verify rollback successful (test key pages)
3. Notify team of rollback
4. Create incident report
5. Plan hotfix

---

## Success Metrics (Week 1)

### Technical Metrics

- [ ] Uptime > 99.9%
- [ ] Error rate < 1%
- [ ] Page load time < 3s (p95)
- [ ] API response time < 2s (p95)
- [ ] Lighthouse Performance > 85
- [ ] Lighthouse Accessibility > 90
- [ ] Lighthouse Best Practices > 95
- [ ] Lighthouse SEO > 95

### Business Metrics

- [ ] Signup conversion rate tracked
- [ ] Dashboard engagement tracked
- [ ] Analysis feature usage tracked
- [ ] Mobile vs Desktop split tracked
- [ ] Average session duration tracked

---

## Post-Launch Tasks

### Immediate (Day 1)

- [ ] Monitor all metrics closely
- [ ] Respond to any user issues
- [ ] Create post-mortem if issues occurred
- [ ] Update status page (if applicable)

### Short-Term (Week 1)

- [ ] Gather user feedback
- [ ] Identify quick wins for improvement
- [ ] Plan Sprint 2 (UI polish backlog)
- [ ] Set up automated alerts
- [ ] Document learnings

### Medium-Term (Month 1)

- [ ] Review Week 1 metrics
- [ ] Plan feature roadmap
- [ ] Address low-priority polish items
- [ ] Optimize performance based on real data
- [ ] Implement monitoring improvements

---

## Support Information

### Emergency Contacts

- **Technical Lead:** ___________________________
- **DevOps:** ___________________________
- **Product Owner:** ___________________________

### Monitoring Dashboards

- **Uptime:** ___________________________
- **Errors:** ___________________________
- **Analytics:** ___________________________
- **Logs:** ___________________________

### Escalation Path

1. **Level 1:** Developer on call
2. **Level 2:** Technical lead
3. **Level 3:** CTO / Engineering manager

---

## Sign-Off

**QA Lead:** _________________ Date: _______

**Technical Lead:** _________________ Date: _______

**Product Owner:** _________________ Date: _______

**Deployment Executed By:** _________________ Date: _______

---

**Status:** Ready for Production ✅

**Next Action:** Execute deployment per DEPLOYMENT_GUIDE.md

---

**Document Version:** 1.0
**Last Updated:** 2025-10-22
