# **Kotoku MVP: Detailed 6-Sprint Development Plan**

## **Overview**

Kotoku now has a product spec, architecture direction, and Django repo blueprint, which means the next critical step is an execution plan that translates strategy into weekly delivery. MVP planning guidance consistently recommends short iterations, clear sprint goals, and explicit validation checkpoints so teams can test assumptions and reduce risk instead of simply accumulating features.

This plan assumes a 6-sprint MVP cycle with 2-week sprints, which is a practical cadence for early-stage products because it balances delivery speed with enough time to complete meaningful product slices and test outcomes.

## **Team Structure**

| Role | Owner | Primary responsibilities |
| :---- | :---- | :---- |
| Product, UX, flow design, acceptance | Yaw / Gap Lenz | Scenario flow, field definitions, review logic, testing, pilot preparation |
| Backend lead | Samuel | Django architecture, PostgreSQL models, DRF endpoints, Celery jobs, storage, auth, audit |
| AI co-engineering | Vibecode AI | Scaffolding, test generation, boilerplate, admin tooling, refactor support |

## **Delivery Assumptions**

* Sprint length: 2 weeks.  
* MVP scope: used vehicle sale and rental agreement only.  
* Backend stack: Django, DRF, PostgreSQL, Redis, Celery, object storage.  
* Export format: PDF only.  
* Identity baseline: Ghana Card \+ phone number \+ SMS OTP.  
* Consent rule: bilateral OTP required before sealing.  
* Engineering style: modular monolith, not microservices.

## **Sprint Plan Summary**

| Sprint | Goal | Main output |
| :---- | :---- | :---- |
|  |  |  |
| Sprint 1 | Foundation and engineering setup | Running backend skeleton with auth foundation and CI/dev workflow |
| Sprint 2 | Identity and agreement draft core | Users can create and save draft agreements with scenario templates |
| Sprint 3 | Evidence capture and storage | Users can attach Ghana Card, photos, and audio metadata to drafts |
| Sprint 4 | Bilateral consent and sealing | Two-party OTP flow and sealed agreement lifecycle work end to end |
| Sprint 5 | Vault and PDF export | Sealed agreements appear in vault and generate PDF exports |
| Sprint 6 | Reopen/annotation/dispute basics plus pilot hardening | MVP is stable enough for controlled field pilot |

## **Sprint 1**

## **Sprint goal**

Set up the backend foundation so the team has a stable development environment, repo conventions, deployment baseline, and core project wiring. MVP roadmaps work best when the first sprint reduces setup risk and creates a usable delivery pipeline before heavy feature work begins.

## **Outcomes**

* The local development environment runs cleanly.  
* CI checks exist for linting, tests, and migrations.  
* Django project structure reflects the approved repo blueprint.  
* Core infrastructure services are wired: PostgreSQL, Redis, Celery, object storage config.

## **Backend work**

* Initialize Django project from repo blueprint.  
* Configure split settings: base, local, test, production.  
* Add DRF, Celery, Redis, PostgreSQL setup.  
* Set up object storage configuration.  
* Create health endpoint and readiness checks.  
* Add a custom user model if needed from day one.  
* Add baseline logging and error reporting hooks.

## **Product and UX work**

* Finalize scenario labels and wording for v1.  
* Finalize field list for used vehicle sale and rental agreement.  
* Freeze MVP policy rules in developer-facing language.  
* Create acceptance criteria for all core user flows.

## **Vibecode AI support**

* Generate app scaffolding and boilerplate.  
* Draft Docker and compose files.  
* Generate test stubs and Makefile commands.  
* Help create initial admin registrations.

## **Deliverables**

* Running API locally.  
* Celery workers start locally.  
* Environment variable template complete.  
* README with setup instructions.  
* Initial architecture decision log.

## **Definition of done**

* New team members can clone repo and run backend locally in under 30 minutes.  
* Health endpoint passes.  
* CI runs successfully on pull requests.  
* Codebase matches agreed app/module structure.

## **Risks**

* Time loss from setup friction.  
* Wrong early assumptions on auth model.

## **Mitigation**

* Lock the custom user approach in Sprint 1\.  
* Keep environment setup documented from the first day.

## **Sprint 2**

## **Sprint goal**

Deliver identity and draft agreement creation so the product has a working “start transaction” backbone. Agile MVP planning emphasizes delivering a thin but real user flow early, because it exposes architectural mistakes faster than isolated backend tasks.

## **Outcomes**

* Phone-based auth foundation exists.  
* Users can create agreement drafts.  
* Scenario templates can be loaded for vehicle and rental flows.  
* Draft step data can be saved and retrieved.

## **Backend work**

* Implement accounts and auth endpoints.  
* Add OTP request and verification foundation.  
* Implement agreements, parties, and identity models.  
* Build template endpoint for used\_vehicle\_sale and rental\_agreement.  
* Create draft agreement API: create, update, fetch, list.  
* Add audit logging for draft creation and updates.

## **Product and UX work**

* Finalize flow order for both scenarios.  
* Define mandatory vs optional fields.  
* Define save-draft behavior and empty-state handling.  
* Review API payloads against mobile UX requirements.

## **Vibecode AI support**

* Generate serializers and viewset skeletons.  
* Draft seed data for templates.  
* Generate unit tests for service functions.

## **Deliverables**

* POST /auth/send-otp  
* POST /auth/verify-otp  
* POST /agreements  
* PATCH /agreements/{id}  
* GET /agreements/{id}  
* GET /templates  
* GET /templates/{scenarioId}

## **Definition of done**

* A user can verify a phone number in dev/staging.  
* A user can create a draft agreement for either scenario.  
* Draft survives round-trip fetch/update.  
* Audit events are written for create/update actions.

## **Risks**

* Overcomplicated template model too early.  
* Confusion between identity verification and agreement-party identity.

## **Mitigation**

* Keep scenario templates versioned but simple.  
* Separate user account from agreement party concept in data model.

## **Sprint 3**

## **Sprint goal**

Add evidence capture support so drafts become evidence-capable, not just text forms. For Kotoku, this sprint is critical because the value proposition depends on credible documentation rather than on form entry alone.

## **Outcomes**

* Agreement drafts can reference uploaded evidence.  
* Ghana Card image metadata is stored.  
* Audio and photo evidence are linked to agreements.  
* Storage, hashing, and processing hooks exist.

## **Backend work**

* Implement evidence app models and upload flows.  
* Add file metadata model with hash and storage key.  
* Implement upload initiation endpoint.  
* Store Ghana Card evidence separately from general evidence types.  
* Add evidence completeness checks by scenario.  
* Queue OCR/transcription placeholders as Celery tasks.  
* Add audit events for upload attachment and processing outcomes.

## **Product and UX work**

* Finalize evidence checklist per scenario.  
* Define minimal acceptable capture for “ready for review.”  
* Define UI labels for photo slots, ID prompts, and audio summaries.  
* Create evidence error-state guidance for failed uploads.

## **Vibecode AI support**

* Generate storage adapters and upload service boilerplate.  
* Generate tests for evidence service and hash creation.  
* Help draft Celery tasks and retry logic.

## **Deliverables**

* POST /agreements/{id}/evidence/upload-url  
* POST /agreements/{id}/evidence  
* GET /agreements/{id}/evidence  
* Internal completeness evaluation logic

## **Definition of done**

* Evidence upload metadata works end to end.  
* Agreement can show required vs missing evidence.  
* Ghana Card uploads and general evidence uploads are distinguishable.  
* Upload events and file hashes are stored.

## **Risks**

* Too much effort spent on media processing before core lifecycle is complete.  
* Local vs cloud storage mismatch.

## **Mitigation**

* Keep OCR/transcription non-blocking and optional in MVP.  
* Use the same storage abstraction in all environments.

## **Sprint 4**

## **Sprint goal**

Deliver bilateral consent and agreement sealing so Kotoku can produce an immutable evidence-backed record. This sprint is the core trust milestone because the MVP must prove that both parties participated and that the agreement can move into a sealed state.

## **Outcomes**

* Separate OTP for both parties works.  
* Agreement readiness validation works.  
* Seal transition and append-only audit trail work.  
* Sealed agreements become immutable except through reopening policy.

## **Backend work**

* Implement consent models and services.  
* Build OTP request/confirm flow per party.  
* Add readiness validation: required fields, identity baseline, evidence minimum, both-party confirmation.  
* Implement seal endpoint and lifecycle state transition.  
* Generate version hash or seal snapshot reference.  
* Prevent direct edits to sealed agreements.  
* Add audit events for OTP requested, OTP confirmed, sealed.

## **Product and UX work**

* Finalize consent copy and trust messaging.  
* Define review summary sections and edit-before-seal behavior.  
* Define failure states: OTP expired, party unavailable, validation incomplete.  
* Walk through full seal flow with test scenarios.

## **Vibecode AI support**

* Scaffold consent service and lifecycle tests.  
* Generate edge-case tests for invalid seal attempts.  
* Help implement state machine guards.

## **Deliverables**

* POST /agreements/{id}/consent/request-otp  
* POST /agreements/{id}/consent/confirm  
* POST /agreements/{id}/validate  
* POST /agreements/{id}/seal

## **Definition of done**

* Both parties can complete separate OTP confirmation.  
* Agreement cannot seal unless rules are satisfied.  
* Sealed agreement cannot be silently edited.  
* Audit trail is complete for consent and seal events.

## **Risks**

* OTP complexity creates delivery issues.  
* Sealing logic spreads into views and serializers.

## **Mitigation**

* Keep consent and sealing in service-layer orchestration.  
* Test state transitions heavily before UI polish.

## **Sprint 5**

## **Sprint goal**

Deliver vault behavior and PDF export so sealed agreements become retrievable, shareable, and useful outside the app. MVP guidance emphasizes focusing on the smallest viable outcome that proves value; for Kotoku, that outcome is not just sealing but being able to retrieve and present the sealed record when needed.

## **Outcomes**

* Sealed agreements appear in vault views.  
* PDF export generation works asynchronously.  
* Retention logic starts to exist.  
* Basic operational visibility exists in admin.

## **Backend work**

* Implement vault models and services.  
* Build vault list/detail endpoints.  
* Generate PDF export in Celery task.  
* Store PDF metadata and object storage reference.  
* Add retention dates and free-retention status.  
* Add admin views for sealed agreements, export failures, retention states.  
* Add audit events for export generation and retention-state changes.

## **Product and UX work**

* Define vault sorting/filtering behavior.  
* Finalize PDF content and ordering.  
* Define retention reminders and user-facing status labels.  
* Review document readability on phone.

## **Vibecode AI support**

* Scaffold PDF renderer wrapper.  
* Generate admin enhancements.  
* Generate tests for vault listing and export task behavior.

## **Deliverables**

* GET /vault  
* GET /vault/{agreementId}  
* POST /vault/{agreementId}/export  
* Background PDF generation job

## **Definition of done**

* A sealed agreement appears in vault with correct state.  
* PDF can be generated and linked to vault record.  
* Export failure is observable and retryable.  
* Retention fields exist and can be queried.

## **Risks**

* PDF generation becomes a formatting rabbit hole.  
* Export logic too tightly coupled to live agreement queries.

## **Mitigation**

* Keep PDF v1 plain, readable, and deterministic.  
* Build export from a snapshot-friendly data structure.

## **Sprint 6**

## **Sprint goal**

Harden the MVP for pilot use by adding reopening fallback, post-seal annotations, dispute basics, test coverage, and deployment readiness. Agile MVP planning stresses that final pre-launch work should focus on stability, instrumentation, and learning readiness rather than uncontrolled feature growth.

## **Outcomes**

* Reopen request flow exists.  
* Post-seal annotations work when amendment is not possible.  
* Basic dispute creation works.  
* QA and staging readiness are complete.  
* Pilot checklist and instrumentation are ready.

## **Backend work**

* Implement disputes module basics.  
* Implement reopen\_requested, reopened\_mutual, and annotated\_post\_seal states.  
* Build reopen request endpoints and bilateral re-auth flow.  
* Block unilateral edits to sealed records.  
* Add post-seal annotation endpoint.  
* Add basic dispute opening and retrieval.  
* Finalize retention jobs and reminder tasks.  
* Improve observability: structured logs, metrics hooks, failure reporting.

## **Product and UX work**

* Finalize dispute and annotation copy.  
* Define pilot test scripts and scenario walkthroughs.  
* Create QA checklist for both scenarios.  
* Prepare onboarding notes for pilot users and support handling.

## **Vibecode AI support**

* Generate test cases for reopen and dispute edge conditions.  
* Assist with staging environment scripts.  
* Help produce admin filters and support tooling.

## **Deliverables**

* POST /agreements/{id}/reopen-request  
* POST /agreements/{id}/reopen-consent/request-otp  
* POST /agreements/{id}/reopen-consent/confirm  
* POST /agreements/{id}/annotations  
* POST /agreements/{id}/disputes

## **Definition of done**

* Reopening requires bilateral re-authentication.  
* If one party is unavailable, sealed content remains immutable while annotation/dispute creation still works.  
* End-to-end pilot flow works in staging.  
* Core operational metrics and error alerts are live.

## **Risks**

* Final sprint becomes overloaded with “nice-to-have” requests.  
* Pilot preparation gets squeezed by unfinished engineering.

## **Mitigation**

* Freeze MVP scope at start of Sprint 6\.  
* Track bugs separately from enhancements.

## **Cross-Sprint Workstreams**

## **Quality assurance**

QA should not wait until Sprint 6\. Early-stage MVP planning works better when testing is continuous and attached to sprint outcomes rather than deferred to the end.

Every sprint should include:

* unit tests for service logic  
* integration tests for major workflows  
* API contract checks  
* regression checks for previous sprint outcomes

## **Documentation**

Every sprint should update:

* API docs  
* architecture notes  
* environment setup docs  
* product policy docs  
* demo checklist

## **Security and compliance posture**

Across all sprints:

* protect secrets with environment variables  
* restrict media access  
* log sensitive actions  
* mask sensitive ID data where possible  
* keep audit events append-only

## **Dependency Map**

| Capability | Depends on |
| :---- | :---- |
| Draft creation | Sprint 1 foundation |
| Evidence upload | Draft creation \+ object storage wiring |
| Seal flow | Identity \+ draft \+ evidence \+ OTP |
| Vault export | Seal flow \+ worker infrastructure |
| Reopening | Seal flow \+ consent models \+ state machine |
| Pilot | All previous sprints plus QA and staging |

## **Release Gates**

## **Gate 1: Architecture ready**

After Sprint 1:

* repo stable  
* CI working  
* local dev reliable

## **Gate 2: Core draft workflow ready**

After Sprint 2:

* auth works  
* draft agreement works  
* templates load correctly

## **Gate 3: Evidence-backed workflow ready**

After Sprint 3:

* evidence metadata and storage working  
* completeness checks working

## **Gate 4: Trust milestone ready**

After Sprint 4:

* bilateral OTP and sealing working  
* audit trail complete

## **Gate 5: Value milestone ready**

After Sprint 5:

* vault and PDF export working

## **Gate 6: Pilot-ready MVP**

After Sprint 6:

* reopen and annotation logic working  
* disputes basic  
* staging stable  
* monitoring live

## **Suggested Weekly Rituals**

| Ritual | Frequency | Purpose |
| :---- | :---- | :---- |
| Sprint planning | Every 2 weeks | Lock sprint scope and owners |
| Backend-product sync | 2 times per week | Align API and UX decisions |
| Demo/review | End of sprint | Show real working slice |
| Bug triage | Weekly | Keep MVP scope from drifting |
| Architecture checkpoint | End of Sprints 2, 4, 6 | Reassess scaling and code health |

## **Recommended Backlog Order Within Sprints**

For each sprint, prioritize work in this sequence:

1. Data model and service rules  
2. API contract  
3. Background jobs or infrastructure needs  
4. Admin/support visibility  
5. Tests  
6. polish only after flow is working

This ordering keeps the team from over-investing in secondary improvements before the core workflow exists.

## **MVP Success Criteria**

The MVP should be considered successful if, by the end of Sprint 6:

* a user can create a vehicle or rental agreement draft,  
* both parties can verify identity baseline and complete separate OTP confirmation,  
* the agreement can be sealed with audit trace,  
* evidence can be attached and referenced,  
* a PDF export can be generated and stored in the vault,  
* post-seal annotation and dispute opening work,  
* and the team can run a controlled field pilot.

## **Immediate Next Actions**

To start Sprint 1 cleanly, the team should do these next:

* create the sprint backlog in GitHub Projects, Notion, or Linear,  
* assign owners to each sprint outcome,  
* convert this plan into issue-sized tasks,  
* define the first staging environment target,  
* and schedule the first end-of-sprint demo.

