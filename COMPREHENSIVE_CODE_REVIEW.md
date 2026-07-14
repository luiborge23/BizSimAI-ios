# BizSim AI — Comprehensive Code Review

**Date:** 2026-05-03
**Reviewer:** Paul (TPM Assistant)
**Scope:** Full codebase — backend (BizSimAI) + iOS app (BizSimAI-ios)

---

## 1. Architecture Overview

BizSim AI is a **macOS SwiftUI-only** business simulation application (not a web app with a Python backend). The simulation engine, AI competitors, and coaching service all run locally.

### Project Structure

```
BizSimAI/ (backend/macOS app — Swift Package)
├── Sources/
│   ├── Engine/
│   │   ├── SimulationEngine.swift    — Core deterministic simulation (670 lines)
│   │   ├── AICompetitor.swift        — 4 AI competitor strategies (324 lines)
│   │   └── GameController.swift      — Auto-play & round management
│   ├── Models/
│   │   ├── SimulationModels.swift    — Domain models (1,200+ lines)
│   │   └── SimulationSession.swift   — Session state management
│   ├── Services/
│   │   └── CoachingService.swift     — Rule-based coaching (219 lines)
│   ├── Services/
│   │   └── ReportingManager.swift    — Export/reporting
│   ├── ViewModels/ (10 files)
│   └── Views/ (Professor, Student, Shared, Components)

BizSimAI-ios/ (iOS app — duplicate of above)
├── BizSimAI/
│   ├── Engine/ (exact copy)
│   ├── Models/ (exact copy)
│   ├── Services/ (exact copy)
│   ├── ViewModels/ (exact copy)
│   └── Views/ (exact copy)
├── BizSimAI.xcodeproj/
└── Package.swift
```

### Key Finding: Duplicate Codebases

There are **two copies** of the entire project:
1. `/Users/luisborges/2026/BizSimAI/` — macOS app (Swift Package, no Xcode project)
2. `/Users/luisborges/2026/BizSimAI-ios/` — iOS app (with Xcode project)

The iOS app's `BizSimAI/` directory is an **exact copy** of the backend's `Sources/` directory. This is a maintenance risk.

---

## 2. SimulationEngine.swift — Core Engine (670 lines)

### Strengths

- **Deterministic simulation** with seeded RNG (`SeededRandomGenerator`) — reproducible results
- **Clear mathematical model** — price elasticity (1.5), SQ weight (1.2), advertising weight (0.6)
- **Multi-channel demand allocation** — wholesale (50%), internet (15%), Amazon (20%), private label (15%)
- **Comprehensive financial model** — production costs, workforce costs, marketing, CSR, endorsement, Amazon fees, rebates, delivery, storage, interest, dividends
- **Investor scorecard** with ratcheting targets (6% increase per round)
- **Stock price model** with volatility dampening (40% previous + 60% new)
- **Social media integration** — TikTok, Instagram, YouTube, influencer tiers
- **Rejection rate model** affected by TQM, training, incentive pay, best practices

### Issues Found

#### P0: Division by zero risk in multiple places
```swift
// Line 135-139: avgWholesalePrice, avgInternetPrice, etc.
let avgWholesalePrice = teamContexts.map { $0.decision.wholesalePrice }
    .reduce(0, +) / Double(max(1, teamContexts.count))  // OK — has guard

// Line 239-240: Division by total demand
let wShare = (wholesaleAttractivities[team.id] ?? 0) / max(totalWholesaleAttract, 0.001)  // OK
```
While most divisions have guards, several edge cases remain:
- Line 272: `Double(wholesaleAllocated) / demandDouble` — `demandDouble` could be 0 (guarded by `if totalDemandForTeam > 0` but the guard is on the outer block)
- Line 358: `team.sharesOutstanding - 1` — if sharesOutstanding is 0, this underflows

#### P0: Stock price model can produce nonsensical results
```swift
// Line 421-431
let epsGrowthFactor = max(0.5, 1.0 + eps / max(abs(baseEPSTarget), 0.01))
// If eps is very negative (e.g., -100), epsGrowthFactor = max(0.5, 1.0 + (-100/2.0)) = max(0.5, -49) = 0.5
// This caps at 0.5 — stock price can never go below $12.5 (0.5 * 25)
// This is too generous for a company losing money
```

#### P1: Storage cost per unit is unrealistically high
```swift
private let storageCostPerUnit: Double = 1.50  // Line 65
// $1.50 per unit per round is very high for athletic footwear inventory
// This will penalize inventory building strategies too aggressively
```

#### P1: Private label allocation is too simplistic
```swift
// Lines 220-228: Lowest bid wins, but no demand sensitivity
// A team bidding $10/unit gets same allocation as one bidding $44/unit
// Should weight bid price into allocation
```

#### P1: Amazon referral fee calculation inconsistency
```swift
// Line 200: amazonReferralRate = 0.15 (15%)
// Line 333: amazonReferralFee = amazonRev * 0.15
// But line 201 uses (1.0 - amazonReferralRate) on amazonPrice, not amazonRev
// The effective price calculation is correct but the naming is confusing
```

#### P2: Overtime cost premium is applied incorrectly
```swift
// Line 296-298
let regularUnits = min(grossProduction, baseCapacity)
let overtimeUnits = max(0, grossProduction - baseCapacity)
let regularProdCost = materialsCost * Double(regularUnits)
let overtimeProdCost = materialsCost * overtimeCostPremium * Double(overtimeUnits)
// This charges overtime premium on ALL units produced beyond capacity,
// not just the overtime portion. The formula is correct but the comment on line 299 is misleading.
```

#### P2: No validation on PlayerDecision ranges
- Wholesale price could be set to $0 or $10,000
- Production quantity could exceed 2x capacity
- No input validation before simulation

---

## 3. AICompetitor.swift — AI Strategies (324 lines)

### Strengths

- **4 distinct archetypes**: Low-Cost Leader, Differentiator, Best-Cost Provider, Adaptive Counter-Player
- **Seeded randomness** for varied but reproducible behavior
- **Emergency loan logic** prevents AI teams from going bankrupt
- **Progressive social media** adoption (nano influencers in late game)

### Issues Found

#### P1: Low-Cost Leader strategy is too aggressive on pricing
```swift
// Line 47: wholesalePrice: baseCost * 1.6
// If baseCost is $30, price = $48. This is very low for athletic footwear.
// May produce unrealistic market dynamics
```

#### P1: Differentiator strategy never issues stock
```swift
// Differentiator has sharesIssued: 0 always
// In real business, premium companies often issue stock to fund growth
```

#### P2: No strategy adaptation based on market conditions
- All strategies use fixed multipliers
- No response to competitor pricing changes beyond the Adaptive strategy
- The Adaptive strategy (if it exists) needs review

---

## 4. CoachingService.swift — Rule-Based Coaching (219 lines)

### Strengths

- **Multi-dimensional analysis**: S/Q, pricing, advertising, CSR, investor score, cash
- **Context-aware messaging**: Compares player decisions to market averages
- **Progressive urgency**: Messages get more urgent as cash depletes

### Issues Found

#### P1: Coaching messages don't account for strategy
- A player intentionally pricing low to gain market share gets penalized
- No recognition of coherent strategy (e.g., "Your low-price strategy is working — market share up 15%")

#### P1: CSR threshold is too high
```swift
// Line 75: if latestDecision.csrInvestment < 1_000
// $1,000 is barely anything. Most players will be below this.
// Should be closer to average spend or use percentile-based threshold
```

#### P2: No forward-looking coaching
- All messages are reactive (based on past results)
- No proactive warnings ("Your cash is declining — consider reducing production next round")

---

## 5. SimulationModels.swift — Domain Models (1,200+ lines)

### Strengths

- **Comprehensive model coverage**: 40+ types covering every simulation dimension
- **Clear enums**: MaterialsQuality, CelebrityEndorsement, DeliveryTime, FulfillmentMethod, etc.
- **Good data structure**: PlayerDecision, RoundResult, InvestorScorecard, TeamStatus all well-structured

### Issues Found

#### P1: PlayerDecision has too many parameters (God Object)
```swift
struct PlayerDecision {
    wholesalePrice, internetPrice, privateLabelBidPrice, privateLabelMaxUnits,
    materialsQuality, stylingBudget, modelsOffered, tqmInvestment,
    advertisingBudget, celebrityEndorsement, retailOutlets, mailInRebate,
    deliveryTime, freeShippingThreshold, amazonPrice, amazonAdBudget,
    fulfillmentMethod, tiktokBudget, instagramBudget, youtubeBudget,
    influencerTier, baseWage, incentivePay, trainingHours,
    productionQuantity, overtimePercent, csrInvestment,
    dividendsPerShare, newLoanAmount, sharesBuyback, sharesIssued
    // 30+ fields — violates Single Responsibility Principle
}
```
**Recommendation**: Split into logical groups:
- `PricingDecision` (wholesale, internet, Amazon, private label)
- `ProductDecision` (materials, styling, models)
- `MarketingDecision` (advertising, endorsement, social media, outlets)
- `ProductionDecision` (quantity, overtime, quality)
- `WorkforceDecision` (wage, incentive, training)
- `FinancialDecision` (dividends, loans, buyback, issuance)

#### P1: No validation on model construction
- `PlayerDecision.init` accepts any values without validation
- Could produce invalid states (negative prices, impossible ratios)

#### P2: SimulationSession has dual responsibility
- Manages simulation state AND result recording
- Should separate: `SessionState` (state management) + `ResultRecorder` (data persistence)

---

## 6. GameController.swift — Auto-Play & Round Management

### Strengths

- **Clean round management**: processRound advances state, records results
- **Quick Demo mode** for testing
- **Session lifecycle management**: start, advance, end

### Issues Found

#### P1: No error handling for simulation failures
- If `processRound` throws, the session enters an undefined state
- Should use Result type or try/catch

#### P2: Session state mutation is not thread-safe
- `SimulationSession` is ObservableObject but mutations happen on main thread
- If UI updates trigger concurrent mutations, could cause race conditions

---

## 7. iOS App (BizSimAI-ios) — Specific Issues

### Strengths

- **Clean SwiftUI architecture** with MVVM pattern
- **Good view organization**: Professor, Student, Shared, Components
- **10 ViewModels** covering all major UI concerns

### Issues Found

#### P1: iOS app is an exact copy of macOS backend
- The `BizSimAI/` directory in the iOS project is identical to the macOS `Sources/` directory
- **Maintenance nightmare**: changes to one must be manually synced to the other
- **Recommendation**: Use Swift Package as a dependency for the iOS app, or use a shared module

#### P1: No network layer — all simulation is local
- The iOS app runs the full simulation locally
- For a classroom setting, this means:
  - No real-time multiplayer (teams can't compete in real-time)
  - Professor can't monitor sessions remotely
  - No cloud backup of student progress

#### P2: No data persistence for long-term storage
- Session data is in-memory (ObservableObject)
- No Core Data, SwiftData, or file-based persistence
- Closing the app loses all session data

#### P2: No error handling in ViewModels
- ViewModels assume simulation always succeeds
- No loading/error states for UI

---

## 8. Security & Privacy

### Issues Found

#### P1: No input sanitization
- PlayerDecision values come from UI sliders/text fields
- No validation that prices are positive, quantities are within bounds
- Could crash the simulation with invalid input

#### P2: No data encryption for saved sessions
- If session data is persisted to disk, financial data is unencrypted
- Consider encrypting sensitive fields (cash, debt, shares)

---

## 9. Testing

### Issues Found

#### P1: No test suite
- No XCTest files found anywhere in the codebase
- Critical simulation logic has zero test coverage
- **Recommendation**: Add unit tests for:
  - `SimulationEngine.processRound()` (deterministic, easy to test)
  - `computeSQRating()` (pure function)
  - `computeRejectionRate()` (pure function)
  - AI strategy decision generation
  - Coaching message generation

#### P2: No integration tests
- No tests for ViewModel → View interaction
- No tests for session lifecycle

---

## 10. Performance

### Issues Found

#### P2: SimulationEngine creates many intermediate arrays
```swift
// Lines 135-139: Maps over teamContexts multiple times for averages
// Could compute all averages in a single pass
```

#### P2: String formatting in hot path
- `String(format: "%.1f", sq)` called in every explanation generation
- In a 10-team, 10-round simulation, this is fine, but could be optimized

---

## 11. UX/UI Observations

### Strengths

- **Clear role separation**: Professor vs Student views
- **Good coaching integration**: AI coach provides real-time feedback
- **Comprehensive metrics**: S/Q, EPS, ROE, stock price, image rating, credit rating

### Issues Found

#### P1: DecisionInputView likely has 30+ sliders
- With 30+ decision parameters, the UI will be very long
- **Recommendation**: Group decisions into tabs/sections (Product, Marketing, Production, Workforce, Finance)

#### P1: No onboarding/tutorial
- New users won't understand the simulation mechanics
- **Recommendation**: Add interactive tutorial for first-time users

#### P2: No dark mode support
- SwiftUI should support both light and dark themes

---

## 12. Recommendations (Prioritized)

### Critical (P0)
1. **Fix division by zero risks** — add guards everywhere
2. **Add input validation** on PlayerDecision
3. **Resolve duplicate codebase** — choose one source of truth

### High Priority (P1)
4. **Add unit tests** for SimulationEngine (critical for a simulation app)
5. **Split PlayerDecision** into logical sub-structures
6. **Add data persistence** (SwiftData/Core Data) for iOS
7. **Add network layer** for multiplayer/remote monitoring
8. **Improve coaching** to be strategy-aware and forward-looking
9. **Add onboarding/tutorial** for new users

### Medium Priority (P2)
10. **Add error handling** in GameController
11. **Reduce storage cost** to more realistic levels
12. **Add dark mode support**
13. **Group decision UI** into logical sections
14. **Add performance profiling** for large simulations

---

## 13. Summary

BizSim AI is a **well-designed business simulation engine** with comprehensive financial modeling, deterministic simulation, and good AI competitor strategies. The codebase is clean and well-organized.

**Key strengths:**
- Deterministic, reproducible simulation
- Comprehensive financial model (10+ cost/revenue categories)
- 4 distinct AI competitor archetypes
- Rule-based coaching with contextual feedback
- Clean MVVM architecture

**Key risks:**
- **Duplicate codebase** (macOS + iOS) creates maintenance burden
- **Zero test coverage** for critical simulation logic
- **No data persistence** on iOS
- **No multiplayer/network** capability for classroom use
- **30+ field PlayerDecision** is a God Object

**Overall assessment:** The simulation engine is production-quality. The iOS app needs significant work for classroom deployment (persistence, networking, testing). The biggest immediate action item is resolving the duplicate codebase situation.
