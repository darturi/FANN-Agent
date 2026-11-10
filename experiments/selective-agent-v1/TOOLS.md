# Selective policy study tools

Work offline in `/workspace`. Read this once. Import the syntax/transport helper:

```python
import sys,json
sys.path.insert(0,'/evidence')
from policy_tools import call,policy
context=json.load(open('/evidence/context.json'))
seeds=json.load(open('/evidence/seeds.json'))
```

The corpus is a JSON object: `queries` is a list of 600 cases, `folds` maps 200
vector groups to five development folds. Each case has `query_id`, `group`,
`stratum`, `native_recall`, `native_work`, `base_states` (23 static observations),
`local_states` (34 progress observations), and `labels.base` / `labels.local`.
Join a string checkpoint key to the state with that `checkpoint_index`.
Each actual label has recall, valid, returned_count, layer0_distances, and two
fixed-stop saving proxies. Negative saving is slower. Never print the whole corpus.
The 19-feature view projects base_states; its own costs are unmeasured.

Runtime eligibility uses actual predicates, not IDs. Allowed eligibility names:
`unfiltered`, `votes32`, `votes108`; choose a nonempty subset. All query types
remain in the measured workload. A skipped type performs genuine native SQL,
including the real measured routing cost. There is no engine work on bypass.

`policy(name, body, profile='light19', eligible=[...])` creates the canonical
availability/checkpoint guard. The body has at most three decision levels.
Profiles are `light19`, `static23`, `progress34`; see context for types/groups.
Trees use the existing expression DSL: e.g. a feature comparison is
`{'op':'gte','args':[{'feature':'checkpoint_index'},{'int':32}]}`.
An if node is `{'if': expression,'then':'stop','else':'continue'}`.
Boolean literals use `{'bool': True}`, integer literals `{'int': 32}`, floats
`{'float': .1}`. Missing observations continue; unknown recall stays unknown.

Calls (all arguments are keyword arguments after the operation):

- `call('inspect')`: context, exports, requests/spending/fit counts.
- `call('fit', profile=..., eligible=[...], risk=1280)`: trusted first-stop
  beam search with five group folds plus refit, charging six of the 96 fits.
  Risk choices: 20,80,320,1280. Output includes a candidate and provenance.
  Light19 ranks physical work; other profiles rank their actual fixed-stop
  proxies. Native bypass uses zero ONLY for ranking, not as a latency result.
- `call('screen', policy=p)`: compact recall, first-stop and proxy diagnostics.
- `call('diagnose', policy=p)`: detailed failure diagnostics.
- `call('export', policy=p, origin='describe authorship or seed/helper reuse')`:
  irreversible semantic export. Phase A has three slots; B has one new revision.
- `call('artifact', hash=...)`: retrieve a saved development artifact.
- Phase A: `call('pause', reason='...')` after 1-3 exports freezes proposals.
- Phase B: `call('finish', decision='EXPORTED_SEMANTIC_HASH', reason='...')`,
  or decision `abstain`. One exported revision becomes the sole final choice.

Each tool result is wrapped by the `fannagent-tool` transport. The helper returns
its result or raises on an error. Use concise prints of the relevant fields.
Cost proxies do not qualify latency. Known recall failures are allowed in pilot
proposals. Final recall requires a lower 95% policy-minus-native bound >=-.005
overall AND every filter, complete top-10 and native recall >=.95 per filter.
Development selection additionally reserves -.0025 recall. Actual cold AND warm
latency confidence bounds must improve. No query identity or ground truth may be
encoded in a runtime tree. Earlier seeds must be credited as reused references.

There are at most eight provider attempts in A and four in B, 120 commands total,
60 active minutes total and 60 seconds per command. Tools show remaining budget.
Finish/pause explicitly before limits: the host never chooses a candidate for you.
The unused confirmation data and reserved vectors are unavailable.
