# BizSimAI Comprehensive Test Plan

## Overview
This plan covers end-to-end testing of the BizSimAI business simulation platform from both **Professor** and **Student** perspectives. Testing is divided into 6 phases with full permutation coverage.

---

## Phase 1: Authentication & Account Management
**Goal:** Verify all auth flows work correctly for both roles.

### 1.1 Professor Authentication
| Test | Steps | Expected |
|------|-------|----------|
| P1-01: Professor Login (Password) | POST `/api/auth/login` with `{"username":"prof1","password":"Prof@2026X","provider":"password"}` | 200 OK, returns token with professor role |
| P1-02: Professor Login (Apple) | Sign In with Apple as professor | 200 OK, token with professor role |
| P1-03: Professor MFA | Login with MFA enabled, enter code | 200 OK after MFA verification |
| P1-04: Professor Pre-Create | POST `/api/professor/pre-create` with new credentials | 201 Created, professor account created |
| P1-05: Invalid Professor Login | Wrong password | 401 Unauthorized |
| P1-06: Non-existent Professor | Login with unregistered username | 401 Unauthorized |

### 1.2 Student Authentication
| Test | Steps | Expected |
|------|-------|----------|
| P1-07: Student Login (Password) | POST `/api/auth/login` with `{"username":"stu1","password":"Stu1@2026X","provider":"password"}` | 200 OK, returns token with student role |
| P1-08: Student Login (Apple) | Sign In with Apple as student | 200 OK, token with student role |
| P1-09: Student MFA | Login with MFA enabled, enter code | 200 OK after MFA verification |
| P1-10: Student Register | POST `/api/auth/register` with student_id, name, password | 201 Created, account created |
| P1-11: Student Register Duplicate | Register with existing student_id | 409 Conflict |
| P1-12: Invalid Student Login | Wrong password | 401 Unauthorized |
| P1-13: iOS App Login Flow | Open app → Login screen → Enter credentials → Submit | Navigate to session list/dashboard |
| P1-14: iOS Apple Sign-In | Tap "Sign in with Apple" → Authenticate → Authorize | Login successful, navigate to session list |
| P1-15: iOS MFA Flow | Login → Enter MFA code → Submit | Login successful |
| P1-16: iOS Logout | Settings → Logout | Return to login screen, session cleared |

### 1.3 Cross-Role Permutations
| Test | Steps | Expected |
|------|-------|----------|
| P1-17: Professor Login as Student | Professor credentials with student role | 403 Forbidden (role mismatch) |
| P1-18: Student Login as Professor | Student credentials with professor role | 403 Forbidden (role mismatch) |
| P1-19: Token Expiry | Wait for token expiry, make API call | 401 Unauthorized, redirect to login |
| P1-20: Concurrent Sessions | Login from iOS + web simultaneously | Both sessions valid |

---

## Phase 2: Professor Session Management
**Goal:** Verify professor can create, manage, and monitor simulation sessions.

### 2.1 Session Creation
| Test | Steps | Expected |
|------|-------|----------|
| P2-01: Create Session (Web) | Professor dashboard → New Session → Configure settings → Save | Session created, unique code generated (BIZ-XXXX) |
| P2-02: Create Session (API) | POST `/api/professor/sessions` with config | 201 Created, session returned |
| P2-03: Session Config - Rounds | Set totalRounds=8 (default) | Session created with 8 rounds |
| P2-04: Session Config - AI Count | Set numberOfAICompetitors=5 | 5 AI competitors created |
| P2-05: Session Config - Scoring Metric | Set scoringMetric=composite | Composite scoring enabled |
| P2-06: Session Config - Timed Mode | Set roundPacingMode=timed, deadlineHours=24 | Deadlines set for each round |
| P2-07: Invalid Session Config | Set negative rounds or zero AI count | 400 Bad Request with validation error |

### 2.2 Student Enrollment
| Test | Steps | Expected |
|------|-------|----------|
| P2-08: Enroll Student (Manual) | Professor dashboard → Add Student → Enter student_id, name | Student enrolled, assigned to team |
| P2-09: Enroll Multiple Students | Add 5 students to session | All enrolled, teams assigned evenly |
| P2-10: Auto-Assign Students | Professor dashboard → Auto-assign | Unassigned students distributed evenly across teams |
| P2-11: Remove Student | Professor dashboard → Remove student | Student removed, team count updated |
| P2-12: Student Already Enrolled | Try to enroll same student twice | 409 Conflict or warning message |
| P2-13: iOS Student Join Session | Open app → Enter session code (BIZ-XXXX) → Join | Student joins session, sees dashboard |
| P2-14: Invalid Session Code | Enter non-existent code | Error message, cannot join |
| P2-15: Session Full | Try to join when maxHumanTeams reached | Error message, session full |

### 2.3 Session Monitoring
| Test | Steps | Expected |
|------|-------|----------|
| P2-16: View Session Dashboard | Professor dashboard → Open session | See all teams, current round, rankings |
| P2-17: View Team Details | Click on team in dashboard | See team's decisions, results, financials |
| P2-18: View Rankings | Professor dashboard → Rankings tab | Teams ranked by scoring metric |
| P2-19: View Announcements | Professor dashboard → Send announcement | Announcement appears in student apps |
| P2-20: Real-time Updates | Professor makes change, student app refreshes | Changes reflected in real-time |

### 2.4 Session Control
| Test | Steps | Expected |
|------|-------|----------|
| P2-21: Pause Session | Professor dashboard → Pause | All students see "Session Paused" |
| P2-22: Resume Session | Professor dashboard → Resume | Session continues from paused state |
| P2-23: End Session Early | Professor dashboard → End Session | All students see "Simulation Complete" |
| P2-24: Reset Session | Professor dashboard → Reset Session | All data cleared, session restarts from round 1 |

---

## Phase 3: Student Simulation Flow (Online Mode)
**Goal:** Verify student can play through a full simulation with AI competitors.

### 3.1 Session Join & Setup
| Test | Steps | Expected |
|------|-------|----------|
| P3-01: Join Session (Code) | Enter session code → Join | Student sees team dashboard |
| P3-02: Join Session (Invite Link) | Tap invite link → Open app → Join | Student joins session automatically |
| P3-03: View Team Assignment | Check dashboard after joining | See team name, starting cash, AI competitors |
| P3-04: View Session Info | Open session details | See total rounds, current round, deadlines |
| P3-05: View Leaderboard | Tap Rankings button | See all teams ranked by scoring metric |
| P3-06: View AI Coach | Tap AI Coach button | See coaching tips for current round |

### 3.2 Round-by-Round Gameplay
| Test | Steps | Expected |
|------|-------|----------|
| P3-07: Round 1 - Make Decisions | Fill all decision fields → Submit | Decisions submitted, round processes |
| P3-08: Round 1 - View Results | After submission, view results | See round 1 results for all teams |
| P3-09: Round 2 - Make Decisions | Fill decisions → Submit | Round 2 processes, results shown |
| P3-10: Round 3 - Make Decisions | Fill decisions → Submit | Round 3 processes, results shown |
| P3-11: Round 4 - Make Decisions | Fill decisions → Submit | Round 4 processes, results shown |
| P3-12: Round 5 - Make Decisions | Fill decisions → Submit | Round 5 processes, results shown |
| P3-13: Round 6 - Make Decisions | Fill decisions → Submit | Round 6 processes, results shown |
| P3-14: Round 7 - Make Decisions | Fill decisions → Submit | Round 7 processes, results shown |
| P3-15: Round 8 - Make Decisions | Fill decisions → Submit | Round 8 processes, results shown |

### 3.3 Decision Input Validation
| Test | Steps | Expected |
|------|-------|----------|
| P3-16: Valid Decisions | Fill all fields with valid values → Submit | Success, round processes |
| P3-17: Missing Required Field | Leave wholesale price empty → Submit | Validation error, cannot submit |
| P3-18: Invalid Price (Negative) | Set wholesale price to -10 → Submit | Validation error, cannot submit |
| P3-19: Invalid Price (Too High) | Set wholesale price to 10000 → Submit | Validation error, cannot submit |
| P3-20: Invalid Production Quantity | Set production quantity > plantCapacity + 50 → Submit | Validation error, cannot submit |
| P3-21: Invalid Advertising Budget | Set advertising budget to -100 → Submit | Validation error, cannot submit |
| P3-22: Invalid Styling Budget | Set styling budget to 0 → Submit | Validation error, cannot submit |
| P3-23: Invalid TQM Investment | Set TQM investment to -50 → Submit | Validation error, cannot submit |
| P3-24: Invalid CSR Investment | Set CSR investment to -100 → Submit | Validation error, cannot submit |
| P3-25: Invalid Best Practices Investment | Set best practices investment to -100 → Submit | Validation error, cannot submit |
| P3-26: Invalid Incentive Pay | Set incentive pay to 2.0 (>1.0) → Submit | Validation error, cannot submit |
| P3-27: Invalid Training Hours | Set training hours to -10 → Submit | Validation error, cannot submit |
| P3-28: Invalid Overtime Percent | Set overtime percent to 100 (>50) → Submit | Validation error, cannot submit |
| P3-29: Invalid Dividends Per Share | Set dividends to -1.0 → Submit | Validation error, cannot submit |
| P3-30: Invalid Shares Buyback | Set shares buyback to -100 → Submit | Validation error, cannot submit |
| P3-31: Invalid Shares Issued | Set shares issued to -100 → Submit | Validation error, cannot submit |
| P3-32: Invalid New Loan Amount | Set new loan amount to -1000 → Submit | Validation error, cannot submit |
| P3-33: Invalid Private Label Bid Price | Set private label bid price to -10 → Submit | Validation error, cannot submit |
| P3-34: Invalid Private Label Max Units | Set private label max units to -10 → Submit | Validation error, cannot submit |
| P3-35: Invalid Amazon Price | Set amazon price to -10 → Submit | Validation error, cannot submit |
| P3-36: Invalid Amazon Ad Budget | Set amazon ad budget to -100 → Submit | Validation error, cannot submit |
| P3-37: Invalid Retail Outlets | Set retail outlets to -10 → Submit | Validation error, cannot submit |
| P3-38: Invalid Mail-in Rebate | Set mail-in rebate to -5 → Submit | Validation error, cannot submit |
| P3-39: Invalid Free Shipping Threshold | Set free shipping threshold to -10 → Submit | Validation error, cannot submit |
| P3-40: Invalid TikTok Budget | Set tiktok budget to -100 → Submit | Validation error, cannot submit |
| P3-41: Invalid Instagram Budget | Set instagram budget to -100 → Submit | Validation error, cannot submit |
| P3-42: Invalid YouTube Budget | Set youtube budget to -100 → Submit | Validation error, cannot submit |
| P3-43: Invalid Influencer Tier | Set influencer tier to invalid value → Submit | Validation error, cannot submit |
| P3-44: Invalid Celebrity Endorsement | Set celebrity endorsement to invalid value → Submit | Validation error, cannot submit |
| P3-45: Invalid Delivery Time | Set delivery time to invalid value → Submit | Validation error, cannot submit |
| P3-46: Invalid Materials Quality | Set materials quality to invalid value → Submit | Validation error, cannot submit |
| P3-47: Invalid Models Offered | Set models offered to 0 → Submit | Validation error, cannot submit |
| P3-48: Invalid FBA/FBM Selection | Select invalid fulfillment method → Submit | Validation error, cannot submit |

### 3.4 Financial Metrics Verification
| Test | Steps | Expected |
|------|-------|----------|
| P3-49: Cash Balance Update | After round 1, check cash balance | Cash = startingCash - costs + revenue |
| P3-50: Inventory Update | After round 1, check inventory | Inventory = production - sales |
| P3-51: S/Q Rating Update | After round 1, check S/Q rating | S/Q updated based on materials quality and TQM investment |
| P3-52: Image Rating Update | After round 1, check image rating | Image updated based on CSR, celebrity endorsement, S/Q |
| P3-53: Credit Rating Update | After round 1, check credit rating | Credit updated based on debt-to-equity ratio |
| P3-54: Investor Score Update | After round 1, check investor score | Investor score calculated from EPS, ROE, stock price, image, credit |
| P3-55: Market Share Update | After round 1, check market share | Market share calculated from units sold vs total market |
| P3-56: Customer Satisfaction Update | After round 1, check satisfaction | Satisfaction updated based on S/Q, image, delivery time |
| P3-57: Rejection Rate Update | After round 1, check rejection rate | Rejection rate calculated from TQM, training, incentive pay |
| P3-58: Cumulative Profit Update | After round 1, check cumulative profit | Cumulative profit = previous + current round profit |
| P3-59: Equity Update | After round 1, check equity | Equity = assets - liabilities |
| P3-60: Total Debt Update | After round 1, check total debt | Total debt = previous debt + new loans - repayments |
| P3-61: EPS Update | After round 1, check EPS | EPS = net income / shares outstanding |
| P3-62: ROE Update | After round 1, check ROE | ROE = net income / equity |
| P3-63: Stock Price Update | After round 1, check stock price | Stock price updated based on EPS, ROE, investor score |

### 3.5 Round Results & Reporting
| Test | Steps | Expected |
|------|-------|----------|
| P3-64: View Round Results | After round 1, tap "View Results" | See detailed results for all teams |
| P3-65: View Revenue Breakdown | In round results, check revenue channels | Wholesale, internet, Amazon, private label revenues shown |
| P3-66: View Cost Breakdown | In round results, check cost categories | Production, workforce, marketing, CSR costs shown |
| P3-67: View Competitor Analysis | In round results, check competitor summary | All AI competitors' revenues and market shares shown |
| P3-68: View Explanations | In round results, check explanations | AI-generated explanations for performance drivers |
| P3-69: View Coaching Tips | In round results, check coaching tips | Personalized coaching tips based on performance |
| P3-70: View Performance History | Tap History button | See all rounds' performance metrics in chart format |
| P3-71: View Leaderboard | Tap Rankings button | See all teams ranked by scoring metric |
| P3-72: Export PDF | Tap Export PDF button | PDF report generated and shared |
| P3-73: Share Session | Tap Share button | Session code/link shared via iOS share sheet |

---

## Phase 4: Quick Demo Mode (Local Simulation)
**Goal:** Verify Quick Demo runs correctly without backend, all 8 rounds complete, and results are consistent.

### 4.1 Quick Demo Initiation
| Test | Steps | Expected |
|------|-------|----------|
| P4-01: Access Quick Demo | Login → Tap "Quick Demo" button | Navigate to Quick Demo setup screen |
| P4-02: Quick Demo Config | Set demo parameters (if configurable) | Demo configured with default settings |
| P4-03: Start Quick Demo | Tap "Start Quick Demo" | Simulation begins, processing indicator shown |

### 4.2 Quick Demo Execution
| Test | Steps | Expected |
|------|-------|----------|
| P4-04: Round 1 Processing | Watch processing indicator during round 1 | "Round 1 of 8 complete" shown |
| P4-05: Round 2 Processing | Watch processing indicator during round 2 | "Round 2 of 8 complete" shown |
| P4-06: Round 3 Processing | Watch processing indicator during round 3 | "Round 3 of 8 complete" shown |
| P4-07: Round 4 Processing | Watch processing indicator during round 4 | "Round 4 of 8 complete" shown |
| P4-08: Round 5 Processing | Watch processing indicator during round 5 | "Round 5 of 8 complete" shown |
| P4-09: Round 6 Processing | Watch processing indicator during round 6 | "Round 6 of 8 complete" shown |
| P4-10: Round 7 Processing | Watch processing indicator during round 7 | "Round 7 of 8 complete" shown |
| P4-11: Round 8 Processing | Watch processing indicator during round 8 | "Round 8 of 8 complete" shown |
| P4-12: Simulation Complete | After round 8, check state | "Simulation Complete!" message shown |
| P4-13: No Freeze/Crash | Monitor app during entire simulation | App remains responsive, no crashes |
| P4-14: Dashboard Updates | Check dashboard during simulation | Round number updates correctly (1→8) |

### 4.3 Quick Demo Results Consistency
| Test | Steps | Expected |
|------|-------|----------|
| P4-15: Dashboard vs Results - Round 8 | Compare dashboard values with final results view | All metrics match exactly (cash, inventory, S/Q, image, credit, investor score, market share, satisfaction, rejection rate) |
| P4-16: Dashboard vs Results - Revenue | Compare revenue breakdowns | Wholesale, internet, Amazon, private label revenues match |
| P4-17: Dashboard vs Results - Costs | Compare cost breakdowns | Production, workforce, marketing, CSR costs match |
| P4-18: Dashboard vs Results - Scorecard | Compare investor scorecard | EPS, ROE, stock price, image rating, credit rating match |
| P4-19: Dashboard vs Results - Rankings | Compare team rankings | All teams ranked correctly in both views |
| P4-20: Dashboard vs Results - Explanations | Compare explanations | AI-generated explanations match between views |
| P4-21: Dashboard vs Results - Coaching Tips | Compare coaching tips | Personalized tips match between views |
| P4-22: Dashboard vs Results - Competitor Analysis | Compare competitor summaries | All AI competitors' data matches between views |
| P4-23: Dashboard vs Results - Performance History | Compare performance history | All rounds' data matches between views |
| P4-24: Dashboard vs Results - PDF Export | Compare PDF with dashboard values | PDF report matches dashboard and results views |

### 4.4 Quick Demo Edge Cases
| Test | Steps | Expected |
|------|-------|----------|
| P4-25: Quick Demo After Online Session | Run Quick Demo after playing online session | Quick Demo starts fresh, no stale data |
| P4-26: Quick Demo After Logout/Login | Logout, login again, run Quick Demo | Quick Demo works correctly with fresh session |
| P4-27: Quick Demo Device Rotation | Rotate device during simulation | UI updates correctly, no crashes |
| P4-28: Quick Demo App Background | Background app during simulation | Simulation continues, results saved on foreground |
| P4-29: Quick Demo Low Memory | Run with low device memory | Simulation completes without OOM crash |
| P4-30: Quick Demo Network Unavailable | Run with no network connection | Simulation completes locally, no network errors |

---

## Phase 5: Multi-Student Session (Online Mode)
**Goal:** Verify multiple students can play in the same session simultaneously.

### 5.1 Multi-Student Setup
| Test | Steps | Expected |
|------|-------|----------|
| P5-01: Two Students Join Same Session | Student A and B join same session code | Both see same session, different teams |
| P5-02: Three Students Join Same Session | Student A, B, C join same session code | All three see same session, different teams |
| P5-03: Four Students Join Same Session | Student A, B, C, D join same session code | All four see same session, different teams |
| P5-04: Five Students Join Same Session | Student A, B, C, D, E join same session code | All five see same session, different teams |
| P5-05: Six Students Join Same Session | Student A, B, C, D, E, F join same session code | All six see same session, different teams |
| P5-06: Max Students Join Session | Try to join when maxHumanTeams reached | Error message, cannot join |

### 5.2 Multi-Student Gameplay
| Test | Steps | Expected |
|------|-------|----------|
| P5-07: Student A Submits Decisions | Student A submits round 1 decisions | Round 1 processes, results shown to all |
| P5-08: Student B Submits Decisions | Student B submits round 1 decisions | Round 1 processes, results shown to all |
| P5-09: Student C Submits Decisions | Student C submits round 1 decisions | Round 1 processes, results shown to all |
| P5-10: Student D Submits Decisions | Student D submits round 1 decisions | Round 1 processes, results shown to all |
| P5-11: Student E Submits Decisions | Student E submits round 1 decisions | Round 1 processes, results shown to all |
| P5-12: Student F Submits Decisions | Student F submits round 1 decisions | Round 1 processes, results shown to all |
| P5-13: All Students Submit Round 1 | All students submit round 1 decisions | Round 1 processes, results shown to all |
| P5-14: All Students Submit Round 2 | All students submit round 2 decisions | Round 2 processes, results shown to all |
| P5-15: All Students Submit Round 3 | All students submit round 3 decisions | Round 3 processes, results shown to all |
| P5-16: All Students Submit Round 4 | All students submit round 4 decisions | Round 4 processes, results shown to all |
| P5-17: All Students Submit Round 5 | All students submit round 5 decisions | Round 5 processes, results shown to all |
| P5-18: All Students Submit Round 6 | All students submit round 6 decisions | Round 6 processes, results shown to all |
| P5-19: All Students Submit Round 7 | All students submit round 7 decisions | Round 7 processes, results shown to all |
| P5-20: All Students Submit Round 8 | All students submit round 8 decisions | Round 8 processes, results shown to all |

### 5.3 Multi-Student Consistency
| Test | Steps | Expected |
|------|-------|----------|
| P5-21: Same Round Results | All students view round 1 results | All see identical results for all teams |
| P5-22: Same Rankings | All students view rankings | All see identical team rankings |
| P5-23: Same Financial Metrics | All students view financial metrics | All see identical cash, inventory, S/Q, etc. for all teams |
| P5-24: Same Leaderboard | All students view leaderboard | All see identical leaderboard |
| P5-25: Real-time Sync | Student A makes decision, Student B refreshes | Student B sees updated data immediately |
| P5-26: Session State Sync | Professor pauses session, all students refresh | All students see "Session Paused" |
| P5-27: Session End Sync | Professor ends session, all students refresh | All students see "Simulation Complete" |

---

## Phase 6: Professor Dashboard (Web)
**Goal:** Verify professor web dashboard works correctly for session management and monitoring.

### 6.1 Professor Dashboard Access
| Test | Steps | Expected |
|------|-------|----------|
| P6-01: Professor Login (Web) | Navigate to professor dashboard → Login | Dashboard loads with session list |
| P6-02: Professor Logout (Web) | Click logout button | Return to login screen |
| P6-03: Professor Session List | View session list on dashboard | All professor's sessions listed with status |
| P6-04: Professor Session Details | Click on session in list | Session details page loads with teams, rounds, results |

### 6.2 Professor Session Management (Web)
| Test | Steps | Expected |
|------|-------|----------|
| P6-05: Create Session (Web) | Click "New Session" → Configure → Save | Session created, appears in session list |
| P6-06: Edit Session (Web) | Click "Edit" on session → Modify settings → Save | Session settings updated |
| P6-07: Delete Session (Web) | Click "Delete" on session → Confirm | Session deleted, removed from list |
| P6-08: Pause Session (Web) | Click "Pause" on session | All students see "Session Paused" |
| P6-09: Resume Session (Web) | Click "Resume" on session | Session continues from paused state |
| P6-10: End Session (Web) | Click "End" on session | All students see "Simulation Complete" |
| P6-11: Reset Session (Web) | Click "Reset" on session | All data cleared, session restarts from round 1 |

### 6.3 Professor Monitoring (Web)
| Test | Steps | Expected |
|------|-------|----------|
| P6-12: View Team Details (Web) | Click on team in dashboard | See team's decisions, results, financials |
| P6-13: View Rankings (Web) | Click "Rankings" tab | See all teams ranked by scoring metric |
| P6-14: View Announcements (Web) | Click "Announcements" tab | See all announcements sent to students |
| P6-15: Send Announcement (Web) | Type announcement → Send | Announcement appears in student apps |
| P6-16: View Session Analytics (Web) | Click "Analytics" tab | See session-wide analytics and reports |
| P6-17: Export Session Report (Web) | Click "Export" button | PDF/CSV report generated and downloaded |

---

## Test Permutations Matrix

### Role × Session Type × Device
| Test ID | Role | Session Type | Device | Notes |
|---------|------|--------------|--------|-------|
| P1-01 to P1-06 | Professor | N/A | Web | Professor auth flows |
| P1-07 to P1-12 | Student | N/A | Web | Student auth flows |
| P1-13 to P1-16 | Student | N/A | iOS (iPhone) | iOS app auth flows |
| P1-17 to P1-20 | Both | N/A | Web+iOS | Cross-role permutations |
| P2-01 to P2-07 | Professor | Online | Web | Session creation |
| P2-08 to P2-15 | Professor+Student | Online | Web+iOS | Student enrollment |
| P2-16 to P2-24 | Professor | Online | Web | Session monitoring & control |
| P3-01 to P3-06 | Student | Online | iOS (iPhone) | Session join & setup |
| P3-07 to P3-15 | Student | Online | iOS (iPhone) | Round-by-round gameplay |
| P3-16 to P3-48 | Student | Online | iOS (iPhone) | Decision input validation |
| P3-49 to P3-63 | Student | Online | iOS (iPhone) | Financial metrics verification |
| P3-64 to P3-73 | Student | Online | iOS (iPhone) | Round results & reporting |
| P4-01 to P4-03 | Student | Quick Demo | iOS (iPhone) | Quick demo initiation |
| P4-04 to P4-14 | Student | Quick Demo | iOS (iPhone) | Quick demo execution |
| P4-15 to P4-24 | Student | Quick Demo | iOS (iPhone) | Results consistency |
| P4-25 to P4-30 | Student | Quick Demo | iOS (iPhone) | Edge cases |
| P5-01 to P5-06 | Multiple Students | Online | iOS (iPhone) | Multi-student setup |
| P5-07 to P5-20 | Multiple Students | Online | iOS (iPhone) | Multi-student gameplay |
| P5-21 to P5-27 | Multiple Students | Online | iOS (iPhone) | Multi-student consistency |
| P6-01 to P6-04 | Professor | Online | Web | Professor dashboard access |
| P6-05 to P6-11 | Professor | Online | Web | Session management (Web) |
| P6-12 to P6-17 | Professor | Online | Web | Session monitoring (Web) |

### Decision Type Permutations
| Test ID | Decision Type | Valid Values | Invalid Values | Notes |
|---------|--------------|--------------|----------------|-------|
| P3-16 to P3-20 | Pricing | 50-500 | Negative, >10000 | Wholesale, internet, private label prices |
| P3-21 to P3-25 | Product | 0-10000 | Negative, >50000 | Styling, TQM, CSR, best practices investments |
| P3-26 to P3-30 | Marketing | 0-50000 | Negative, >100000 | Advertising, social media budgets |
| P3-31 to P3-35 | Workforce | 20000-40000 | Negative, >100000 | Base wage, incentive pay, training hours |
| P3-36 to P3-40 | Production | 0-500 | Negative, >1000 | Production quantity, overtime percent |
| P3-41 to P3-48 | Finance | 0-100000 | Negative, >500000 | CSR, dividends, buyback, issued shares, loans |

### Scoring Metric Permutations
| Test ID | Scoring Metric | Expected Behavior | Notes |
|---------|---------------|-------------------|-------|
| P3-54, P5-21 | Investor Score | Teams ranked by investor score | EPS + ROE + Stock Price + Image + Credit scores |
| P3-54, P5-21 | Cumulative Profit | Teams ranked by cumulative profit | Total profit across all rounds |
| P3-54, P5-21 | Revenue | Teams ranked by cumulative revenue | Total revenue across all rounds |
| P3-54, P5-21 | Composite | Teams ranked by composite score | 40% profit + 30% revenue + 30% market share |

### AI Difficulty Permutations
| Test ID | AI Difficulty | Expected Behavior | Notes |
|---------|--------------|-------------------|-------|
| P3-07 to P3-15 | Easy | AI makes conservative decisions | Lower prices, less advertising |
| P3-07 to P3-15 | Medium | AI makes balanced decisions | Moderate prices, moderate advertising |
| P3-07 to P3-15 | Hard | AI makes aggressive decisions | Higher prices, more advertising, better quality |

---

## Test Execution Order

### Phase 1: Authentication (Day 1)
1. P1-01 to P1-06: Professor auth flows (Web)
2. P1-07 to P1-12: Student auth flows (Web)
3. P1-13 to P1-16: iOS app auth flows (iPhone)
4. P1-17 to P1-20: Cross-role permutations

### Phase 2: Professor Session Management (Day 2)
1. P2-01 to P2-07: Session creation (Web)
2. P2-08 to P2-15: Student enrollment (Web + iOS)
3. P2-16 to P2-24: Session monitoring & control (Web)

### Phase 3: Student Simulation Flow (Day 3-4)
1. P3-01 to P3-06: Session join & setup (iOS)
2. P3-07 to P3-15: Round-by-round gameplay (iOS)
3. P3-16 to P3-48: Decision input validation (iOS)
4. P3-49 to P3-63: Financial metrics verification (iOS)
5. P3-64 to P3-73: Round results & reporting (iOS)

### Phase 4: Quick Demo Mode (Day 5)
1. P4-01 to P4-03: Quick demo initiation (iOS)
2. P4-04 to P4-14: Quick demo execution (iOS)
3. P4-15 to P4-24: Results consistency (iOS)
4. P4-25 to P4-30: Edge cases (iOS)

### Phase 5: Multi-Student Session (Day 6)
1. P5-01 to P5-06: Multi-student setup (iOS)
2. P5-07 to P5-20: Multi-student gameplay (iOS)
3. P5-21 to P5-27: Multi-student consistency (iOS)

### Phase 6: Professor Dashboard (Day 7)
1. P6-01 to P6-04: Professor dashboard access (Web)
2. P6-05 to P6-11: Session management (Web)
3. P6-12 to P6-17: Session monitoring (Web)

---

## Prerequisites
- **Backend:** Running on EC2 at `18.215.180.58:80`
- **iOS App:** Built and installed on iPhone 17 Pro Max (UDID: `00008150-000839012132401C`)
- **Test Accounts:** 
  - Professor: `prof1` / `Prof@2026X`
  - Student: `stu1` / `Stu1@2026X`
- **Network:** Stable internet connection for online mode, offline capability for Quick Demo
- **Device:** iPhone 17 Pro Max with sufficient storage and battery

## Success Criteria
- All 173 tests pass without crashes or data inconsistencies
- Dashboard and Final Results views show identical values for all metrics
- Quick Demo completes all 8 rounds without freeze or crash
- Multi-student sessions maintain data consistency across all devices
- Professor dashboard reflects real-time changes from student actions
- All validation rules prevent invalid input submission

## Risk Mitigation
- **Backend Downtime:** Use Quick Demo mode for iOS testing if backend is unavailable
- **Device Issues:** Have backup device (iPad or another iPhone) ready
- **Network Issues:** Test offline scenarios (Quick Demo, cached data)
- **Data Corruption:** Reset session after each major test phase
- **Account Lockout:** Use separate test accounts for each test phase

---

*Test Plan Version: 1.0*
*Created: 2026-07-13*
*Last Updated: 2026-07-13*
