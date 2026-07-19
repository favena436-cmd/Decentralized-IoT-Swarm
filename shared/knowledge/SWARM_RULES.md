# Swarm Rules & Operating Procedures

## Core Principles

1. **Always be the best version of ourselves**
   - Every node runs the latest code before doing anything else
   - Auto-update on startup, with rollback on failure
   - No stale nodes allowed on the network

2. **Zero-downtime resilience**
   - If a node crashes, another picks up its tasks within 30 seconds
   - All state is shared, never local-only
   - Crash = automatic restart, not human intervention

3. **Fair delegation**
   - Tasks go to the agent best suited for the job
   - No agent is overloaded while others are idle
   - If an agent is down, its work redistributes automatically

4. **Paid service readiness**
   - Every node can offer billable capabilities
   - Usage is tracked per-client for billing
   - Quality of service is never compromised for free users

---

## Node Lifecycle Rules

### Startup Sequence
1. Check for updates (auto-apply if available)
2. Verify connectivity to orchestrator
3. Register with current capabilities
4. Pull latest shared knowledge
5. Announce ready status
6. Accept tasks

### Health Check Rules
- Heartbeat every 10 seconds to orchestrator
- If 3 heartbeats missed, node is marked offline
- If 5 heartbeats missed, tasks redistribute
- Self-test runs every 5 minutes (CPU, memory, disk, network)
- Any anomaly triggers automatic diagnostic + report

### Update Rules
- Check for new versions on every startup
- Hot-reload: apply updates without restart when possible
- Full restart only for kernel/dependency changes
- Rollback automatically if new version fails health check
- Update channel: stable (production) / beta (testing) / dev (experimental)
- Stable updates auto-apply
- Beta updates auto-apply only if node has beta enabled
- Dev updates require explicit approval

### Crash Recovery Rules
1. Node detects crash (or orchestrator detects unresponsive)
2. Orchestrator marks node as "recovering"
3. Tasks reassigned to healthy nodes
4. Node auto-restarts via systemd/launchd
5. On restart, node reports crash context to orchestrator
6. Orchestrator decides: rejoin, investigate, or retire
7. Crash log saved to shared/crashes/ for analysis
8. Pattern detection: if same crash happens 3x, node is quarantined

---

## Delegation Rules

### Task Routing
- **OWL** (Orchestrator): Routes all tasks, maintains global state, resolves conflicts
- **Antigravity** (Architect): System design, code review, refactoring, documentation
- **Chat Node** (Voice/Comms): STT, TTS, voice chat, user-facing communication
- **Xbox Hermes** (Hardware): Device I/O, code execution, builds, testing on real hardware

### Fair Distribution Algorithm
1. Check which agents are online
2. Check current load (tasks in progress) per agent
3. Assign to least-loaded agent capable of handling the task
4. If all capable agents are full, queue the task (don't overload)
5. If no capable agent is online, escalate to user with clear message
6. Maximum queue depth: 10 tasks per agent
7. Tasks older than queue-max get priority escalation

### Capability Advertisement
- Each node advertises its capabilities on registration
- Capabilities include: role, OS, RAM, installed skills, current load
- Orchestrator maintains a capability registry
- Tasks can include capability requirements (e.g., "needs GPU", "needs 4GB RAM")
- Orchestrator only routes to nodes that meet requirements

---

## Paid Service Rules

### Service Tiers

#### Free Tier
- Basic chat with AI agents
- Standard response time (< 30s)
- Community support
- Up to 3 nodes per swarm
- Basic monitoring dashboard

#### Pro Tier ($29/month per node)
- Priority task routing (faster response)
- Voice AI (STT/TTS) included
- Advanced monitoring + alerts
- Up to 10 nodes per swarm
- Auto-update with early access to new features
- Email support
- Custom skill installation

#### Business Tier ($99/month per node)
- Everything in Pro
- Unlimited nodes
- Dedicated orchestrator
- Custom agent roles
- Usage analytics + billing reports
- SLA: 99.9% uptime guarantee
- Priority support (4hr response)
- White-label option
- API access for programmatic control

#### Enterprise Tier (custom pricing)
- Everything in Business
- On-premise deployment
- Custom AI model integration
- Compliance (HIPAA, SOC2)
- Dedicated account manager
- Custom SLA (99.99%)
- 24/7 phone support
- Audit logging

### Billing Rules
- Usage tracked per-node, per-task-type
- Monthly billing cycle, pro-rated for partial months
- 14-day free trial for Pro and Business tiers
- Grace period: 7 days after payment failure before service pause
- Data export always available (no vendor lock-in)
- Refund policy: full refund within first 30 days

### Service Quality Rules
- Pro/Business tasks always prioritized over free
- Free tier throttled only during extreme load (>80% capacity)
- Paid nodes get guaranteed minimum resources (CPU, RAM reservation)
- If SLA is breached, automatic credit applied to next bill
- All tiers get crash recovery and auto-restart

---

## Communication Rules

### Inter-Agent Communication
- All messages go through the orchestrator (no direct agent-to-agent bypass)
- Message format: JSON with id, timestamp, sender, recipient, type, payload
- Maximum message size: 1MB
- Messages expire after 5 minutes if undelivered
- Critical messages (errors, crashes) bypass queue and go immediately

### User Communication
- Chat Node is the default user-facing agent
- Status updates pushed via WebSocket (no polling)
- Errors reported in plain language, not stack traces
- Progress updates for long tasks (> 10s) every 5 seconds
- User can interrupt any task with "stop" or "cancel"

### Shared Knowledge Rules
- All agents read from shared/knowledge/ for reference
- Only Antigravity can write to shared/knowledge/ (prevents conflicts)
- Task results go to shared/results/ with agent ID and timestamp
- Shared files are the source of truth, local copies are cache only
- Knowledge base auto-prunes: items not accessed in 30 days go to archive

---

## Security Rules

### Access Control
- Nodes authenticate with orchestrator on join (token-based)
- Each node gets a unique token, revocable by orchestrator
- Orchestrator token rotates every 24 hours
- Failed auth 3 times = node banned for 15 minutes
- All inter-node traffic encrypted (TLS where available)

### Data Protection
- User data never leaves the swarm without explicit consent
- Crash logs scrubbed of PII before saving
- Shared directories have per-agent read/write permissions
- Backup encryption: AES-256
- Data retention: 90 days for logs, 1 year for task results, forever for knowledge

### Update Security
- All updates signed with Ed25519 signature
- Signature verified before applying update
- Update server certificate pinned
- Rollback on signature failure (never run unsigned code)

---

## Monitoring & Alerting Rules

### What We Monitor
- Per-node: CPU, RAM, disk, network, uptime, task queue depth
- Per-task: latency, success/failure, retries
- System-wide: total throughput, error rate, active nodes, queue health
- Security: auth failures, unusual traffic patterns, banned nodes

### Alert Rules
- **INFO**: Node joined, task completed, update applied (logged only)
- **WARN**: Node slow (>2x normal latency), queue depth >5, disk >80%
- **ERROR**: Node offline, task failed 3x, crash detected, auth failure
- **CRITICAL**: Orchestrator offline, >50% nodes down, security breach

### Alert Delivery
- WARN+: Push to dashboard immediately
- ERROR+: Email to admin + dashboard
- CRITICAL: Email + SMS + dashboard + auto-remediation attempt

---

## Maintenance Rules

### Daily (automated)
- Health check all nodes
- Rotate logs
- Verify backups
- Check for updates
- Clean temp files

### Weekly (automated, human-reviewed)
- Performance report
- Security audit log review
- Capacity planning check
- Knowledge base cleanup

### Monthly (human-led)
- Full system review
- Update roadmap review
- Customer feedback review
- Cost optimization

---

## Expansion Rules

### Adding New Nodes
1. Run `bootstrap.sh` on target device
2. Node auto-discovers orchestrator (or use `--orchestrator`)
3. Node registers with capabilities
4. Orchestrator validates and adds to registry
5. Node pulls latest shared state
6. Node is ready for tasks

### Adding New Agent Roles
1. Antigravity designs the role interface
2. OWL integrates into task router
3. New role gets: handler registration, capability advertisement, health check
4. Documentation updated
5. Tested in dev → beta → stable

### Adding New Skills/Tools
1. Skill submitted as PR to shared/skills/
2. Antigravity reviews for architecture
3. Xbox Hermes tests on target platform
4. Chat Node validates user-facing UX
5. OWL approves for production
6. Rolled out to all nodes via auto-update

---

## Conflict Resolution

### Task Conflicts
- If two agents claim the same task, orchestrator decides based on:
  1. Which agent is best suited (capability match)
  2. Which agent has lower current load
  3. Which agent claimed it first (tiebreaker)
- Loser gets notified immediately with reason

### Resource Conflicts
- Paid nodes always get resource priority over free
- Within same tier: first-come-first-served
- Resource limits enforced per-node (no hogging)
- If node exceeds limits, non-critical tasks get throttled

### Human Override
- Jimmy (human) can override any automated decision
- Override commands: `override node <id> <action>`, `override task <id> <action>`
- All overrides logged for audit
- Overrides expire after 1 hour unless renewed

---

## Version: 1.0.0 | Effective: 2026-06-30 | Owner: Jimmy + OWL
