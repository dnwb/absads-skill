# ABSADS Claim Retrieval

This context covers astronomy literature retrieval and comparison of manuscript claims with identifiable source passages. Source applicability is distinct from scientific truth, manuscript editing, and manuscript build compatibility.

## Language

**Claim（论断）**:
A specific statement whose quantity, scope, or interpretation can be compared with an identifiable source passage.
_Avoid_: Topic, paper
**Subclaim（子论断）**:
A separately testable part of a claim, linked to its parent manuscript statement when a compound claim contains multiple factual or interpretive assertions.
_Avoid_: Evidence fragment, search result

**Source Identity（来源身份）**:
The identity and version of a paper, established through its bibliographic identifiers and source provenance.
_Avoid_: Scientific validity, claim support

**Consulted Version（实际读取版本）**:
The specific edition of a source used for a comparison, identified by available version identifiers, publication information, or retrieval details. A source location refers to this edition, not implicitly to the latest edition.
_Avoid_: Latest version assumed, mandatory DOI and arXiv pair

**Applicability Profile（适用性档案）**:
A structured comparison of sample, energy band, model assumptions, and statistical definition used only when a subclaim contains a precise number, limit, or model interpretation.
_Avoid_: Universal evidence score, publication verdict
**Applicability Status（适用性状态）**:
A retrieval outcome describing how directly a source maps to a subclaim: `direct_match`, `conditional_match`, `partial_match`, `unresolved`, or `no_result`; it does not assert scientific truth.
_Avoid_: Proven, disproven, publication-ready
**Next Action（下一步建议）**:
A non-binding retrieval or wording suggestion tied to a documented applicability gap, such as locating a source passage, adding a condition, or removing an unverified number; it does not modify the manuscript.
_Avoid_: Automatic edit, publication decision
**Direct Match（直接匹配）**:
An applicability status for which the source evidence meets the claim type's location requirement: metadata can directly match identity or bibliographic claims, while numerical results, limits, sample findings, and model interpretations require a pinpointed passage in the body, table, figure, or equation.
_Avoid_: Abstract relevance, paper existence
**Evidence Role（证据角色）**:
A role assigned to a source-to-subclaim relation and anchored to a source location: `primary_observation`, `conditional_limit`, `model_prediction`, `method_or_calibration`, or `review_or_summary`; one source can have multiple roles, with supplementary explanation.
_Avoid_: Permanent paper type, evidence score

**Evidence Relation（证据关系）**:
The direction of a source's bearing on a subclaim: `supports`, `limits`, `contradicts`, or `not_directly_relevant`. An undetermined relation is left unset with a gap explanation; a direct match can contradict a claim.
_Avoid_: Applicability status, scientific verdict

**Retrieval Budget（检索预算）**:
A declared limit on query variants, candidate results, reading scope, time, or pages for one subclaim, with a reason recorded when the default limit is exceeded.
_Avoid_: Universal search quota, proof threshold

**Claim Ledger（论断台账）**:
A human-readable Markdown record that maps claims and subclaims to queries, source identities, evidence roles, applicability statuses, gaps, and next actions; the first version is not an automatically generated manifest.
_Avoid_: Bibliography, manuscript revision log
**Editorial Decision（编辑决定）**:
An externally made manuscript-handling outcome recorded after retrieval, such as retain, qualify, remove a number, rewrite, or defer; `absads` does not make this decision.
_Avoid_: Automatic edit, retrieval status

**Gap Type（缺口类型）**:
A structured description of why a subclaim remains unresolved, such as missing location, scope mismatch, band mismatch, model mismatch, missing statistical definition, inaccessible source, exhausted budget, or no qualifying record.
_Avoid_: Failure, disproof

**Evidence Excerpt（证据摘录）**:
A brief quotation or numerical extract paired with an identifiable source location and retaining the conditions necessary to understand it; it is not a copy of the full passage.
_Avoid_: Full-text archive, context-free number
**Source Applicability（来源适用性）**:
The degree to which a source passage addresses a claim under matching sample, energy band, model assumptions, and statistical definitions. An applicability assessment is not a judgment of ultimate scientific truth or publication readiness.
_Avoid_: Truth verification, manuscript approval
