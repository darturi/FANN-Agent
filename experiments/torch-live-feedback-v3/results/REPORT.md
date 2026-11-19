# First v3 agent attempt: censored by idle shutdown

Job **23741092** used **21m02s** and completed its native startup/quality/timing qualification. The worker then stopped on its old fifteen-minute idle rule while the model was doing offline fitting. **No learned policy reached native evaluation, and no agent/oracle latency comparison exists yet.** This is an infrastructure-censored attempt, not an agent abstention or a zero-savings result.

The model made 24 settled requests for **$1.707958**, with zero uncertain charges. Qualification issued 252 ANN requests and charged 256 reserved slots. All seven source cases preserved native recall/count; its 112 diagnostic timings are not policy-performance evidence. The late liveness request was rejected before registration and used no ANN queries.

The raw return, compiler/module identity, source/quality/timing hashes, model transcript, fitting scripts and partial research state are preserved in the sibling `trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/run-v1` directory. The paid transcript and files can be resumed without resetting the ledger. The earlier unpaid TLS failure is recorded separately; it dispatched zero paid requests.

The heartbeat/resume repair has 31 passing tests and retains fixed allocation deadlines, idle expiry after disconnection, immutable closed decisions, settled charge accounting and tool idempotence. The prepared continuation needs approval for one additional job because the initial contract allowed one allocation. It is bounded to 5h38m, at most 5:59:02 over both jobs, the same $15 cumulative model ceiling, and the same 300,000 cumulative ANN cap. No continuation has been dispatched. See [CONTINUATION.md](../CONTINUATION.md).
