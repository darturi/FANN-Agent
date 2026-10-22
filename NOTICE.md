# Third-party notices

FANNAgent is distributed under the [MIT license](LICENSE). Project-specific
implementation is by Daniel Arturi (darturi).

## FANNBench shared primitives

Shared neutral search, policy, data, and evidence algorithms originated in the
FANNBench harness. Its original MIT notice is retained below.

```text
MIT License

Copyright (c) 2026 FANNBench contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Dependencies and research

FANNAgent uses mini-swe-agent 2.4.6 for the base agent loop and model interfaces,
with LiteLLM model dispatch. mini-swe-agent is a separately installed MIT-licensed
dependency, copyright 2025 Kilian A. Lieret and Carlos E. Jimenez; its distribution
retains its own license. This repository does not vendor a fork of that agent.

Other dependencies retain their own licenses and are listed in
[pyproject.toml](pyproject.toml) and [uv.lock](uv.lock). Dependency installation
does not transfer ownership of those projects to FANNAgent. The separate pgvector
extension preserves its PostgreSQL, pgvector, and instrumentation notices.

The [research-guidance document](docs/RESEARCH_GUIDANCE.md) identifies the papers
used by the cited primer and describes their limits of application. Citing those
papers does not claim authorship of their methods or datasets.
