# BizSimAI E2E Test Plan — RC3/RC5/RC6 + Error Handling
## Date: 2026-07-15
## Device: iPhone 17 Pro Max (96BEAEB2-7A4C-5E79-AD11-D8718B2CA8D5)
## Backend: EC2 18.215.180.58:80 | Session: BIZ-AEHS

---

## PHASE 1: Authentication Permutations (Login/Logout)

### Test 1.1: Professor Login — Success
- **Action**: Open app → Enter professor / [REDACTED] → Login
- **Expected**: Dashboard loads, scheduler starts (token refresh active)
- **Verify**: No error messages, can navigate to sessions

### Test 1.2: Professor Login — Wrong Password (401)
- **Action**: Enter professor / wrongpassword → Login
- **Expected**: "Incorrect username or password. Please try again." (NOT raw 401)
- **Verify**: UserFriendlyError mapping works

### Test 1.3: Professor Login — Non-existent User (404)
- **Action**: Enter "nonexistent" / [REDACTED] → Login
- **Expected**: "Account not found. Please check your username or contact support." (NOT raw 404)
- **Verify**: UserFriendlyError mapping works

### Test 1.4: Student Login — Success (STU001)
- **Action**: Open app → Enter STU001 / [REDACTED] → Login
- **Expected**: Student dashboard loads, scheduler starts
- **Verify**: Can see session BIZ-AEHS

### Test 1.5: Student Login — Wrong Password (401)
- **Action**: Enter STU001 / wrongpassword → Login
- **Expected**: "Incorrect username or password. Please try again."

### Test 1.6: Student Login — Non-existent User (404)
- **Action**: Enter STU999 / [REDACTED] → Login
- **Expected**: "Account not found. Please check your username or contact support."

### Test 1.7: Rate Limit Trigger (429)
- **Action**: Enter wrong password 5+ times rapidly
- **Expected**: "Too many login attempts. Please wait a few minutes before trying again." (NOT raw 429)
- **Verify**: Rate limiter DEBUG mode is active (should NOT trigger on EC2 with DEBUG=true)

### Test 1.8: Logout → Re-login
- **Action**: Login as professor → Logout → Login again
- **Expected**: Clean logout, clean re-login, no stale token errors

---

## PHASE 2: Session Operations (Professor)

### Test 2.1: Create Session
- **Action**: Professor dashboard → Create new session (or use BIZ-AEHS)
- **Expected**: Session created, no errors

### Test 2.2: View Sessions List
- **Action**: Professor dashboard → View sessions
- **Expected**: BIZ-AEHS appears in list

### Test 2.3: View Session Results
- **Action**: Open BIZ-AEHS → View results/leaderboard
- **Expected**: Data loads, no errors

---

## PHASE 3: Session Operations (Student)

### Test 3.1: Student Join Session
- **Action**: Login as STU001 → Find BIZ-AEHS → Join
- **Expected**: Successfully joins, sees team dashboard

### Test 3.2: Student Submit Decision
- **Action**: Make a decision → Submit
- **Expected**: Submission succeeds, no errors

### Test 3.3: Student View Results
- **Action**: After round completes → View results
- **Expected**: Results display correctly

---

## PHASE 4: RC3 — JWT Expiry & Refresh

### Test 4.1: Proactive Token Refresh (Token < 2 min expiry)
- **Action**: Login → Wait for token to approach expiry (or manually test via console)
- **Expected**: Token refreshes silently, user stays logged in
- **Verify**: No logout during active session

### Test 4.2: Session Restore After App Restart
- **Action**: Login → Close app completely → Reopen app
- **Expected**: Auto-restores session, no re-login required
- **Verify**: Scheduler starts on restore

### Test 4.3: Token Refresh Fails (Refresh Token Expired)
- **Action**: Clear refresh token from keychain → Try any authenticated action
- **Expected**: Forces logout, shows "Session expired. Please log in again."

---

## PHASE 5: RC5 — Retry/Backoff (Transient Errors)

### Test 5.1: Network Timeout Recovery
- **Action**: Login → Toggle airplane mode ON → Wait 5s → Toggle OFF → Try action
- **Expected**: Request retries with backoff (2s, 4s, 8s), eventually succeeds

### Test 5.2: Server Error (502/503/504) Recovery
- **Action**: Simulate server error (if possible via backend toggle) → Try action
- **Expected**: Retries 3 times with exponential backoff, then fails gracefully

### Test 5.3: Client Error (401/404/409) — NO Retry
- **Action**: Login with wrong password → Should NOT retry (client error)
- **Expected**: Fails immediately, no backoff delay

---

## PHASE 6: RC6 — Keychain Race Conditions

### Test 6.1: Rapid Login Attempts
- **Action**: Login → Quick logout → Quick login again
- **Expected**: No keychain corruption, clean state each time

### Test 6.2: Login During Token Refresh
- **Action**: Login → Wait for proactive refresh → Try to submit decision during refresh
- **Expected**: No race condition, token swap is atomic

### Test 6.3: App Crash During Token Persistence
- **Action**: Login → Force quit app mid-operation → Reopen
- **Expected**: Session restores cleanly, no corrupted tokens

---

## PHASE 7: Error Handling UX (All Screens)

### Test 7.1: All Error Messages Are User-Friendly
- **Action**: Trigger every error condition across all screens
- **Expected**: NO raw HTTP codes (401, 404, 429, 500, etc.) visible to user
- **Verify**: All messages use UserFriendlyError mapping

### Test 7.2: Retry Buttons Always Work
- **Action**: Trigger error → Tap retry
- **Expected**: Retry succeeds or shows appropriate message

---

## PHASE 8: Multi-Student Cohort Test (20 Students)

### Test 8.1: All 20 Students Login
- **Action**: Login STU001-STU020 sequentially
- **Expected**: All log in successfully, no rate limiting issues

### Test 8.2: All 20 Students Join Session
- **Action**: All students join BIZ-AEHS
- **Expected**: All join successfully

### Test 8.3: All 20 Students Submit Decisions
- **Action**: Professor advances round → All students submit
- **Expected**: All submissions succeed

---

## Execution Order
1. Build & install (in progress)
2. Phase 1-3: Basic auth + session operations
3. Phase 4-6: RC3/RC5/RC6 specific tests
4. Phase 7: Error handling UX audit
5. Phase 8: Full 20-student cohort test
6. Fix any bugs found → Rebuild → Retest

## Success Criteria
- All 8 phases pass with zero crashes
- Zero raw HTTP error codes visible to user
- JWT refresh works silently (no unexpected logouts)
- Network retries work transparently
- Keychain never corrupted across rapid operations
