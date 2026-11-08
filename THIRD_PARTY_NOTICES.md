# Third-party notices

The [PolyForm Noncommercial License 1.0.0](LICENSE) covers only code and documentation owned by this project. Third-party components keep their own licences, listed below. Nothing here relicenses a third-party component under PolyForm.

## Ported code

### noop (MIT)

- **File:** `src/rsi_kernel/adapters/gdpevo_memory/library.py` (the full MIT notice is also kept at the top of that file).
- **Upstream:** https://github.com/huacnlee/noop at commit `246561d04d444f90ed634af5cede9f2fd682a22a`, `cloud/src/tools.ts:43,47–56,344–357` and `src/brain.ts:75–97`.

```
MIT License
Copyright (c) 2026 Jason Lee

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

### OpenHands benchmarks prompt (MIT)

- **File:** `src/rsi_kernel/adapters/swebench_live/prompt_template.j2`.
- **Upstream:** https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/benchmarks/swebenchmultilingual/prompts/default.j2
- **Named local exceptions:** skill sentence appended; Python/conda-specific environment lines 9, 22 and 23 removed. See `docs/prereg-fd2-swebench-live.md` section 2.1.
- **Licence source:** https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/LICENSE

```
MIT License

Copyright (c) 2025 All Hands AI

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

## Dependencies resolved in `uv.lock`

None of these are vendored in this repository; they are installed from their own distributions and keep their own licences. Several NumPy/SciPy versions are lockfile alternatives for different Python versions, not all installed together.

| Distribution | Version | Licence |
|---|---|---|
| annotated-types | 0.8.0 | MIT |
| anyio | 4.16.0 | MIT |
| attrs | 26.1.0 | MIT |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| exceptiongroup | 1.3.1 | MIT, plus PSF licence notice for copied Python standard-library portions |
| gepa | 0.1.4 (Git `3d34469165f0d604df3b48f1d5c776e9080f3da0`) | MIT |
| h11 | 0.16.0 | MIT |
| httpcore2 | 2.14.0, 2.16.0 | BSD-3-Clause |
| httpx2 | 2.14.0, 2.16.0 | BSD-3-Clause |
| httpx2-jsfetch | 1.0 | BSD-3-Clause (Emscripten-only marker) |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| mcp | 2.3.0 | MIT |
| mcp-types | 2.3.0 | MIT |
| numpy | 2.2.6 | BSD-3-Clause core, with bundled-component notices |
| numpy | 2.4.6, 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.7.0 | MIT |
| pycparser | 3.11, 3.12 | BSD-3-Clause |
| pydantic | 2.14.3 | MIT |
| pydantic-core | 2.50.4 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyjwt | 2.15.1 | MIT |
| pytest | 9.2.0 | MIT |
| python-multipart | 0.0.32, 0.0.33 | Apache-2.0 |
| pywin32 | 312 | PSF-2.0 (Windows-only marker) |
| referencing | 0.37.0 | MIT |
| rpds-py | 0.30.0, 2026.9.1 | MIT |
| scipy | 1.15.3, 1.17.1, 1.18.1 | BSD-3-Clause core, with bundled-component licences and notices |
| sse-starlette | 3.5.1, 3.6.0 | BSD-3-Clause |
| starlette | 1.7.0, 1.10.0 | BSD-3-Clause |
| tomli | 2.5.0 | MIT |
| truststore | 0.10.5 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.5 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |

NumPy and SciPy binary wheels bundle further components (for example OpenBLAS/LAPACK under BSD-family licences, the GCC runtime under GPL with the GCC Runtime Library Exception, and libquadmath under LGPL). Any redistribution of those binaries, such as a bundled wheel set or container image, must keep the notices shipped inside them.

The build backend, hatchling, is not pinned in `uv.lock` and is not redistributed by this project.
