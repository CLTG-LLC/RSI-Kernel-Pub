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

## Dependencies resolved in `uv.lock`

None of these are vendored in this repository; they are installed from their own distributions and keep their own licences. Several NumPy/SciPy versions are lockfile alternatives for different Python versions, not all installed together.

| Distribution | Version | Licence |
|---|---|---|
| colorama | 0.4.6 | BSD-3-Clause |
| exceptiongroup | 1.3.1 | MIT, plus PSF licence notice for copied Python standard-library portions |
| gepa | 0.1.4 (Git `3d34469165f0d604df3b48f1d5c776e9080f3da0`) | MIT |
| iniconfig | 2.3.1 | MIT |
| numpy | 2.2.6 | BSD-3-Clause core, with bundled-component notices |
| numpy | 2.4.6, 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.7.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pytest | 9.2.0 | MIT |
| scipy | 1.15.3, 1.17.1, 1.18.1 | BSD-3-Clause core, with bundled-component licences and notices |
| tomli | 2.5.0 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |

NumPy and SciPy binary wheels bundle further components (for example OpenBLAS/LAPACK under BSD-family licences, the GCC runtime under GPL with the GCC Runtime Library Exception, and libquadmath under LGPL). Any redistribution of those binaries, such as a bundled wheel set or container image, must keep the notices shipped inside them.

The build backend, hatchling, is not pinned in `uv.lock` and is not redistributed by this project.
