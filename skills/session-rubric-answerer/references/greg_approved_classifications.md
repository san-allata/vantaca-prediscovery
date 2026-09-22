# Greg-Approved Classifications Reference
**Source:** Greg Hamm SME Review Sessions — Rubric Deep Dive
**Dates:** September 14, 15, 16, 21, 2026
**Purpose:** Classification rulings and domain rules confirmed directly by Greg Hamm. These override general heuristics for the topics they cover. Always load this file at Step 2b of the session processing workflow.

---

## How to Use This File

1. **Load at Step 2b** — before extracting or classifying any row
2. **Check topic match first** — before applying the general decision ladder, check if the question topic matches a GR-1 through GR-7 ruling or a GR-7 specific topic entry
3. **Record the rule** — when a ruling applies, record `[GR-N: description]` in the assessor notes
4. **These rules supersede the general decision ladder** for the topics they cover
5. **Add new entries** when Greg or another authoritative SME confirms a new classification ruling in a review session

---

## Domain Rules (GR-1 through GR-6)

### GR-1: Integration = AC, Not FB

**Source:** Greg Hamm, 09/16/2026
**Quote:** *"Very few were feature backlog… most of them were because it's either StrongRoom or VendorSmart. They were not — they were classified as configuration change."*

**Rule:** If a capability is delivered through a known, supported Associa integration partner, the correct classification is **AC** (requires configuration/adoption of the integration), **not FB**.

**Known Associa integration partners:**
- **StrongRoom** — AP workflow automation (invoice routing, approval chains, pre-payment controls, check generation)
- **VendorSmart / VendorSpark** — in-house AP system (cache management, payables routing, configurable conditions). Currently in rollout; will eventually replace StrongRoom for many branches.
- **Stripe** — payment processing (credit card, ACH)
- **Third-party mailing vendors** — statement/coupon mailing (integrated with TownSq billing module)
- **Bank lockbox integrations** — payment file import (integrated with TownSq AR module)

**When FB still applies (exceptions to GR-1):**
- Greg or an authoritative SME has explicitly named this specific sub-feature as a gap
- The integration definitively does not cover the required sub-feature (confirmed, not assumed)
- The integration is not yet available to this branch (timing gap → FB with date noted)

**Do NOT classify FB solely because native Vantaca lacks the capability.**

---

### GR-2: Community Management Context — Not Business Client Context

**Source:** Greg Hamm, confirmed by Sanjeev Sharma, 09/15/2026
**Quote:** *"Some of them were blatantly wrong because I think it was comparing with business versus community."* — Greg: *"Yeah, exactly."*

**Rule:** All classifications and evidence must be scoped to **HOA/community management** context. The branch manages homeowner associations, not commercial business clients. Features that exist for commercial clients may not exist for community management, and vice versa.

**How to apply:**
- When reading transcript evidence: confirm it refers to community management operations (billing homeowners, managing associations, delinquency for HOA assessments, etc.)
- When reading the TownSq capability column: confirm the capability described is for the community management product, not commercial AP/AR
- If context is ambiguous: note the ambiguity, flag HITL, and do not classify

---

### GR-3: StrongRoom ≠ Native Vantaca ≠ VendorSmart — Keep Systems Distinct

**Source:** Sanjeev Sharma + Greg Hamm, 09/21/2026
**Quote:** *"We want to know Vantaca's inherent workflows — identical to this [StrongRoom workflow]."* Greg: *"Strong Room was my very first project for Associa."*

**Rule:** These are three distinct systems on different ownership and migration timelines. Never conflate them.

| System | Type | Scope | Migration status |
|---|---|---|---|
| **Native Vantaca (WorkPoints+)** | Core accounting engine | GL, AR, reporting, bank reconciliation | Destination system |
| **StrongRoom** | Third-party AP workflow platform | Invoice routing, approval chains, pre-payment controls, check generation | Associa does not own it; long-term plan to migrate to VendorSmart |
| **VendorSmart / VendorSpark** | Associa in-house AP system (built after acquiring Castle) | Cache management, payables routing, configurable conditions | In rollout; "a number of years before we get there" for full migration |

**In assessor notes:** Always name the system explicitly in the TOWNSQ line: `[native Vantaca]`, `[StrongRoom]`, `[VendorSmart]`, `[Stripe]`, `[other integration]`.

**AP question rule:** For AP-related questions:
- StrongRoom → StrongRoom (same system, no change): **AC**
- StrongRoom → VendorSmart (system migration): assess case by case
- Anything → native Vantaca only: evaluate Vantaca-native capability on its own merits

---

### GR-4: Exception Automation = FB on Top of an AC Base

**Source:** Greg Hamm, 09/21/2026
**Quote:** *"The process is one-to-one. There's configuration to it, but then how it's implemented every month — that is going to be our feature gap, that we want to be able to automate that... only show when there's an exception to the process."*

**Rule:** When the base process is 1-to-1 (configuration-equivalent → AC), but the branch additionally requires **automated exception surfacing**, the automation layer is a **separate FB** gap.

**Examples of automation-layer FB gaps:**
- Auto-detect expired recurring charges
- Auto-alert when homeowner delivery method changes (coupon → statement)
- Auto-notify when homeowner consent changes for direct debit
- Auto-surface exceptions in monthly recurring charge runs without manual review

**How to classify:**
- Classification in column J = **AC** (base process)
- Assessor Notes must include: `Also requires: [automated exception detection — FB gap per GR-4]`
- Add a companion note for the PM/backlog team to track the automation gap

---

### GR-5: Third-Party External Access / Portal Retirement = Always FB

**Source:** Greg Hamm, 09/14/2026
**Quote:** *"It's not just rebranding, it's more about changing the whole process… that's definitely a feature backlog item."* (On third-party auditor/external data access requiring portal retirement)

**Rule:** Any requirement to provide external parties (auditors, collections agencies, third-party data consumers) with dedicated portal access **where the current access portal must be retired and replaced** is always **FB**. This is a full rebuild, not a branding or configuration change.

**Applies to:** Auditor portals, external data consumer portals, white-labeled client portals that need to be fully replaced (not just rebranded).

**Does NOT apply to:** External users granted read-only access via existing TownSq Community module (that is a known partial capability → AC or Partial-AC depending on whether it meets the branch's need).

---

### GR-6: No "Non-Negotiable" Language

**Source:** Sanjeev Sharma confirming Greg Hamm's position, 09/15/2026
**Quote:** *"Non-negotiable items, they are negotiable."*

**Rule:** Never use the phrase "non-negotiable" in any assessor note, classification rationale, or rubric output. Never treat any item as an immovable FB blocker without explicit, on-record SME confirmation. Items previously labeled non-negotiable should be re-examined as potential ACs or PCs.

---

## Specific Greg-Confirmed Topic Classifications (GR-7)

These are specific capability topics reviewed directly with Greg Hamm. Use as authoritative classification precedents when the same topic appears in a branch answer.

| Topic | Greg's Confirmation | Source Date | Classification | Notes |
|---|---|---|---|---|
| Billing frequencies (monthly / quarterly / semi-annual / annual) | *"Those are the same."* | 09/14/2026 | **AC** | Fully supported natively in TownSq |
| Billing start dates / fiscal year flexibility | *"They can start anytime — it all depends on your fiscal year for your community."* | 09/14/2026 | **AC** | No restriction on when a community's billing cycle begins |
| Homeowner self-service payment (balance pay, online) | *"That's a one-to-one."* | 09/21/2026 | **AC** | Self-service homeowner payment portal is a direct match |
| AR exception handling / manual review workflow | *"Yeah, I think that's about right."* (on full exception handling workflows, lockbox import, user roles) | 09/21/2026 | **AC** | Configuration of lockbox import, user roles for exception review |
| Financial statement distribution & tracking (build, distribute, track) | *"We've been doing that since 2008. We were the first ones to do it."* | 09/14/2026 | **AC** | Core platform capability; no gap |
| Chargebacks (90-day dispute window, reversal on homeowner ledger) | *"Yeah, pretty much [already supported very well]… We'll reverse the charge on the homeowner's ledger."* | 09/14/2026 | **AC** | Chargeback workflow well supported; process change for branch to adapt to TownSq's flow |
| Assessment mid-year changes (end current, start new amount) | *"We have to end the current assessment early and start the new assessment… from the next billing month to the end of the fiscal year."* — confirmed supported | 09/14/2026 | **AC** | Platform handles mid-year assessment changes |
| Direct debit consent & recurring charge updates | *"We are holding their direct debit and they said, just bill me for all my recurring charges… We're going to pull the new recurring charge out."* — consent-based, supported | 09/14/2026 | **AC + PC** | AC: direct debit configuration; PC: branch must communicate with homeowners on consent changes |
| StrongRoom AP workflow (branch currently on StrongRoom → stays on StrongRoom during migration) | *"Strong room to strong room, we are good to go."* | 09/14/2026 | **AC** | No gap; StrongRoom workflows carry over |
| VendorSmart / VendorSpark cache management module | *"There is a specific cache management module in VendorSpark, which can be configured to route payables into it if there is a reason."* | 09/14/2026 | **AC** | Module exists and is configurable; requires setup |
| Stop payments / voiding checks (post-payment) | *"That's where we get this to stop payments and voiding checks… it depends on the integration we have with the banks."* | 09/14/2026 | **AC** | Supported via bank integration; configuration required |
| Credit reporting — native platform | *"We don't do anything native within the platform. Anytime we do any credit reporting, it is a third party. So we do a data extract and send it to the third party."* | 09/14/2026 | **FB** (no native); **AC** if third-party integration is available and configured | Associa explored native credit reporting but never implemented it; concerns were raised at the time |
| Third-party auditor portal (dedicated access, current portal must be retired) | *"It's you gotta retire the whole thing, yeah… that's definitely a feature backlog item."* | 09/14/2026 | **FB** | Not a config/branding change; requires full build (GR-5) |
| Recurring charge exception automation (auto-surface expired charges, delivery changes) | *"That is going to be our feature gap that we want to be able to automate that."* | 09/21/2026 | **FB** (automation layer on top of AC base per GR-4) | Monthly setup = AC; automated exception detection = FB |

---

## Adding New Rulings

When Greg or another authoritative SME confirms a new classification in a review session:

1. Add a row to the GR-7 table above with: Topic, quote, source date, classification, notes
2. If it is a general pattern (not just a single topic), consider adding a GR-N rule in the Domain Rules section
3. Update the `session_processing_guide.md` Section 9 summary to reference the new rule
4. Update `branch-assessor-skill` and `rubric-classifier-skill` GR-7 tables to match

**Maintainer:** Cristian Gaspari
**Last updated:** 2026-09-21
