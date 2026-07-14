# BizSimAI Architecture Deep-Dive Fix Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fix the Quick Demo freeze AND wire up the real professor/student production flow so the app actually works end-to-end.

**Architecture:** Separate computation from observable state. `SimulationEngine.processRound()` currently mutates `SimulationSession` (a `@Model` class that JSON-encodes/decodes on every property access) directly, making background threading impossible and causing multi-second freezes. We create a snapshot → pure-compute → apply-back pattern. For production, we wire `RoundControlView` to actually call the game controller and backend.

**Tech Stack:** Swift 6, SwiftUI, SwiftData (`@Model`), `@Observable`, GCD

---

## Root Cause Analysis

### Problem 1: Quick Demo Freeze — JSON Encode/Decode Storm

`SimulationSession` is a SwiftData `@Model` class. Every computed property (`teams`, `config`, `roundResults`, `currentRoundDecisions`) is stored as a JSON `Data?` blob. **Every single read triggers a full `JSONDecoder().decode()`, and every single write triggers a full `JSONEncoder().encode()`.**

In `SimulationEngine.processRound()` (lines 81–538), per round:
- `session.config` → 1 decode
- `session.teams` → 1 decode (accessed 10+ times)
- `session.teams[index].x = y` → decode entire array, modify, re-encode entire array (happens 5+ times per team)
- `session.recordResult()` → decode `roundResults`, modify, re-encode + decode `teams`, modify, re-encode
- `session.updateRankings()` → decode `teams`, decode `roundResults` per team
- `session.currentRoundDecisions` → decode

**Per round: ~30 JSON encode/decode cycles. For 8 rounds: ~240 cycles.**
Each cycle is ~10–50ms → **2.4–12 seconds of pure JSON overhead**, blocking the main thread.

### Problem 2: `@Model` Observation Floods SwiftUI

Since `SimulationSession` is `@Model` (observable), every mutation notifies SwiftUI. With 30+ mutations per round × 8 rounds = 240+ SwiftUI re-render triggers. The main thread is drowned.

### Problem 3: `RunLoop.current.run(until:)` Doesn't Help

The computation for a single round takes 1–2 seconds. The 300ms inter-round delay is irrelevant — each round's computation itself blocks the main thread. `RunLoop.run(until:)` only yields during the delay, not during computation.

### Problem 4: Background Threading Impossible As-Is

`SimulationEngine.processRound()` directly mutates `SimulationSession` (`session.recordResult()`, `session.teams[index].x = y`, `session.updateRankings()`). Swift 6 strict concurrency forbids accessing `@Model`/`@Observable` objects from background threads. Every threading hack fails.

### Problem 5: `RoundControlView.advanceRound()` Is a Non-Functional Stub

```swift
// RoundControlView.swift line 289
private func advanceRound() {
    withAnimation(.spring(duration: 0.4)) {
        if isLastRound { endSession() }
        else {
            currentRound += 1          // ← just increments local @State
            teamSubmissions = ...      // ← just resets local array
        }
    }
}
```

It does NOT call:
- `session.advanceRound()`
- `gameController.processRoundAfterPlayerSubmit()`
- `NetworkService.advanceRound()`
- Any backend interaction at all

The professor can see a round counter increment, but no simulation runs, no results are generated, and no data goes to or from the backend.

### Problem 6: No Real Professor → Student Round Flow

There's no working mechanism for:
- Professor seeing which students have submitted decisions (reads from local `@State`, not from `session` or backend)
- Professor advancing the round (triggers AI decisions + simulation + backend sync)
- Results being pushed back to students after round advance

---

## Proposed Architecture

```
┌──────────────────────────────────────────────────────────┐
│ SimulationSession (@Model, @Observable, MAIN THREAD ONLY) │
│                                                          │
│  Only touched at boundaries:                             │
│  1. SNAPSHOT — copy all data to plain structs (1 read)   │
│  2. APPLY — write back results (1 write per property)    │
│                                                          │
│  Never accessed during computation.                      │
└──────────────┬──────────────────────────────┬──────────┘
               │                               │
               ▼                               ▲
    ┌─────────────────────┐          ┌─────────┘
    │ SimulationSnapshot  │          │ RoundOutput
    │ (plain struct)      │          │ (plain struct)
    │ - teams: [TeamStatus]│         │ - results: [RoundResult]
    │ - config: SessionConf│         │ - explanations: [ResultExpl]
    │ - roundResults: [...]│         │ - teamUpdates: [TeamUpdate]
    │ - decisions: [...]   │         │
    │ - currentRound: Int  │         │
    └─────────┬───────────┘          │
              │                       │
              ▼                       │
    ┌─────────────────────────────────┘
    │ SimulationEngine.processRoundPure()
    │ (plain class, no @Observable, BACKGROUND THREAD SAFE)
    │
    │ Takes: SimulationSnapshot + decisions
    │ Returns: RoundOutput
    │ Does NOT touch SimulationSession.
    └────────────────────────────┘
```

**Quick Demo flow (fixed):**
```
runQuickDemo():
  1. snapshot = session.takeSnapshot()        ← main thread, 1 bulk decode
  2. DispatchQueue.global().async:
     3. for each round:
        a. output = engine.processRoundPure(snapshot, decisions)
        b. DispatchQueue.main.async:
           c. session.applyRoundOutput(output)  ← main thread, 1 bulk encode
           d. update @Observable display props
        e. Thread.sleep(300ms)                 ← background, doesn't block UI
  4. DispatchQueue.main.async:
     5. isProcessing = false
```

**Production flow (fixed):**
```
Professor clicks "Advance Round":
  1. RoundControlView.advanceRound()
  2. → gameController.processRoundAfterPlayerSubmit()
  3. → session.submitDecision() for each AI team
  4. → snapshot = session.takeSnapshot()
  5. → DispatchQueue.global().async:
       engine.processRoundPure(snapshot, decisions)
  6. → DispatchQueue.main.async:
       session.applyRoundOutput(output)
  7. → BackendState.shared.advanceRound() (sync to backend)
  8. → students poll/fetch results from backend
```

---

## Task Breakdown

### Task 1: Create `SimulationSnapshot` and `RoundOutput` Structs

**Objective:** Plain `Sendable` value types that carry all data the engine needs and all data it produces.

**Files:**
- Create: `BizSimAI/Engine/SimulationSnapshot.swift`

**Step 1: Write the structs**

```swift
// SimulationSnapshot.swift
// BizSimAI
//
// Plain Sendable value types for background-thread simulation.
// Breaks the @Model/@Observable coupling so the engine can run
// off the main thread without Swift 6 concurrency violations.

import Foundation

/// Immutable snapshot of all data SimulationEngine.processRound() needs.
/// Created on the main thread, consumed on a background thread.
struct SimulationSnapshot: Sendable {
    let config: SessionConfiguration
    let currentRound: Int
    let teams: [TeamStatus]
    let decisions: [UUID: PlayerDecision]
    let previousRoundDecisions: [UUID: PlayerDecision]
    let roundResults: [UUID: [Int: RoundResult]]
}

/// A team status update produced by the simulation, to be applied
/// back to the @Model SimulationSession on the main thread.
struct TeamUpdate: Sendable {
    let teamId: UUID
    let cash: Double
    let inventory: Int
    let sqRating: Double
    let imageRating: Double
    let creditRating: CreditRating
    let reputation: Double
    let equity: Double
    let totalDebt: Double
    let sharesOutstanding: Int
    let cumulativeRD: Double
    let cumulativeMarketing: Double
    let cumulativeCSR: Double
    let cumulativeTQM: Double
    let cumulativeProfit: Double
    let cumulativeInvestorScore: Double
    let roundsScored: Int
    let hasSubmittedDecisions: Bool
    let rank: Int
}

/// All output from processing one round, to be applied on the main thread.
struct RoundOutput: Sendable {
    let round: Int
    let results: [RoundResult]
    let explanations: [ResultExplanation]
    let teamUpdates: [TeamUpdate]
    let updatedRoundResults: [UUID: [Int: RoundResult]]
}
```

**Step 2: Build to verify it compiles**

Run: `xcodebuild -project BizSimAI/BizSimAI.xcodeproj -scheme BizSimAI -destination 'platform=iOS,id=96BEAEB2-7A4C-5E79-AD11-D8718B2CA8D5' -configuration Debug -allowProvisioningUpdates build`
Expected: BUILD SUCCEEDED (structs compile, no logic changed)

---

### Task 2: Add `takeSnapshot()` and `applyRoundOutput()` to SimulationSession

**Objective:** Boundary methods on `SimulationSession` that bulk-copy data to/from plain structs, minimizing JSON encode/decode cycles.

**Files:**
- Modify: `BizSimAI/Models/SimulationSession.swift` (add methods at end of class, before closing `}`)

**Step 1: Add `takeSnapshot()` method**

Add this method to `SimulationSession` (e.g., after `func rank(for teamId:)`):

```swift
// MARK: - Snapshot / Apply (for background-thread simulation)

/// Bulk-copy all data the engine needs into a plain Sendable struct.
/// Call this ONCE on the main thread before dispatching to background.
/// This avoids 30+ individual JSON decode cycles during computation.
func takeSnapshot() -> SimulationSnapshot {
    let allDecisions = currentRoundDecisions
    let prevDecisions = previousRoundDecisions
    let allResults = roundResults
    return SimulationSnapshot(
        config: config,
        currentRound: currentRound,
        teams: teams,
        decisions: allDecisions,
        previousRoundDecisions: prevDecisions,
        roundResults: allResults
    )
}
```

**Step 2: Add `applyRoundOutput()` method**

```swift
/// Apply simulation results back to the @Model session.
/// Call this ONCE on the main thread after background computation.
/// Performs a single bulk encode per property (not 30+ decode/encode cycles).
func applyRoundOutput(_ output: RoundOutput) {
    // Record results (triggers team status updates internally)
    for result in output.results {
        recordResult(result)
    }

    // Apply team updates (single encode of teams array)
    var updatedTeams = teams
    for update in output.teamUpdates {
        if let index = updatedTeams.firstIndex(where: { $0.id == update.teamId }) {
            updatedTeams[index].cash = update.cash
            updatedTeams[index].inventory = update.inventory
            updatedTeams[index].sqRating = update.sqRating
            updatedTeams[index].imageRating = update.imageRating
            updatedTeams[index].creditRating = update.creditRating
            updatedTeams[index].reputation = update.reputation
            updatedTeams[index].equity = update.equity
            updatedTeams[index].totalDebt = update.totalDebt
            updatedTeams[index].sharesOutstanding = update.sharesOutstanding
            updatedTeams[index].cumulativeRD = update.cumulativeRD
            updatedTeams[index].cumulativeMarketing = update.cumulativeMarketing
            updatedTeams[index].cumulativeCSR = update.cumulativeCSR
            updatedTeams[index].cumulativeTQM = update.cumulativeTQM
            updatedTeams[index].cumulativeProfit = update.cumulativeProfit
            updatedTeams[index].cumulativeInvestorScore = update.cumulativeInvestorScore
            updatedTeams[index].roundsScored = update.roundsScored
            updatedTeams[index].rank = update.rank
        }
    }
    teams = updatedTeams  // single encode

    // Update rankings
    updateRankings()
}
```

**Step 3: Build to verify**

Run: same xcodebuild command
Expected: BUILD SUCCEEDED

---

### Task 3: Add `processRoundPure()` to SimulationEngine

**Objective:** A pure-computation version of `processRound()` that takes a `SimulationSnapshot` + decisions, returns `RoundOutput`, and NEVER touches `SimulationSession`. Safe to run on a background thread.

**Files:**
- Modify: `BizSimAI/Engine/SimulationEngine.swift` (add method after existing `processRound()`)

**Step 1: Add the pure method**

Add this after the existing `processRound()` method (after line 538):

```swift
// MARK: - Pure Computation (background-thread safe)

/// Process a round WITHOUT touching SimulationSession.
/// Takes a snapshot + decisions, returns all results + team updates.
/// Safe to call on a background thread.
func processRoundPure(
    snapshot: SimulationSnapshot,
    decisions: [UUID: PlayerDecision]
) -> RoundOutput {
    let config = snapshot.config
    let round = snapshot.currentRound
    var rng = SeededRandomGenerator(seed: config.randomSeed &+ UInt64(round))

    // 1. Build team contexts and compute S/Q ratings
    var teamSQRatings: [UUID: Double] = [:]
    var teamRejectionRates: [UUID: Double] = [:]
    var teamContexts: [(team: TeamStatus, decision: PlayerDecision)] = []

    for team in snapshot.teams {
        guard let decision = decisions[team.id] else { continue }

        let updatedCumulativeTQM = team.cumulativeTQM + decision.tqmInvestment

        let sqRating = computeSQRating(
            materialsQuality: decision.materialsQuality,
            stylingBudget: decision.stylingBudget,
            modelsOffered: decision.modelsOffered,
            cumulativeTQM: updatedCumulativeTQM,
            bestPractices: decision.bestPracticesInvestment,
            trainingHours: decision.trainingHours,
            previousSQ: team.sqRating
        )
        teamSQRatings[team.id] = sqRating

        let rejectionRate = computeRejectionRate(
            cumulativeTQM: updatedCumulativeTQM,
            trainingHours: decision.trainingHours,
            incentivePay: decision.incentivePay,
            bestPractices: decision.bestPracticesInvestment
        )
        teamRejectionRates[team.id] = rejectionRate

        teamContexts.append((team, decision))
    }

    // 2. Compute total market demand
    let demandGrowth = min(2.0, 1.0 + 0.05 * Double(round))
    let totalDemand = Double(config.baseMarketDemand)
        * config.marketType.demandMultiplier
        * demandGrowth
        * rng.noiseFactor(amplitude: config.marketType.volatility)

    let wholesaleDemand = totalDemand * wholesaleShare
    let internetDemand = totalDemand * internetShare
    let privateLabelDemand = totalDemand * privateLabelShare
    let amazonDemand = totalDemand * amazonShare

    // 3. Compute competitive indices (same as processRound)
    let avgWholesalePrice = teamContexts.map { $0.decision.wholesalePrice }.reduce(0, +) / Double(max(1, teamContexts.count))
    let avgInternetPrice = teamContexts.map { $0.decision.internetPrice }.reduce(0, +) / Double(max(1, teamContexts.count))
    let avgSQ = teamSQRatings.values.reduce(0, +) / Double(max(1, teamSQRatings.count))
    let avgAdvertising = teamContexts.map { $0.decision.advertisingBudget }.reduce(0, +) / Double(max(1, teamContexts.count))
    let avgRebate = teamContexts.map { $0.decision.mailInRebate }.reduce(0, +) / Double(max(1, teamContexts.count))

    var wholesaleAttractivities: [UUID: Double] = [:]
    var internetAttractivities: [UUID: Double] = [:]
    var amazonAttractivities: [UUID: Double] = [:]

    for (team, decision) in teamContexts {
        let sq = teamSQRatings[team.id] ?? 5.0

        let tiktokFactor = 1.0 + min(0.08, decision.tiktokBudget / 15_000 * 0.08)
        let instagramFactor = 1.0 + min(0.06, decision.instagramBudget / 15_000 * 0.06)
        let youtubeFactor = 1.0 + min(0.05, decision.youtubeBudget / 15_000 * 0.05)
        let estInfluencerCount: Double
        if decision.socialMediaBudget <= 0 {
            estInfluencerCount = 0
        } else {
            switch decision.influencerTier {
            case .none: estInfluencerCount = 0
            case .nano: estInfluencerCount = Double(max(1, Int(decision.socialMediaBudget / 1000)))
            case .micro: estInfluencerCount = Double(max(1, Int(decision.socialMediaBudget / 5000)))
            case .macro: estInfluencerCount = Double(max(1, Int(decision.socialMediaBudget / 20000)))
            case .mega: estInfluencerCount = Double(max(1, Int(decision.socialMediaBudget / 60000)))
            }
        }
        let influencerCountFactor = max(1, sqrt(estInfluencerCount))
        let influencerFactor = 1.0 + decision.influencerTier.engagementRate * decision.influencerTier.reachMultiplier * 0.1 * influencerCountFactor
        let socialMediaDemandBoost = tiktokFactor * instagramFactor * youtubeFactor * influencerFactor

        let effectivePrice = decision.wholesalePrice - decision.mailInRebate * 0.6
        let avgEffectivePrice = avgWholesalePrice - avgRebate * 0.6
        let priceAttract = pow(max(avgEffectivePrice, 1) / max(effectivePrice, 1), priceElasticity)
        let sqAttract = pow(sq / max(avgSQ, 1), sqWeight)
        let adAttract = pow(max(decision.advertisingBudget, 100) / max(avgAdvertising, 100), advertisingWeight)
        let outletFactor = 1.0 + Double(decision.retailOutlets) / 100.0 * outletsWeight
        let endorseFactor = decision.celebrityEndorsement.demandBoost
        let reputationFactor = 0.7 + 0.6 * team.reputation
        let deliveryFactor = decision.deliveryTime.demandBoost

        wholesaleAttractivities[team.id] = priceAttract * sqAttract * adAttract
            * outletFactor * endorseFactor * reputationFactor * deliveryFactor
            * socialMediaDemandBoost
            * rng.noiseFactor(amplitude: noiseAmplitude)

        let iPriceAttract = pow(max(avgInternetPrice, 1) / max(decision.internetPrice, 1), priceElasticity * 0.9)
        let iSQAttract = pow(sq / max(avgSQ, 1), sqWeight * 1.1)
        let freeShipBoost = 1.0 + max(0, (100 - decision.freeShippingThreshold) / 200.0)

        internetAttractivities[team.id] = iPriceAttract * iSQAttract * adAttract
            * endorseFactor * reputationFactor * freeShipBoost
            * socialMediaDemandBoost
            * rng.noiseFactor(amplitude: noiseAmplitude)

        let amazonReferralRate = 0.15
        let amazonEffectivePrice = decision.amazonPrice * (1.0 - amazonReferralRate)
        let avgAmazonPrice = teamContexts.map { $0.decision.amazonPrice }.reduce(0, +) / Double(max(1, teamContexts.count))
        let avgAmazonEffective = avgAmazonPrice * (1.0 - amazonReferralRate)
        let aPriceAttract = pow(max(avgAmazonEffective, 1) / max(amazonEffectivePrice, 1), priceElasticity * 0.8)
        let aReviewProxy = pow(sq / max(avgSQ, 1), sqWeight * 1.2)
        let aAdBoost = 1.0 + min(0.15, decision.amazonAdBudget / 10_000 * 0.15)
        let aBuyBox = decision.fulfillmentMethod.buyBoxMultiplier
        let aTrust = decision.fulfillmentMethod.trustMultiplier

        amazonAttractivities[team.id] = aPriceAttract * aReviewProxy * aAdBoost
            * aBuyBox * aTrust * socialMediaDemandBoost
            * rng.noiseFactor(amplitude: noiseAmplitude)
    }

    let totalWholesaleAttract = wholesaleAttractivities.values.reduce(0, +)
    let totalInternetAttract = internetAttractivities.values.reduce(0, +)
    let totalAmazonAttract = amazonAttractivities.values.reduce(0, +)

    // 4. Private-label allocation (lowest bid wins)
    let privateLabelBids = teamContexts.sorted { $0.decision.privateLabelBidPrice < $1.decision.privateLabelBidPrice }
    var privateLabelAllocations: [UUID: Int] = [:]
    var remainingPL = Int(privateLabelDemand)
    for (team, decision) in privateLabelBids {
        if remainingPL <= 0 { break }
        let allocation = min(decision.privateLabelMaxUnits, remainingPL)
        privateLabelAllocations[team.id] = allocation
        remainingPL -= allocation
    }

    // 5. Compute results for each team
    var results: [RoundResult] = []
    var explanations: [ResultExplanation] = []
    var teamUpdates: [TeamUpdate] = []
    var updatedRoundResults = snapshot.roundResults

    for (team, decision) in teamContexts {
        let sq = teamSQRatings[team.id] ?? 5.0
        let rejectionRate = teamRejectionRates[team.id] ?? 0.08

        let wShare = (wholesaleAttractivities[team.id] ?? 0) / max(totalWholesaleAttract, 0.001)
        let iShare = (internetAttractivities[team.id] ?? 0) / max(totalInternetAttract, 0.001)
        let wholesaleAllocated = Int(wholesaleDemand * wShare)
        let internetAllocated = Int(internetDemand * iShare)
        let plAllocated = privateLabelAllocations[team.id] ?? 0

        let aShare = (amazonAttractivities[team.id] ?? 0) / max(totalAmazonAttract, 0.001)
        let amazonAllocated = Int(amazonDemand * aShare)

        let baseCapacity = config.plantCapacity
        let overtimeCapacity = Int(Double(baseCapacity) * decision.overtimePercent / 100.0)
        let totalCapacity = baseCapacity + overtimeCapacity

        let grossProduction = min(decision.productionQuantity, totalCapacity)
        let rejectedUnits = Int(Double(grossProduction) * rejectionRate)
        let netProduction = grossProduction - rejectedUnits

        let totalAvailable = netProduction + team.inventory
        let totalDemandForTeam = wholesaleAllocated + internetAllocated + amazonAllocated + plAllocated

        let capForSale = min(totalDemandForTeam, totalAvailable)
        let wSold: Int, iSold: Int, aSold: Int, plSold: Int

        if totalDemandForTeam > 0 {
            let capDouble = Double(capForSale)
            let demandDouble = Double(totalDemandForTeam)
            wSold = min(wholesaleAllocated, Int(capDouble * Double(wholesaleAllocated) / demandDouble))
            let afterW = capForSale - wSold
            let remainDemand3 = Double(amazonAllocated + internetAllocated + plAllocated)
            aSold = min(amazonAllocated, remainDemand3 > 0 ? Int(Double(afterW) * Double(amazonAllocated) / remainDemand3) : 0)
            let afterWA = afterW - aSold
            let remainDemand2 = Double(internetAllocated + plAllocated)
            iSold = min(internetAllocated, remainDemand2 > 0 ? Int(Double(afterWA) * Double(internetAllocated) / remainDemand2) : 0)
            plSold = min(plAllocated, capForSale - wSold - aSold - iSold)
        } else {
            wSold = 0; iSold = 0; aSold = 0; plSold = 0
        }
        let totalSold = wSold + iSold + aSold + plSold

        let wholesaleRev = Double(wSold) * decision.wholesalePrice
        let internetRev = Double(iSold) * decision.internetPrice
        let privateLabelRev = Double(plSold) * decision.privateLabelBidPrice
        let amazonRev = Double(aSold) * decision.amazonPrice

        let materialsCost = config.baseCostPerUnit * decision.materialsQuality.costMultiplier
        let regularUnits = min(grossProduction, baseCapacity)
        let overtimeUnits = max(0, grossProduction - baseCapacity)
        let regularProdCost = materialsCost * Double(regularUnits)
        let overtimeProdCost = materialsCost * overtimeCostPremium * Double(overtimeUnits)

        if grossProduction == 0 {
            let previousStock = updatedRoundResults[team.id]?[round - 1]?.scorecard.stockPrice ?? baseStockTarget
            let zeroScorecard = InvestorScorecard(
                round: round, eps: 0, roe: 0, stockPrice: previousStock,
                imageRating: team.imageRating, creditRating: team.creditRating,
                epsScore: 0, roeScore: 0, stockPriceScore: 0,
                imageScore: 0, creditScore: Double(team.creditRating.investorScore)
            )
            let zeroResult = RoundResult(
                teamId: team.id, round: round,
                wholesaleRevenue: 0, internetRevenue: 0, amazonRevenue: 0, privateLabelRevenue: 0,
                productionCosts: config.fixedCostsPerRound, marketingCosts: 0, csrCosts: 0,
                endorsementCosts: 0, interestExpense: 0, dividendsPaid: 0,
                workforceCosts: 0, storageCosts: 0, rebateCosts: 0, deliveryCosts: 0,
                socialMediaCosts: 0, amazonFees: 0,
                wholesaleUnitsSold: 0, internetUnitsSold: 0, amazonUnitsSold: 0, privateLabelUnitsSold: 0,
                marketShare: 0, customerSatisfaction: 0, inventory: team.inventory,
                rejectionRate: 0, cash: team.cash - config.fixedCostsPerRound, sqRating: sq,
                awarenessScore: 0, scorecard: zeroScorecard
            )
            results.append(zeroResult)

            if updatedRoundResults[team.id] == nil { updatedRoundResults[team.id] = [:] }
            updatedRoundResults[team.id]?[round] = zeroResult

            teamUpdates.append(TeamUpdate(
                teamId: team.id, cash: team.cash - config.fixedCostsPerRound,
                inventory: team.inventory, sqRating: sq,
                imageRating: team.imageRating, creditRating: team.creditRating,
                reputation: team.reputation, equity: team.equity, totalDebt: team.totalDebt,
                sharesOutstanding: team.sharesOutstanding, cumulativeRD: team.cumulativeRD,
                cumulativeMarketing: team.cumulativeMarketing, cumulativeCSR: team.cumulativeCSR,
                cumulativeTQM: team.cumulativeTQM, cumulativeProfit: team.cumulativeProfit,
                cumulativeInvestorScore: team.cumulativeInvestorScore, roundsScored: team.roundsScored,
                hasSubmittedDecisions: false, rank: team.rank
            ))
            continue
        }

        let totalProdCost = regularProdCost + overtimeProdCost
            + config.fixedCostsPerRound + decision.stylingBudget
            + decision.tqmInvestment + decision.bestPracticesInvestment

        let workersNeeded = max(1, grossProduction / 10)
        let wageCost = decision.baseWage * Double(workersNeeded) / 1000.0
        let incentiveCost = decision.incentivePay * Double(grossProduction)
        let trainingCost = decision.trainingHours * 50.0 * Double(workersNeeded) / 1000.0
        let workforceCosts = wageCost + incentiveCost + trainingCost

        let marketingCost = decision.advertisingBudget + Double(decision.retailOutlets) * 50
        let csrCost = decision.csrInvestment
        let endorseCost = decision.celebrityEndorsement.annualCost

        let influencerCount: Int
        if decision.socialMediaBudget <= 0 {
            influencerCount = 0
        } else {
            switch decision.influencerTier {
            case .none: influencerCount = 0
            case .nano: influencerCount = max(1, Int(decision.socialMediaBudget / 1000))
            case .micro: influencerCount = max(1, Int(decision.socialMediaBudget / 5000))
            case .macro: influencerCount = max(1, Int(decision.socialMediaBudget / 20000))
            case .mega: influencerCount = max(1, Int(decision.socialMediaBudget / 60000))
            }
        }
        let influencerCost = Double(influencerCount) * decision.influencerTier.costPerInfluencer
        let socialMediaTotalCost = decision.socialMediaBudget + influencerCost

        let amazonReferralFee = amazonRev * 0.15
        let amazonFulfillmentFee = decision.fulfillmentMethod.feePerUnit * Double(aSold)
        let amazonAdCost = decision.amazonAdBudget
        let totalAmazonFees = amazonReferralFee + amazonFulfillmentFee + amazonAdCost

        let rebateRedemptionRate = 0.6
        let rebateCosts = decision.mailInRebate * rebateRedemptionRate * Double(wSold)
        let deliveryCosts = decision.deliveryTime.costPerUnit * Double(wSold)
        let freeShipRate = max(0, min(1.0, (100 - decision.freeShippingThreshold) / 100.0))
        let internetShippingCost = Double(iSold) * 5.0 * freeShipRate

        let newInventory = max(0, totalAvailable - totalSold)
        let storageCosts = storageCostPerUnit * Double(newInventory)

        let interestRate = baseInterestRate * team.creditRating.interestRateMultiplier
        let interestExpense = team.totalDebt * interestRate

        let safeBuyback = min(decision.sharesBuyback, team.sharesOutstanding - 1)
        let newShares = max(1, team.sharesOutstanding - safeBuyback + decision.sharesIssued)
        let dividendsPaid = decision.dividendsPerShare * Double(newShares)

        let issuancePrice = max(5, team.cumulativeInvestorScore > 0 ? team.cumulativeInvestorScore / 2 : 15)
        let issuanceProceeds = Double(decision.sharesIssued) * issuancePrice

        let totalRevenue = wholesaleRev + internetRev + amazonRev + privateLabelRev
        let totalCosts = totalProdCost + workforceCosts + marketingCost + csrCost
            + endorseCost + rebateCosts + deliveryCosts + internetShippingCost + storageCosts
            + interestExpense + dividendsPaid + socialMediaTotalCost + totalAmazonFees

        let profit = totalRevenue - totalCosts

        let prevStockForBuyback = updatedRoundResults[team.id]?[round - 1]?.scorecard.stockPrice ?? 25.0
        let buybackCost = Double(safeBuyback) * max(5, prevStockForBuyback)
        let cashChange = profit - buybackCost + decision.newLoanAmount + issuanceProceeds
        let newCash = team.cash + cashChange
        let newDebt = max(0, team.totalDebt + decision.newLoanAmount)
        let newEquity = max(1, team.equity + profit)

        let marketShare = Double(totalSold) / max(totalDemand, 1)

        let priceFairness = min(1.0, avgWholesalePrice / max(decision.wholesalePrice, 1))
        let supplyAdequacy = totalDemandForTeam > 0 ? min(1.0, Double(totalSold) / Double(totalDemandForTeam)) : 0.5
        let satisfaction = min(1.0, max(0.0,
            0.35 * (sq / 10.0) + 0.3 * priceFairness + 0.2 * supplyAdequacy + 0.15 * team.reputation))
        let newReputation = 0.7 * team.reputation + 0.3 * satisfaction

        let eps = profit / Double(newShares)
        let roe = profit / newEquity
        let debtToEquity = newEquity > 0 ? newDebt / newEquity : 10
        let interestCoverage = interestExpense > 0 ? max(0, profit + interestExpense) / interestExpense : 20
        let cashRatio = newDebt > 0 ? newCash / newDebt : 5

        let creditRating = CreditRating.fromFinancials(
            debtToEquity: debtToEquity, interestCoverage: interestCoverage, cashRatio: cashRatio)

        let sqImageContrib = sq * 5.0
        let adImageContrib = min(15, decision.advertisingBudget / 2000.0 * 5)
        let csrImageContrib = min(15, decision.csrInvestment / 2000.0 * 5)
        let endorseImageContrib = decision.celebrityEndorsement.imageBoost
        let modelsImageContrib = min(10, Double(decision.modelsOffered) * 2)
        let workforceImageContrib = min(5, decision.trainingHours / 40.0 * 5)
        let instagramImageContrib = min(8, decision.instagramBudget / 10_000 * 8)
        let tiktokImageContrib = min(4, decision.tiktokBudget / 10_000 * 4)
        let youtubeImageContrib = min(5, decision.youtubeBudget / 10_000 * 5)
        let influencerImageContrib = decision.influencerTier.imageBoost
        let imageRating = min(100, sqImageContrib + adImageContrib + csrImageContrib
            + endorseImageContrib + modelsImageContrib + workforceImageContrib
            + instagramImageContrib + tiktokImageContrib + youtubeImageContrib + influencerImageContrib)

        let epsGrowthFactor = max(0.5, 1.0 + eps / max(abs(baseEPSTarget), 0.01))
        let roeFactor = max(0.5, 1.0 + roe)
        let previousStockPrice = updatedRoundResults[team.id]?[round - 1]?.scorecard.stockPrice ?? baseStockTarget
        let dividendYield = decision.dividendsPerShare / max(1, previousStockPrice)
        let creditFactor = creditRating.investorScore / 20.0
        let dilutionPenalty = decision.sharesIssued > 0 ? max(0.85, 1.0 - Double(decision.sharesIssued) / Double(max(1, team.sharesOutstanding)) * 0.5) : 1.0
        let rawStockPrice = max(1, baseStockTarget * epsGrowthFactor * roeFactor
            * (1 + dividendYield) * creditFactor * dilutionPenalty
            * rng.noiseFactor(amplitude: 0.03))
        let stockPrice = round > 1 ? 0.4 * previousStockPrice + 0.6 * rawStockPrice : rawStockPrice

        let ratchetMultiplier = pow(1.0 + targetRatchetRate, Double(round))
        let epsTarget = baseEPSTarget * ratchetMultiplier
        let roeTarget = baseROETarget * ratchetMultiplier
        let stockTarget = baseStockTarget * ratchetMultiplier
        let imageTarget = min(90, baseImageTarget * (1.0 + 0.03 * Double(round)))

        let epsScore = min(20, max(0, 20 * eps / max(epsTarget, 0.01)))
        let roeScore = min(20, max(0, 20 * roe / max(roeTarget, 0.001)))
        let stockPriceScore = min(20, max(0, 20 * stockPrice / max(stockTarget, 1)))
        let imageScore = min(20, max(0, 20 * imageRating / max(imageTarget, 1)))
        let creditScore = creditRating.investorScore

        let scorecard = InvestorScorecard(
            round: round, eps: eps, roe: roe, stockPrice: stockPrice,
            imageRating: imageRating, creditRating: creditRating,
            epsScore: epsScore, roeScore: roeScore, stockPriceScore: stockPriceScore,
            imageScore: imageScore, creditScore: creditScore)

        let result = RoundResult(
            teamId: team.id, round: round,
            wholesaleRevenue: wholesaleRev, internetRevenue: internetRev,
            amazonRevenue: amazonRev, privateLabelRevenue: privateLabelRev,
            productionCosts: totalProdCost, marketingCosts: marketingCost,
            csrCosts: csrCost, endorsementCosts: endorseCost,
            interestExpense: interestExpense, dividendsPaid: dividendsPaid,
            workforceCosts: workforceCosts, storageCosts: storageCosts,
            rebateCosts: rebateCosts, deliveryCosts: deliveryCosts + internetShippingCost,
            socialMediaCosts: socialMediaTotalCost, amazonFees: totalAmazonFees,
            wholesaleUnitsSold: wSold, internetUnitsSold: iSold,
            amazonUnitsSold: aSold, privateLabelUnitsSold: plSold,
            marketShare: marketShare, customerSatisfaction: satisfaction,
            inventory: newInventory, rejectionRate: rejectionRate,
            cash: newCash, sqRating: sq,
            awarenessScore: min(1, (decision.advertisingBudget + decision.socialMediaBudget) / 25000),
            scorecard: scorecard)

        results.append(result)

        // Store in updated results map
        if updatedRoundResults[team.id] == nil { updatedRoundResults[team.id] = [:] }
        updatedRoundResults[team.id]?[round] = result

        // Compute team update
        let prevTotal = team.cumulativeInvestorScore * Double(team.roundsScored)
        let newRoundsScored = team.roundsScored + 1
        let newCumInvestorScore = (prevTotal + scorecard.totalScore) / Double(newRoundsScored)

        teamUpdates.append(TeamUpdate(
            teamId: team.id, cash: newCash, inventory: newInventory,
            sqRating: sq, imageRating: imageRating, creditRating: creditRating,
            reputation: newReputation, equity: newEquity, totalDebt: newDebt,
            sharesOutstanding: newShares,
            cumulativeRD: team.cumulativeRD + decision.stylingBudget,
            cumulativeMarketing: team.cumulativeMarketing + decision.advertisingBudget,
            cumulativeCSR: team.cumulativeCSR + decision.csrInvestment,
            cumulativeTQM: team.cumulativeTQM + decision.tqmInvestment,
            cumulativeProfit: team.cumulativeProfit + profit,
            cumulativeInvestorScore: newCumInvestorScore,
            roundsScored: newRoundsScored,
            hasSubmittedDecisions: false, rank: team.rank))

        if !team.isAI {
            explanations = generateExplanations(
                decision: decision, result: result, sq: sq,
                avgPrice: avgWholesalePrice, marketShare: marketShare,
                rejectionRate: rejectionRate)
        }
    }

    return RoundOutput(
        round: round, results: results, explanations: explanations,
        teamUpdates: teamUpdates, updatedRoundResults: updatedRoundResults)
}
```

**Step 2: Build**

Run: same xcodebuild
Expected: BUILD SUCCEEDED

---

### Task 4: Rewrite `GameController.runQuickDemo()` Using Snapshot + Background Compute

**Objective:** The Quick Demo now takes a snapshot, dispatches computation to a background thread, and applies results on the main thread. UI never freezes.

**Files:**
- Modify: `BizSimAI/Engine/GameController.swift` (replace `runQuickDemo()` method)

**Step 1: Replace `runQuickDemo()` with the snapshot-based version**

Replace the entire `runQuickDemo()` method with:

```swift
/// Runs the entire simulation automatically with preset player decisions.
/// ARCHITECTURE: Snapshot → Background Compute → Main-Thread Apply
/// 1. Take a snapshot of session state (1 bulk JSON decode, main thread)
/// 2. Dispatch computation to background thread (DispatchQueue.global)
/// 3. After each round, hop to main thread to apply results (1 bulk JSON encode)
/// 4. UI never freezes — main thread is free between rounds
func runQuickDemo() {
    guard !isProcessing else { return }
    isProcessing = true

    let totalRounds = session.config.totalRounds

    // Step 1: Take initial snapshot (main thread, bulk decode)
    var workingSnapshot = session.takeSnapshot()

    // Step 2: Run all rounds on background thread
    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
        guard let self else { return }

        var allResults: [RoundResult] = []
        var allExplanations: [ResultExplanation] = []
        var allPlayerSummaries: [RoundSummary] = []
        var finalTeamUpdates: [TeamUpdate] = []
        var finalRoundResults = workingSnapshot.roundResults

        for round in 1...totalRounds {
            guard workingSnapshot.currentRound <= totalRounds else { break }

            // Generate player decision
            guard let playerTeamId = workingSnapshot.teams.first(where: { !$0.isAI })?.id else { break }
            let playerDecision = self.generateDemoPlayerDecision(teamId: playerTeamId, round: round)

            // Build decisions map for this round
            var roundDecisions = workingSnapshot.decisions
            roundDecisions[playerTeamId] = playerDecision

            // Generate AI decisions
            let avgWholesale = playerDecision.wholesalePrice
            let avgInternet = playerDecision.internetPrice

            for team in workingSnapshot.teams where team.isAI {
                let competitorProfits = workingSnapshot.teams.reduce(into: [UUID: Double]()) { dict, t in
                    dict[t.id] = t.cumulativeTQM
                }
                let context = AIDecisionContext(
                    config: workingSnapshot.config,
                    team: team,
                    playerPreviousDecision: nil,
                    roundsRemaining: totalRounds - round,
                    competitorProfits: competitorProfits,
                    averageWholesalePrice: avgWholesale,
                    averageInternetPrice: avgInternet
                )
                var rng = SeededRandomGenerator(
                    seed: workingSnapshot.config.randomSeed
                    &+ UInt64(round)
                    &+ UInt64(bitPattern: Int64(team.id.hashValue)))
                let aiDecision = self.aiCompetitors
                    .first(where: { $0.teamId == team.id })?
                    .strategy
                    .makeDecisions(teamId: team.id, round: round, context: context, rng: &rng)
                if let aiDecision { roundDecisions[team.id] = aiDecision }
            }

            // Update snapshot with round decisions
            workingSnapshot = SimulationSnapshot(
                config: workingSnapshot.config,
                currentRound: round,
                teams: workingSnapshot.teams,
                decisions: roundDecisions,
                previousRoundDecisions: workingSnapshot.previousRoundDecisions,
                roundResults: finalRoundResults
            )

            // Step 3a: Run pure computation (background thread, NO @Model access)
            let output = self.engine.processRoundPure(
                snapshot: workingSnapshot, decisions: roundDecisions)

            allResults.append(contentsOf: output.results)
            allExplanations.append(contentsOf: output.explanations)
            finalTeamUpdates = output.teamUpdates
            finalRoundResults = output.updatedRoundResults

            // Collect player summary
            if let pResult = output.results.first(where: { $0.teamId == playerTeamId }) {
                allPlayerSummaries.append(
                    RoundSummary(from: pResult, price: playerDecision.wholesalePrice))
            }

            // Update teams in the working snapshot for next round
            var updatedTeams = workingSnapshot.teams
            for update in output.teamUpdates {
                if let idx = updatedTeams.firstIndex(where: { $0.id == update.teamId }) {
                    updatedTeams[idx].cash = update.cash
                    updatedTeams[idx].inventory = update.inventory
                    updatedTeams[idx].sqRating = update.sqRating
                    updatedTeams[idx].imageRating = update.imageRating
                    updatedTeams[idx].creditRating = update.creditRating
                    updatedTeams[idx].reputation = update.reputation
                    updatedTeams[idx].equity = update.equity
                    updatedTeams[idx].totalDebt = update.totalDebt
                    updatedTeams[idx].sharesOutstanding = update.sharesOutstanding
                    updatedTeams[idx].cumulativeRD = update.cumulativeRD
                    updatedTeams[idx].cumulativeMarketing = update.cumulativeMarketing
                    updatedTeams[idx].cumulativeCSR = update.cumulativeCSR
                    updatedTeams[idx].cumulativeTQM = update.cumulativeTQM
                    updatedTeams[idx].cumulativeProfit = update.cumulativeProfit
                    updatedTeams[idx].cumulativeInvestorScore = update.cumulativeInvestorScore
                    updatedTeams[idx].roundsScored = update.roundsScored
                }
            }

            // Update AI competitor tracking (on main thread later)
            // Prepare next round snapshot
            let prevDecisions = roundDecisions
            workingSnapshot = SimulationSnapshot(
                config: workingSnapshot.config,
                currentRound: round + 1,
                teams: updatedTeams,
                decisions: [:],
                previousRoundDecisions: prevDecisions,
                roundResults: finalRoundResults
            )

            // Step 3b: Apply results to @Model session on MAIN THREAD
            // (between rounds, so UI can update)
            DispatchQueue.main.sync {
                self.session.applyRoundOutput(output)
                self.lastRoundResults = output.results
                self.latestExplanations = output.explanations

                // Update AI tracking
                for result in output.results {
                    if let idx = self.aiCompetitors.firstIndex(where: { $0.teamId == result.teamId }) {
                        self.aiCompetitors[idx].updateFromResult(result)
                    }
                }

                // Add player summaries
                if let pSum = allPlayerSummaries.last {
                    self.session.playerRoundSummaries.append(pSum)
                }
            }

            // 300ms delay between rounds (background thread, doesn't block UI)
            Thread.sleep(forTimeInterval: 0.3)
        }

        // Step 4: Mark complete on main thread
        DispatchQueue.main.async {
            self.isProcessing = false
        }
    }
}
```

**Step 2: Build**

Run: same xcodebuild
Expected: BUILD SUCCEEDED

**Step 3: Install on device and test**

Run: `xcodebuild ... install`
Then: Launch app → login `test1`/`Test@1234` → Quick Demo → tap blue button
Expected: UI stays responsive, rounds appear one by one, no freeze

---

### Task 5: Wire `RoundControlView.advanceRound()` to Actually Run the Simulation

**Objective:** When the professor clicks "Advance Round", the game controller actually processes the round (AI decisions + simulation), not just increments a local counter.

**Files:**
- Modify: `BizSimAI/Views/Professor/RoundControlView.swift` (replace `advanceRound()`)

**Step 1: Replace `advanceRound()` method**

Replace the existing `advanceRound()` (line 289) with:

```swift
private func advanceRound() {
    guard let session = appState.activeSession else { return }
    guard let gameController = appState.gameController else { return }

    if isLastRound {
        endSession()
        return
    }

    // Disable button during processing
    isProcessing = true

    // Run AI decisions + simulation via game controller
    // This uses the same snapshot→background→apply pattern
    DispatchQueue.global(qos: .userInitiated).async {
        // Generate AI decisions and process round
        gameController.processRoundAfterPlayerSubmit()

        DispatchQueue.main.async {
            self.isProcessing = false
            self.loadFromSession()
        }
    }
}

@State private var isProcessing: Bool = false
```

**Step 2: Update the button disabled condition**

In `controlButtons`, change:
```swift
.disabled(!allSubmitted || isPaused)
```
to:
```swift
.disabled(!allSubmitted || isPaused || isProcessing)
```

**Step 3: Build and verify**

Run: same xcodebuild
Expected: BUILD SUCCEEDED

---

### Task 6: Wire `RoundControlView` Submission Tracking to Real Session Data

**Objective:** The professor sees real submission status from the session/backend, not local `@State` copies.

**Files:**
- Modify: `BizSimAI/Views/Professor/RoundControlView.swift`

**Step 1: Update `loadFromSession()` to read from session**

Replace existing `loadFromSession()` with:

```swift
private func loadFromSession() {
    guard let session = appState.activeSession else { return }
    currentRound = session.currentRound
    totalRounds = session.config.totalRounds
    isPaused = session.isPaused
    teamSubmissions = session.teams.map { team in
        TeamSubmission(
            id: team.id, name: team.name, isAI: team.isAI,
            hasSubmitted: team.hasSubmittedDecisions || team.isAI,
            submittedAt: team.hasSubmittedDecisions ? Date() : nil
        )
    }
}
```

**Step 2: Add `onReceive` timer to refresh submission status**

Add to the `body` modifier chain (after `.onAppear`):

```swift
.onReceive(Timer.publish(every: 5, on: .main, in: .common).autoconnect()) { _ in
    loadFromSession()
}
```

**Step 3: Build**

Run: same xcodebuild
Expected: BUILD SUCCEEDED

---

### Task 7: Fix `processRoundAfterPlayerSubmit()` to Use Snapshot Pattern

**Objective:** The professor's round advance also uses the snapshot → background → apply pattern, so it doesn't freeze the UI either.

**Files:**
- Modify: `BizSimAI/Engine/GameController.swift`

**Step 1: Rewrite `processRoundAfterPlayerSubmit()` to use `processRoundPure()`**

Replace the existing method (lines 42–111) with:

```swift
func processRoundAfterPlayerSubmit() {
    guard !isProcessing else { return }
    isProcessing = true

    let round = session.currentRound

    // Generate AI decisions (main thread, touches @Observable)
    guard let playerTeamId = session.teams.first(where: { !$0.isAI })?.id else {
        isProcessing = false
        return
    }
    let playerPrevDecision: PlayerDecision? = session.previousRoundDecisions[playerTeamId]

    let submittedDecisions = Array(session.currentRoundDecisions.values)
    let avgWholesale = submittedDecisions.isEmpty ? 80.0
        : submittedDecisions.map(\.wholesalePrice).reduce(0, +) / Double(submittedDecisions.count)
    let avgInternet = submittedDecisions.isEmpty ? 90.0
        : submittedDecisions.map(\.internetPrice).reduce(0, +) / Double(submittedDecisions.count)

    for competitor in aiCompetitors {
        guard let aiTeam = session.teams.first(where: { $0.id == competitor.teamId }) else { continue }
        let competitorProfits = session.teams.reduce(into: [:]) { dict, t in
            dict[t.id] = t.cumulativeProfit
        }
        let context = AIDecisionContext(
            config: session.config,
            team: aiTeam,
            playerPreviousDecision: playerPrevDecision,
            roundsRemaining: session.config.totalRounds - round,
            competitorProfits: competitorProfits,
            averageWholesalePrice: avgWholesale,
            averageInternetPrice: avgInternet
        )
        var rng = SeededRandomGenerator(
            seed: session.config.randomSeed
            &+ UInt64(round)
            &+ UInt64(bitPattern: Int64(competitor.teamId.hashValue)))
        let aiDecision = competitor.strategy.makeDecisions(
            teamId: competitor.teamId, round: round, context: context, rng: &rng)
        session.submitDecision(aiDecision)
    }

    // Snapshot → Background Compute → Main-Thread Apply
    let snapshot = session.takeSnapshot()
    let decisions = session.currentRoundDecisions

    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
        guard let self else { return }

        let output = self.engine.processRoundPure(
            snapshot: snapshot, decisions: decisions)

        // Apply results on main thread
        DispatchQueue.main.async {
            self.session.applyRoundOutput(output)
            self.lastRoundResults = output.results
            self.latestExplanations = output.explanations

            // Update AI tracking
            for result in output.results {
                if let idx = self.aiCompetitors.firstIndex(where: { $0.teamId == result.teamId }) {
                    self.aiCompetitors[idx].updateFromResult(result)
                }
            }

            // Add player round summary
            if let playerTeam = self.session.playerTeam,
               let playerResult = output.results.first(where: { $0.teamId == playerTeam.id }),
               let playerDec = decisions[playerTeam.id] {
                let summary = RoundSummary(from: playerResult, price: playerDec.wholesalePrice)
                self.session.playerRoundSummaries.append(summary)
            }

            self.session.advanceRound()
            self.isProcessing = false
        }
    }
}
```

**Step 2: Build**

Run: same xcodebuild
Expected: BUILD SUCCEEDED

---

### Task 8: Build, Install, and Test Quick Demo on Real Device

**Objective:** Verify the Quick Demo no longer freezes on the iPhone.

**Step 1: Build**
Run: `xcodebuild -project /Users/luisborges/2026/BizSimAI-ios/BizSimAI/BizSimAI.xcodeproj -scheme BizSimAI -destination 'platform=iOS,id=96BEAEB2-7A4C-5E79-AD11-D8718B2CA8D5' -configuration Debug -allowProvisioningUpdates build`

**Step 2: Install**
Run: `xcodebuild ... install`

**Step 3: Launch and test**
Run: `xcrun devicectl device process launch --device 96BEAEB2-7A4C-5E79-AD11-D8718B2CA8D5 com.luisborges.bizsim.BizSimAI`

Manual test:
1. Login as `test1` / `Test@1234`
2. Go to Quick Demo tab (green graduation cap)
3. Tap "Quick Demo (Auto-Play All Rounds)"
4. Verify: UI stays responsive, rounds appear incrementally, results display

Expected: No freeze. Each round's results appear with ~300ms gap. Total completion in ~3-5 seconds.

---

## Files Changed Summary

| File | Change |
|------|--------|
| `BizSimAI/Engine/SimulationSnapshot.swift` | NEW — `SimulationSnapshot`, `RoundOutput`, `TeamUpdate` structs |
| `BizSimAI/Models/SimulationSession.swift` | ADD `takeSnapshot()` + `applyRoundOutput()` methods |
| `BizSimAI/Engine/SimulationEngine.swift` | ADD `processRoundPure()` — pure computation, no @Model access |
| `BizSimAI/Engine/GameController.swift` | REWRITE `runQuickDemo()` + `processRoundAfterPlayerSubmit()` to use snapshot pattern |
| `BizSimAI/Views/Professor/RoundControlView.swift` | WIRE `advanceRound()` to call game controller, add real submission tracking |

## Risks & Tradeoffs

1. **Code duplication**: `processRoundPure()` duplicates the logic of `processRound()`. We keep the original `processRound()` for backward compatibility during transition. After verification, the original can be deleted.

2. **SwiftData consistency**: `applyRoundOutput()` does multiple mutations to `SimulationSession`. Since it's on the main thread, SwiftData context is safe. But if the model context is shared with SwiftData's auto-save, we need to be careful about save timing.

3. **AI strategy access**: `runQuickDemo()` accesses `self.aiCompetitors` from the background thread (to get strategy objects). These are NOT `@Observable` — they're plain classes. But `GameController` is `@Observable`. We need to verify `aiCompetitors` is safe to access from background. The `@unchecked Sendable` conformance already claims this is safe.

4. **Backend sync**: The production flow needs the backend to support the advance-round API. `NetworkService.advanceRound()` already exists. We need to verify it returns results that can be applied to the session.

5. **`DispatchQueue.main.sync` inside `DispatchQueue.global().async`**: This is safe (background → main sync is a standard pattern, only main → main sync would deadlock). But it blocks the background thread until main thread processes. Since the main thread is free (not doing computation), this is fine.
