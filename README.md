# PyToJSRegex Converter

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python-to-JavaScript regular expression converter that handles syntax differences and flags between the two implementations.

## Features

- Converts Python regex patterns to JavaScript‑compatible syntax
- Handles key differences:
  - Python named groups `(?P<name>…)` → `(?<name>…)`
  - Named backreferences `(?P=name)` → `\k<name>` (with warning)
  - Anchors `\A` / `\Z` → `^` / `$` (with semantic warnings)
  - Verbose mode (`re.VERBOSE`) – removes comments and insignificant whitespace
  - Automatic addition of the `u` flag when Unicode property escapes (`\p{…}`, `\P{…}`) are present
- Warns about unsupported or risky features:
  - Lookbehind assertions (limited browser support)
  - Atomic groups `(?>…)`
  - Conditional patterns `(?(id)yes|no)`
  - Unbalanced parentheses
  - Invalid escapes (e.g., `\N`)
- Preserves all other valid regex constructs without alteration
- Provides verbose step‑by‑step conversion output
- Separate, comprehensive test suite

## Installation

```bash
git clone https://github.com/Whitestar14/pytojsregex.git
cd pytojsregex
```

Requires Python 3.6+.

## Usage

### Command Line

```bash
python py_to_js_regex.py "your_python_regex" [--flags FLAGS] [-v]

# Example
python py_to_js_regex.py "(?P<word>\\w+)" --flags "i"
# Output: /(?<word>\w+)/i
```

**Options:**

- `--flags`: Python regex flags as a string (e.g., `i`, `m`, `s`, `x`, `u`; combine like `imx`)
- `-v` / `--verbose`: show each conversion step
- `--test`: run the test suite

### Programmatic Use

```python
from py_to_js_regex import py_to_js_regex, parse_flags

js_regex, warnings, steps = py_to_js_regex(
    r'^(?P<date>\d{4}-\d{2}-\d{2})',
    py_flags=parse_flags('i'),
    verbose=True
)
print(js_regex)   # /^(?<date>\d{4}-\d{2}-\d{2})/i
```

## Key Conversions

| Python Pattern       | JavaScript Equivalent | Notes                                                       |
|----------------------|-----------------------|-------------------------------------------------------------|
| `(?P<name>…)`       | `(?<name>…)`         | Named capturing groups                                      |
| `(?P=name)`          | `\k<name>`           | Named backreferences (warning: limited browser support)     |
| `\A` / `\Z`         | `^` / `$`            | Converted with semantic warnings (especially with `m` flag) |
| `re.VERBOSE` (flag) | Whitespace/comments removed | Comments start with unescaped `#`; literal `#` must be escaped: `\#` |
| `(?x)` inline flag  | removed               | Inline verbose flag is stripped                             |
| `\p{…}` / `\P{…}`   | unchanged             | Automatically adds `u` flag                                 |

## Known Limitations

- **Lookbehind** support in JavaScript is still not universal – the tool emits a warning.
- **Atomic groups** cannot be emulated – a warning is given and the group is left as‑is.
- **Conditional patterns** (`(?(1)…|…)`) are not supported in any JavaScript engine.
- **Verbose mode and literal `#`** – in verbose patterns, an unescaped `#` begins a comment. To match a literal hash, escape it: `\#`. The converter preserves escaped hashes correctly.

## Running the Tests

```bash
python -m pytest test_py_to_js_regex.py
# or
python py_to_js_regex.py --test
```

All tests are in `test_py_to_js_regex.py` and can be run independently.

## Contributing

Report issues or contribute improvements via [GitHub](https://github.com/Whitestar14/pytojsregex). Please include:
- Failing test cases with expected vs. actual output
- The exact Python regex and flags used

## License

This project is licensed under the MIT License
