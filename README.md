# PyToJSRegex Converter

A Python-to-JavaScript regular expression converter that handles syntax differences and flags between the two implementations.

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- Converts Python regex patterns to JavaScript-compatible syntax
- Handles key differences:
  - Strips `r` prefix and quotes
  - Converts `re.VERBOSE` flag by removing comments/whitespace
  - Transforms Python-specific syntax (`\A`, `\Z`, named groups)
  - Manages regex flags (`re.IGNORECASE` → `i`, etc.)
- Preserves complex patterns:
  - Non-capturing groups
  - Lookaround assertions
  - Atomic groups (with warnings)
- Generates conversion warnings for unsupported features
- Provides verbose conversion step tracking

## Installation

```bash
git clone https://github.com/Whitestar14/pytojsregex.git
cd pytojsregex
```

Requires Python 3.6+

## Usage

### Command Line Interface

```bash
python pytojsregex.py "your_python_regex" [--flags FLAGS] [-v]

# Example
python pytojsregex.py r"\b\d{3}-\d{4}\b" --flags "m"
# Output: /\b\d{3}-\d{4}\b/m
```

Options:
- `--flags`: Python regex flags (e.g., `im` for IGNORECASE+MULTILINE)
- `-v/--verbose`: Show detailed conversion steps
- `--test`: Run test suite

### Programmatic Use

```python
from pytojsregex import py_to_js_regex

js_regex, warnings, steps = py_to_js_regex(
    r'^(?P<date>\d{4}-\d{2}-\d{2})',
    py_flags=re.IGNORECASE,
    verbose=True
)
```

## Key Conversions

| Python Pattern      | JavaScript Equivalent      | Notes                             |
|---------------------|----------------------------|-----------------------------------|
| `r"\Astart"`        | `/^start/`                 | Start-of-string anchor            |
| `r"end\Z"`          | `/end$/`                   | End-of-string anchor              |
| `(?P<name>pattern)` | `(?<name>pattern)`         | Named groups                      |
| `r"(?>atomic)"`     | `(?:atomic)`               | Atomic groups → non-capturing     |
| `re.VERBOSE`        | Whitespace/comments removed| With conversion warnings           |

## Known Limitations

### 1. `re.VERBOSE` vs Literal `#` Characters (Test 33 Edge Case)

**Patterns containing `#` with `re.VERBOSE` may break:**

```python
# Python (with VERBOSE)
r"^(?:\w+\s*:\s*\d+\s*(?:#.*)?)+$", "mx"
```

**Expected JavaScript:**
```javascript
/^(?:\w+\s*:\s*\d+\s*(?:#.*)?)+$/m
```

**Current Behavior:**
```javascript
/^(?:\w+\s*:\s*\d+\s*(?:))+$/m  # Loses #.*
```

**Reason:** JavaScript lacks native support for Python's verbose regex parsing. The converter cannot reliably distinguish between:
- `#` used for comments (should be removed)
- `#` as literal regex syntax (should be preserved)

**Workaround:** Escape `#` or avoid `re.VERBOSE`:
```python
r"(?:\#.*)?"  # Escape the # character
```

### 2. Other Unsupported Features
- Conditional patterns (`(?(id)yes|no)`)
- Extended lookbehind assertions
- Regex module extensions (e.g. `\p` without `u` flag)

## Contributing

1. Report issues with:
   - Failing test cases
   - Incorrect conversions
   - Feature requests
2. Include:
   - Python regex pattern
   - Flags used
   - Expected JavaScript output

```bash
python pytojsregex.py --test  # Verify existing tests before contributing
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Note:** This tool provides best-effort conversions - always verify outputs using JavaScript regex testers.


