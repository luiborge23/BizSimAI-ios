# BizSim AI — Comprehensive Implementation Plan

**Date:** 2026-05-03
**Last Updated:** 2026-05-06
**Author:** Paul (TPM Assistant)
**Status:** In Progress — Phase 5 Core (Auth + WebSocket) ✅ + Production Config ✅ + Apple/Google JWKS ✅ + iOS Build ✅

---

## Executive Summary

BizSim AI is a SwiftUI business simulation application with a deterministic simulation engine, AI competitors, and rule-based coaching. The codebase has strong foundations (55+ Swift files, 12K+ lines) but needs a backend layer before classroom deployment. This plan addresses all critical, high, medium, and production gaps identified across multiple code reviews and audits.

### Key Metrics
- **Total issues found:** 25+ across all categories
- **Critical (P0):** 4 issues requiring immediate fix (incl. new backend gap)
- **High (P1):** 8 issues requiring fix before deployment
- **Medium (P2):** 9+ issues for enhancement
- **Estimated effort:** 18-28 days of focused development

---

## Phase 1: Critical Fixes (P0) — Days 1-2

### 1.1 Resolve Duplicate Codebase

**Problem:** Two exact copies of the codebase exist:
- `/Users/luisborges/2026/BizSimAI/` — macOS app (Swift Package)
- `/Users/luisborges/2026/BizSimAI-ios/` — iOS app (with Xcode project)

**Solution:**
1. Keep `BizSimAI-ios/` as the primary development location
2. Move `BizSimAI/` to `BizSimAI-backend/` (for future web backend)
3. Create a shared Swift Package at `BizSimAI-Core/` containing:
   - All Models (SimulationModels.swift, SimulationSession.swift)
   - All Engine code (SimulationEngine.swift, AICompetitor.swift, GameController.swift)
   - All Services (CoachingService.swift, ReportingManager.swift)
4. Both macOS and iOS apps depend on `BizSimAI-Core` via SPM
5. Each app only contains its own Views and ViewModels

**Verification:** Both projects build without errors, all imports resolve correctly.

### 1.2 Add Input Validation to PlayerDecision

**Problem:** PlayerDecision accepts any values without validation, which can crash the simulation.

**Solution:** Add a `validate()` method and make PlayerDecision init fail-safe:

```swift
struct PlayerDecision {
    enum ValidationError: Error, LocalizedError {
        case negativePrice(String)
        case priceBelowCost(String)
        case productionExceedsCapacity(Int, Int)
        case invalidWageRange(Double, ClosedRange<Double>)
        case invalidDividendRange(Double)
        case invalidLoanAmount(Double)
        
        var errorDescription: String? { /* ... */ }
    }
    
    func validate(baseCost: Double, capacity: Int) throws {
        guard wholesalePrice > 0 else { throw .negativePrice("Wholesale price") }
        guard internetPrice > 0 else { throw .negativePrice("Internet price") }
        guard amazonPrice > 0 else { throw .negativePrice("Amazon price") }
        guard wholesalePrice >= baseCost * 1.1 else { throw .priceBelowCost("Wholesale price") }
        guard internetPrice >= baseCost * 1.1 else { throw .priceBelowCost("Internet price") }
        guard productionQuantity <= capacity * 2 else { throw .productionExceedsCapacity(productionQuantity, capacity) }
        guard baseWage >= 15_000 && baseWage <= 40_000 else { throw .invalidWageRange(baseWage, 15_000...40_000) }
        guard dividendsPerShare >= 0 && dividendsPerShare <= 5.0 else { throw .invalidDividendRange(dividendsPerShare) }
        guard newLoanAmount >= 0 && newLoanAmount <= 50_000 else { throw .invalidLoanAmount(newLoanAmount) }
    }
}
```

**Verification:** Unit tests verify all validation rules.

### 1.3 Fix Division by Zero Risks in SimulationEngine

**Problem:** Multiple division operations lack proper guards.

**Solution:** Add guards to all division operations (see inline code comments in original plan for exact placement in `computeWholesaleDemand`, `computeInternetDemand`, `computeAmazonDemand`, `computePrivateLabelDemand`).

**Verification:** Run simulation with single team, verify no crashes.

---

## Phase 2: High Priority Fixes (P1) — Days 3-6

### 2.1 Split PlayerDecision into Logical Sub-structures

**Problem:** PlayerDecision has 30+ fields, violating SRP.

**Solution:** Create logical sub-structures:
- `PricingDecision` — wholesale/internet/amazon/private label pricing
- `ProductDecision` — materials, styling, models, TQM, best practices
- `MarketingDecision` — advertising, celebrity, retail, social media, fulfillment
- `WorkforceDecision` — wage, incentive, training
- `ProductionDecision` — quantity, overtime, CSR
- `FinancialDecision` — dividends, loans, buyback, issuance

Backward-compatible computed properties maintain existing API.

**Verification:** All existing code compiles with backward-compatible computed properties.

### 2.2 Fix CoachingService Strategy-Awareness

**Problem:** Coaching messages don't account for player strategy, only penalize deviations.

**Solution:** Add strategy detection (LowCostLeader, PremiumDifferentiator, MarketingHeavy, WorkforceFocused, Balanced) and forward-looking coaching that considers cash runway, rounds remaining, share dilution impact.

**Verification:** Coaching messages are context-aware and provide positive reinforcement.

### 2.3 Fix AI Competitor Strategies

**Problem:** Low-Cost Leader pricing is too aggressive; strategies don't adapt to market conditions.

**Solution:** Add market-aware adaptation (price floor at 85% of market, share issuance for growth funding in later rounds, adaptive strategy protocol).

**Verification:** AI competitors produce realistic, varied decisions across rounds.

### 2.4 Add Error Handling in GameController

**Problem:** No error handling for simulation failures; session enters undefined state.

**Solution:** Result type for `advanceRound()`, Status enum (idle/running/paused/ended/error), proper error recovery.

### 2.5 Add SwiftData/Core Data Persistence

**Problem:** Session data is lost when app closes.

**Solution:** Add SwiftData persistence (iOS 17+) with `PersistentSession` model, `SessionPersistenceService` for CRUD operations, JSON serialization for complex nested objects.

**Verification:** Sessions persist across app restarts.

---

## Phase 3: Medium Priority Enhancements (P2) — Days 7-10

### 3.1 Add Dark Mode Support
Use semantic colors (`Color.primary`, `Color.secondary`, `Color(.systemBackground)`) instead of hardcoded colors.

### 3.2 Group Decision UI into Logical Sections
TabView with tabs: Pricing, Product, Marketing, Workforce, Production, Finance.

### 3.3 Add Onboarding/Tutorial
4-page interactive tutorial covering: welcome, making decisions, competing against AI, AI coaching.

### 3.4 Fix Storage Cost and Private Label Allocation
Reduce storage cost to $0.25/unit/round (realistic), weight private label allocation by bid price.

---

## Phase 4: Testing — Days 11-12

### 4.1 Unit Tests for SimulationEngine
- `testProcessRound_ValidInput_NoCrash` — round processing
- `testComputeSQRating_DifferentQuality_YieldsDifferentRatings` — S/Q calculation
- `testComputeRejectionRate_HighTraining_LowerRate` — defect calculation
- `testComputeWholesaleAttractivity_PriceAndQuality_AffectAttractivity` — demand model

### 4.2 Integration Tests
- `testFullSimulation_RoundsComplete_NoCrash` — end-to-end 10-round simulation
- `testCoachingService_GeneratesMessages` — coaching feedback quality

**Target:** 80%+ code coverage for SimulationEngine and AICompetitor modules.

---

## Phase 5: Classroom Production Layer (NEW — 2026-05-05)

> **Status:** Not started. Added after comprehensive code audit on May 05.
> **Priority:** Blocks classroom deployment entirely.
> **Estimated effort:** 10-15 days of focused development.

### 5.1 Cloud Backend for Real Session Sharing (BLOCKS DEPLOYMENT)

**Problem:** The app has **no cloud backend** — no Firebase, CloudKit, or any server layer. Students type a session code like `BIZ-7M4V`, but there's no way for a student on a *different device* to actually join that session. The `findSession()` looks up `professorSessions` which only lives in the professor's local `AppState`.

**Impact:** Students can only join if they're in the exact same app instance. The demo buttons (`startDemo()`, `startQuickDemo()`) exist as workarounds, but they create local simulations, not shared ones. **This blocks ALL classroom deployment.**

**Solution:** Implement a lightweight backend. Recommended: **Firebase Firestore** (best fit for iOS/Swift ecosystem):
- Real-time data sync (students see updates live)
- Simple authentication (email, Google, Apple)
- Session state persistence
- Push notification triggers

**Key components needed:**
1. `NetworkService` — WebSocket/REST client abstraction for the app
2. `SyncService` — Maps `SimulationSession` ↔ Firestore documents
3. `AuthManager` — Handles login/signup (Apple Auth + optional Google)
4. `SessionSyncManager` — Manages conflict resolution, optimistic updates, offline queue
5. Backend endpoint — Firebase Cloud Function for server-side game loop (optional, or keep serverless with Firestore triggers)

**Data model mapping:**
```
Firestore:
├── sessions/{sessionId}
│   ├── config (SessionConfiguration)
│   ├── currentRound
│   ├── state (active/completed)
│   ├── teams[]
│   └── results[]
├── sessions/{sessionId}/decisions/{round}/{teamId}
│   └── PlayerDecision
├── users/{userId}
│   ├── email
│   ├── displayName
│   ├── role (professor/student)
│   └── sessions[]
└── announcements/{sessionId}/{announceId}
    └── message text, timestamp, authorId
```

**Sync protocol:**
```swift
enum SyncAction {
    case createSession(config: SessionConfiguration)
    case joinSession(sessionId: String, teamName: String)
    case submitDecision(round: Int, decision: PlayerDecision)
    case syncRoundResults([RoundResult])
    case syncLeaderboard([RankingEntry])
    case sendAnnouncement(message: String)
}
```

### 5.2 User Authentication ✅ DONE (2026-05-06)

**Status:** Implemented with JWT-based auth.

**What was built:**
- `auth.py` — JWT token creation/verification (no external deps), login/register endpoints
- `routers/auth.py` — Login (password, Apple, Google), register, verify token, role-gated endpoints
- Professor login: username/password (default: `professor` / `bizsimai2026`)
- Student registration: student_id + name + password
- Apple/Google ID token exchange: placeholder for prod verification
- Role-based access: `verify_professor()`, `verify_student_or_professor()` dependencies
- 24-hour token expiry, HS256 algorithm

**Endpoints:**
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | None | Login (password/apple/google) |
| `/api/auth/register` | POST | None | Student registration |
| `/api/auth/verify` | POST | JWT | Verify token, return user info |
| `/api/auth/professor-only` | POST | JWT + Professor | Professor-only check |
| `/api/auth/student-or-professor` | POST | JWT + Student/Prof | Student/professor check |

**Tests:** 13 Phase 5 tests pass (auth, registration, token verification, WebSocket, grade export)

### 5.3 Real-Time Synchronization ✅ DONE (2026-05-06)

**Status:** WebSocket implementation complete.

**What was built:**
- `ws_manager.py` — Connection manager for per-session WebSocket groups
- `routers/websocket.py` — WebSocket endpoint with JWT auth, message handling
- Auto-broadcast on session start and round completion
- Room-based: students only receive updates for their session code

**WebSocket Protocol:**
- Endpoint: `ws://host/ws/{sessionCode}?token={jwt_token}`
- Supported message types:
  - `{"type": "join", "teamId": "..."}` — identify as a team
  - `{"type": "ping"}` / `{"type": "pong"}` — keepalive
  - `{"type": "request_status"}` — request current session status
- Incoming broadcast messages:
  - `{"type": "connected", ...}` — welcome with session info
  - `{"type": "session_started", ...}` — when professor starts session
  - `{"type": "round_complete", ...}` — results published
  - `{"type": "status", ...}` — current session status
  - `{"type": "error", ...}` — error messages

**Tests:** WebSocket connect/disconnect tests pass

### 5.4 Announcements System (Prof → Student)

**Problem:** `AnnouncementsView.swift` exists (132 lines) but professors can't send announcements to students.

**Solution:** Wire up the UI to Firestore:
```swift
class AnnouncementService {
    func send(sessionId: String, text: String) async throws
    func fetchForSession(sessionId: String) async -> [Announcement]
    // Firestore path: announcements/{sessionId}/{announceId}
}
```

### 5.5 Grade Mapping / LMS Integration

**Problem:** `GradeMappingView.swift` (221 lines) exists but no grade export/integration with Moodle, Canvas, or Blackboard.

**Solution:**
- CSV export for manual LMS import (immediate)
- Canvas LTI integration (longer term)
- Professor assigns grade weightings → auto-calculates student grades

---

## Phase 6: Polish (Future) — Days 25-28

### 6.1 Accessibility Audit
- VoiceOver labels on all interactive elements
- Dynamic Type support (font scaling)
- Color contrast compliance (WCAG AA minimum)

### 6.2 Internationalization (i18n)
- Extract all strings to `Localizable.strings`
- Support for Spanish, French, Portuguese (classroom languages)

### 6.3 Crash Reporting
- Add Firebase Crashlytics
- Anonymous usage analytics (no PII)

### 6.4 Cross-Platform Polish
- macOS-specific UI adjustments
- iPad multitasking support (split view, slide over)

### 6.5 Beta Testing Program
- TestFlight distribution
- Feedback collection form
- Bug triage workflow

---

## Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1: Critical Fixes | Days 1-2 | Duplicate codebase resolved, input validation, division by zero fixes |
| 2: High Priority | Days 3-6 | PlayerDecision split, coaching improvements, AI strategy fixes, error handling, persistence |
| 3: Medium Priority | Days 7-10 | Dark mode, grouped UI, onboarding, storage/PL fixes |
| 4: Testing | Days 11-12 | Unit tests, integration tests, 80%+ coverage |
| **5: Classroom Production** | **Days 13-25** | **Firebase backend, Auth, Real-time sync, Announcements, Grade export** |
| 6: Polish | Days 25-28 | Accessibility, i18n, Crashlytics, beta testing |

### Immediate Next Steps (Updated 2026-05-05)

1. **Phase 5, Step 1: Cloud Backend** — This is now the #1 priority. Without it, the app cannot be used in a classroom.
2. **Phase 5, Step 2: Authentication** — Required for session ownership and grade tracking.
3. **Phase 1-4** — Can run in parallel with Phase 5 backend development (the local app is feature-complete; backend can be built alongside).
4. **Phase 5, Steps 4-5** — Announcements and grade export build on top of the backend.

---

## Risk Assessment (Updated 2026-05-05)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **No backend blocks deployment** | **Critical** | Build Firebase backend as Phase 5 |
| No authentication | High | Apple Auth + Google Sign-In |
| No real-time sync | High | Firestore listeners |
| Duplicate codebase grows | Medium | Move to shared SPM package (Phase 1) |
| Zero test coverage | High | Add unit tests for SimulationEngine first |
| No persistence | Medium | Add SwiftData persistence (Phase 2) |
| Complex UI (30+ fields) | Low | Group into tabs/sections (Phase 3) |

---

## Success Criteria (Updated 2026-05-05)

### Pre-Production (Phase 1-4)
- [ ] Both macOS and iOS apps build without errors
- [ ] All P0 issues resolved
- [ ] 80%+ code coverage for SimulationEngine
- [ ] Sessions persist across app restarts
- [ ] Coaching messages are strategy-aware
- [ ] AI competitors produce realistic decisions
- [ ] Dark mode fully supported
- [ ] Onboarding tutorial present
- [ ] Decision UI grouped into logical sections

### Classroom Ready (Phase 5)
- [ ] **Firebase backend deployed (sessions shareable across devices)**
- [ ] **Apple/Google authentication working**
- [ ] **Real-time sync: students see professor actions live**
- [ ] **Professor can send announcements to students**
- [ ] **Grade CSV export functional**

### Production Launch (Phase 6)
- [ ] **Accessibility audit passed**
- [ ] **TestFlight beta testing launched**

---

## Current State (2026-05-05)

### What's Done
- ✅ All UI views implemented (Professor, Student, Launch, Shared)
- ✅ Complete simulation engine with 6 decision categories
- ✅ AI competitors with 4 strategies (Low-Cost Leader, Differentiator, Best-Cost, Adaptive)
- ✅ Rule-based coaching service (14 heuristic rules)
- ✅ Investor Scorecard (EPS, ROE, Stock Price, Image, Credit — each worth 20 pts)
- ✅ Ratcheting targets (+6% per round)
- ✅ Multi-channel demand model (Wholesale, Amazon, Internet, Private Label)
- ✅ Social media integration (TikTok, Instagram, YouTube)
- ✅ Student leaderboard & round results
- ✅ AI Coach (rule-based) + Claude API hook (Settings)
- ✅ PDF export
- ✅ Clean, buildable SwiftUI codebase
- ✅ Deterministic simulation (SeededRandomGenerator)

### What's Pending
- 🔴 Cloud backend (Firebase) — **blocks deployment**
- 🔴 User authentication
- 🔴 Real-time sync
- 🟡 Input validation
- 🟡 Division-by-zero guards
- 🟡 Error handling in GameController
- 🟡 SwiftData persistence
- 🟡 Coaching strategy-awareness
- 🟡 AI strategy adaptation
- 🟡 Dark mode
- 🟡 Onboarding tutorial
- 🟡 Accessibility audit
- 🟡 Unit tests
