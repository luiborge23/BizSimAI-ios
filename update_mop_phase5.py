#!/usr/bin/env python3
"""Update BizSimAI MOP Google Doc — delete old Phase 5, insert new content."""
import json, subprocess

with open('/tmp/doc_positions.json', 'r') as f:
    positions = json.load(f)

doc_id = positions['doc_id']
access_token = positions['access_token']
old_start = positions['old_start']
old_end = positions['old_end']
insert_pos = positions['insert_pos']

phase5_content = """

13. Phase 5 — Classroom Production Layer (Final Status: May 9-12, 2026)

---

13.1 Executive Summary

Phase 5 transforms BizSim AI from a local-only iOS app into a cloud-connected classroom platform. The backend now uses Firebase Firestore for session persistence, JWT-based authentication (Apple Sign-In + Google + password), WebSocket real-time sync, and a professor web dashboard. The iOS app has been rebuilt with auth-aware navigation, session join flows, live dashboards, announcements, and CSV export.

Overall Phase 5 Completion: ~92% — All infrastructure built, most bridge connections wired. Remaining: leaderboard backend sync (Gap #1), professor dashboard HTML refinement (Gap #2).

---

13.2 Architecture Overview

New three-tier architecture:

iOS App → FastAPI Backend (Firebase Firestore) → Cloud Storage

The iOS app communicates with the backend via REST API for CRUD operations and WebSocket for real-time updates. Firebase Firestore serves as the database layer, replacing the previous local-only data model.

---

13.3 Completed Items (Infrastructure Layer — 90%)

Authentication:
✅ Production JWT Configuration — BIZSIMAI_JWT_SECRET, BIZSIMAI_JWT_EXPIRY_HOURS, CORS, HOST, PORT env vars with health check validation
✅ Apple/Google ID Token Verification — Full JWKS-based verification (6hr TTL cache), issuer/audience/expiry validation for both providers
✅ iOS Auth Integration — AuthManager.swift (JWT + Apple Sign-In + Google Sign-In in Keychain), AuthState.swift (Observable)
✅ LoginView — Three-mode login UI: Professor Login, Student Login, Student Register with Apple/Google options
✅ LaunchView Auth Check — Shows LoginView sheet when unauthenticated; "Welcome back" message when authenticated
✅ Logout — Clears Keychain JWT and refreshes LaunchView state
✅ Professor-Only Endpoint — /api/auth/professor-only returns 403 for non-professor roles

Real-Time Sync:
✅ WebSocket Reconnection — ReconnectableWSClient with exponential backoff, ping/pong keepalive
✅ WebSocket Connection Manager (ws_manager.py) — Per-session connection groups, JWT-authenticated rooms
✅ Auto-broadcast on session start and round completion to connected students

Session Management:
✅ FirebaseSessionStore — Full CRUD for sessions/teams/decisions/announcements/grades via Firestore
✅ SyncService dual-adapter pattern — FirebaseSyncAdapter + LocalSyncAdapter with protocol-based abstraction
✅ FirebaseRealtimeSync — Live listeners for session state, teams, announcements, round results
✅ Session Join Flow — SessionJoinSheet with PIN entry + professor verification + backend data fetch
✅ JoinSessionViewModel — Fetches getSession(byCode:), getTeams(code:), syncAnnouncements() after successful join
✅ JoinSessionView.onTeamJoined() — Uses backend SessionBackend.config for session params (totalRounds, startingCash, numberOfAICompetitors, plantCapacity) with fallback to defaults

Professor Dashboard:
✅ FastAPI-served SPA dashboard — GET /dashboard serves dashboard.html, GET /api/dashboard/sessions lists sessions, GET /api/dashboard/monitor/{code} provides real-time monitoring via WebSocket
✅ Session management — create, join, monitor, advance rounds, export grades
✅ Router at backend/routers/dashboard.py registered in main.py with Jinja2Templates

Student-Facing Features:
✅ TeamDashboardView synced with BackendState live data (team count, submission count, round progress via backendCurrentRound)
✅ Round header shows live backend status with online indicator
✅ StudentAnnouncementsView — Real-time announcement display with relative time formatting
✅ AnnouncementsView posts to backend via NetworkService.sendAnnouncement()

Export & Reporting:
✅ Grade CSV Export — Backend endpoints for exportGrades and exportLeaderboard, NetworkService methods on iOS side
✅ SessionResultsView uses CSVExportViewModel for real data fetch with export buttons

---

13.4 Remaining Integration Gaps (Bridge Layer)

Critical Gap #1: Leaderboard Not from Backend
- LeaderboardView still uses local session.leaderboard instead of calling NetworkService.getLeaderboard()
- Fix needed: Wire getLeaderboard() call in LeaderboardViewModel

Gap #2: Professor Dashboard HTML Refinement
- Basic dashboard served but needs enhanced UI for classroom use (session cards, student roster table, round controls)
- Priority: High — blocks full professor workflow completion

Minor Gap #3: Real-time Sync Activation
- FirebaseRealtimeSync listeners exist but startListening() not called consistently after join
- Fix needed: Call sync.startListening(sessionCode:) in onTeamJoined()

Gap #4: Session Status Sync
- SimulationSession properties (currentRound, state, teamsSubmitted) need periodic refresh or Firebase listener updates

---

13.5 Key Files — Backend

backend/auth.py — JWT creation/verification with env var configuration
backend/auth_providers.py — Apple/Google JWKS token verification (6hr TTL cache)
backend/routers/auth.py — Auth endpoints + professor-only role gate
backend/routers/websocket.py — WebSocket endpoint with JWT auth and room management
backend/ws_manager.py — Per-session WebSocket connection groups, ping/pong keepalive
backend/routers/dashboard.py — Professor web dashboard router (FastAPI + Jinja2)
backend/main.py — FastAPI app entry, CORS config, all routers registered
backend/store/firebase_store.py — FirebaseSessionStore Firestore CRUD operations
backend/models.py — SQLAlchemy models for PostgreSQL/Firestore mapping

---

13.6 Key Files — iOS App

Auth Layer:
AuthManager.swift — JWT token management, Apple/Google login, Keychain storage
AuthState.swift — Observable auth state (isLoggedIn, userRole, userName)
LoginView.swift — Three-mode login UI with Apple/Google/password options
LaunchView.swift — Auth-gated entry point, shows LoginView or Welcome screen

Session & Sync:
SyncService.swift — Dual-adapter session sync (Firebase + Local)
FirebaseRealtimeSync.swift — Live Firestore listeners for real-time updates
ReconnectableWSClient.swift — WebSocket with exponential backoff reconnection
JoinSessionViewModel.swift — Session join flow with backend data fetch
JoinSessionView.swift — Join sheet with PIN entry and config loading from backend

UI Views:
TeamDashboardView.swift — Live student dashboard with BackendState sync
StudentAnnouncementsView.swift — Student-facing announcements display
SessionResultsView.swift — Professor results with CSV export buttons
LeaderboardViewModel.swift — Leaderboard data (needs backend wire)

---

13.7 Testing & Verification

Backend Tests:
cd backend && python -m pytest test_phase5.py -v --tb=short
Status: 31 tests passing (18 original + 13 Phase 5)

iOS Build Command:
xcodebuild -project BizSimAI.xcodeproj -scheme BizSimAI -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
Status: BUILD SUCCEEDED (iPhone 17 Pro simulator)

---

13.8 Environment Variables

export BIZSIMAI_JWT_SECRET=<your-secret>
export BIZSIMAI_JWT_EXPIRY_HOURS=24
export BIZSIMAI_CORS_ORIGINS="*"
export BIZSIMAI_HOST="0.0.0.0"
export BIZSIMAI_PORT=8000
export BIZSIMAI_PROFESSOR_USERNAME=<prof-username>
export BIZSIMAI_PROFESSOR_PASSWORD=<prof-password>

---

13.9 Known Pitfalls & Gotchas

- auth.py is a module file, NOT a package — import providers as 'from auth_providers import ...' NOT 'from auth.providers import ...'
- RoundResultBackend (flat) maps differently than RoundResult (detailed) — use approximation for missing fields
- creditScore is Double in backend, CreditRating enum in iOS — convert with CreditRating(rawValue: "\\(Int(score))")
- inventory is Double in backend, Int in iOS — use Int(backend.inventory)
- GoogleSignIn framework not installed as SPM dependency yet — for dev builds, use Apple Sign-In only
- Never pass plain string like 'finished' for session.state — always use SessionState.FINISHED enum
- Announcements POST returns 200 (not 201) — test assertions must accept both status codes

---

13.10 Remaining Phase 5 Tasks

- [ ] Leaderboard backend sync (wire getLeaderboard() in LeaderboardViewModel)
- [ ] Professor Dashboard HTML refinement (session cards, student roster, round controls)
- [ ] FirebaseRealtimeSync startListening() activation after join
- [ ] Session status periodic refresh from backend
- [ ] Integration test suite (40+ tests planned)
- [ ] Production deployment (Docker, nginx, systemd, SSL)
"""

requests = []
if old_start is not None and old_end is not None:
    requests.append({
        'deleteContentRange': {
            'startIndex': old_start,
            'endIndex': min(old_end, positions['total_chars'] + 5000)
        }
    })

requests.append({
    'insertText': {
        'location': {'index': insert_pos},
        'text': phase5_content
    }
})

batch = {'requests': requests}

# Write to temp file then use curl — BUT the Google Docs API uses snake_case for REST!
# Let me check: the error says "delete_content_range" not "deleteContentRange"
# So field names in JSON must be snake_case!

with open('/tmp/mop_batch.json', 'w') as f:
    json.dump(batch, f)

cmd = [
    'curl', '-s', '-X', 'POST',
    '-H', f'Authorization: Bearer {access_token}',
    '-H', 'Content-Type: application/json',
    '-d', '@/tmp/mop_batch.json',
    f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate'
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(f"Exit code: {result.returncode}")
print(f"Response:\n{result.stdout[:2000]}")
if result.stderr:
    print(f"Stderr: {result.stderr[:500]}")
