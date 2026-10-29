# Claim Retrieval and Source Applicability

Use this protocol for manuscript claim checks. Use topic-oriented discovery for surveys; do not force surveys into a claim ledger. Domain terms are defined in ../GLOSSARY.md.

## Boundary

Compare a claim with source passages and their applicable conditions. This is not a judgment of ultimate scientific truth or publication readiness. Do not edit a manuscript unless a separate task authorizes it. Under this protocol, return non-binding next actions only. An editorial decision is externally supplied; leave it unset until supplied.

## Retrieval Contract

1. Assign a claim ID and preserve the original wording and manuscript location when available.
2. Split compound statements into independently checkable subclaims. Keep the parent ID; do not change the manuscript.
3. State each subclaim's question, required source roles, coverage, and retrieval budget before searching.
4. Look up known bibcodes, DOI, or arXiv IDs directly. Otherwise locate candidates with title keywords, object names, and the relevant quantity.
5. For each retrieval request, record the subclaim ID and what the request must establish. A follow-up request must identify the remaining gap.
6. Initially request `bibcode,title,year,identifier,doi`, with 5 candidates per query. Add abstracts or authors only when needed. Do not print long author lists by default.
7. Select relevant papers before retrieving additional content. Metadata confirms identity, not scientific results.
8. If an abstract is insufficient, read the relevant body passage, table, figure, equation, or appendix. Follow the existing source-first workflow; do not automatically download PDFs.
9. Record the actual consulted version, location, short quotation or numerical extract, and necessary conditions. Preserve an arXiv version when available; never invent missing identifiers or versions.
10. Assess applicability and evidence direction separately. Keep conflicting sources visible rather than selecting only supporting results.
11. Stop within budget and report missing coverage, gaps, and the stop reason. Return a Markdown ledger; save it only when the calling task requests a file.

Example identity lookup using the existing CLI:

```bash
python scripts/ads_scix.py search 'bibcode:1929PNAS...15..168H' --rows 1 --fields bibcode title year identifier doi
python scripts/ads_scix.py arxiv search --id-list 2401.01234v2 --max-results 5
```

## Applicability

For a precise number, upper limit, or model interpretation, compare these dimensions explicitly:

| Dimension | Required comparison |
|---|---|
| Quantity | Definition, units, normalization, and conversion assumptions |
| Sample | Population, selection, size, and permitted scope of generalization |
| Energy band | Boundaries and observed/rest frame, when applicable |
| Model | Assumptions and parameters necessary for the result |
| Statistics | Confidence level, estimator, uncertainty, or limit convention |

Use `match`, `mismatch`, `unknown`, or `not_applicable` per dimension, with a short reason. Missing information is `unknown`, not a match. A mismatch does not automatically mean the source contradicts the claim.

For ordinary identity or bibliographic claims, use a concise comparison without the full profile.

| Status | Meaning |
|---|---|
| `direct_match` | The relevant source result directly addresses the subclaim under matching conditions. Identity claims can use metadata; numerical results, limits, sample findings, and model interpretations require a pinpointed body/table/figure/equation location. |
| `conditional_match` | The source addresses the assertion only under explicit conditions absent from or broader than the manuscript wording. |
| `partial_match` | Only part of the assertion is covered. Explain the remaining part; split it further when independently testable. |
| `unresolved` | A candidate exists, but location, access, definitions, or comparability cannot be established. |
| `no_result` | No qualifying source was found within the declared search scope and budget. This is not proof that no such source exists. |

Record status on each source-to-subclaim comparison. Record `no_result` on the subclaim when there is no qualifying source. Multiple conflicting comparisons must remain separate; do not reduce them to a single truth verdict.

Evidence roles: `primary_observation`, `conditional_limit`, `model_prediction`, `method_or_calibration`, `review_or_summary`. A source can have multiple roles, each tied to a subclaim and location. Corroboration describes a relationship between sources, not a new evidence type.

Evidence relations: `supports`, `limits`, `contradicts`, `not_directly_relevant`. Leave an undetermined relation unset with an explanation. A `direct_match` can `contradict` the manuscript. Relation is not a publication verdict.

For unresolved items, record one or more gap types plus a short explanation: `missing_location`, `scope_mismatch`, `band_mismatch`, `model_mismatch`, `statistical_definition_missing`, `inaccessible_source`, `budget_exhausted`, `no_qualifying_record`. Mismatch gaps can also accompany conditional/partial comparisons. Do not confuse a budget stop with missing scientific evidence.

## Default Budget and Stopping

Default: at most two targeted query variants per subclaim, with 5 candidates per variant. Known-ID lookup and targeted reading of an already selected source are separate from discovery variants; they remain subject to the declared identity/read budget. Do not bypass the limit by repeatedly renaming follow-up queries. Requests, candidates, and reading scope must be accounted for.

Declare the targeted reading scope, such as one selected section and its table or appendix. Use task-specific time or page limits when needed; do not claim a fixed time limit unless one was declared.

Stop when required role and applicability coverage is reached, two consecutive query variants yield no new qualifying source, the declared budget is exhausted, or no actionable source lead remains. An unresolved outcome is legitimate. One source is not a universal evidence-sufficiency threshold.

Record one stop reason: `required_coverage_reached`, `two_variants_no_new_source`, `query_budget_reached`, `reading_budget_reached`, `time_budget_reached`, `no_actionable_lead`. Record gaps separately. If widening the budget, state the new limit and the concrete reason before proceeding; never expand without a finite limit.

Non-binding next actions can include locate passage, obtain access, check version, add conditions, remove an unverified number, or defer. Recommend retaining a qualitative statement only if it has its own matching evidence. Search failure alone cannot justify calling a claim false or preserving it with vague wording.

## Markdown Ledger

Use a compact summary table, with detailed records below it when needed:

| Claim/subclaim ID | Original assertion | Source/version and location | Role | Status | Relation | Conditions/gaps | Next action | External editorial decision |
|---|---|---|---|---|---|---|---|---|

Each detailed record includes parent ID, original text, manuscript location if available, question, query parameters, source identity/URL, consulted version, retrieval time, evidence location/excerpt, applicability, gaps, and stop reason. Record ADS `q/fq/fl/rows/start/sort` and actual base URL, or the exact arXiv parameters and endpoint. An empty filter list is valid. Never store credentials or authenticated URLs containing tokens.

Record all available bibliographic identifiers without requiring every paper to have both DOI and arXiv ID. If a version cannot be pinned, state this limitation; do not implicitly label it the latest edition. A source-file line range must name the file and consulted edition.

### YAML-shaped Example

This is a protocol example, not a machine schema or real literature evidence. All source and numerical values below are fictional.

```yaml
claim_id: C-01
original_text: "All sources have efficiency below 1%."
manuscript_location: "Introduction, paragraph 2"
subclaim_id: C-01a
question: "Does the stated bound apply to all sources?"
budget:
  query_variants: 2
  candidates_per_variant: 5
  reading_scope: "Selected results section and associated table"
required_roles: [conditional_limit]
queries:
  - purpose: "Locate the cited bound and its sample"
    source: ADS
    base_url: "https://api.adsabs.harvard.edu"
    q: 'title:"fictional efficiency study"'
    fq: []
    fl: [bibcode, title, year, identifier, doi]
    rows: 5
    start: 0
    sort: "date desc"
    retrieved_at: "<actual retrieval timestamp>"
comparisons:
  - source:
      bibcode: "<returned bibcode>"
      doi: null
      arxiv_id: "<consulted versioned ID, if available>"
      source_url: "<actual source URL>"
      consulted_version: "<actual edition>"
    evidence:
      - role: conditional_limit
        location: "Section 4, Table 2"
        excerpt: "For the selected sample under model M, the 95% bound is 1%."
    applicability:
      quantity: {result: match, reason: "Same efficiency definition"}
      sample: {result: mismatch, reason: "Selected sample, not all sources"}
      energy_band: {result: unknown, reason: "Not yet established"}
      model: {result: mismatch, reason: "The manuscript omits model M"}
      statistics: {result: match, reason: "95% upper limit"}
    status: unresolved
    relation: limits
    gap_types: [scope_mismatch, model_mismatch]
    gap_explanation: "The generalization is unsupported; band comparability remains unverified."
stop_reason: reading_budget_reached
coverage_gap: "Band comparison is incomplete."
next_action: "Resolve band comparability and add the sample/model conditions."
editorial_decision: null  # Supplied only by the user or upstream editorial workflow.
```

Additional fictional acceptance scenarios:

| Scenario | Expected outcome |
|---|---|
| Same sample, band, quantity, model, and confidence level; located table gives the quoted limit | `direct_match` / `supports`, with location and numerical excerpt |
| Matching setup; located measurement is inconsistent with the manuscript number | `direct_match` / `contradicts`, not a supporting result |
| Relevant abstract but required results table cannot be accessed | `unresolved`, relation unset, `inaccessible_source` plus explanation |
| No qualifying record after two scoped variants | `no_result`, relation unset, `no_qualifying_record`, explicit scope and stop reason |

## Handoff and Build Boundary

Send the ledger, unresolved gaps, conflicts, and non-binding next actions to the caller. Final wording, citation placement, scientific sufficiency, and publication decisions belong to the manuscript workflow. Preserve externally supplied editorial decisions as such.

Official BibTeX export establishes export provenance, not local build compatibility. Undefined journal macros such as `\prd`, stale `.bbl` files, and citation-rendering failures belong to manuscript build checks. Do not relabel them as source-identity or scientific-evidence failures.
