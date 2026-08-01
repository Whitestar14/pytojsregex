"""
Test suite for py_to_js_regex.
Run with: python test_py_to_js_regex.py
Or via the main module: python py_to_js_regex.py --test
"""

from py_to_js_regex import py_to_js_regex, parse_flags


def run_tests():
    """Run all tests and report results."""
    tests = _build_tests()
    passed = 0
    failed = 0
    for i, (py_regex, flags_str, expected_js, expected_warnings) in enumerate(tests, 1):
        py_flags = parse_flags(flags_str)
        js_regex, warnings_list, _ = py_to_js_regex(py_regex, py_flags, verbose=False)

        regex_ok = (js_regex == expected_js)
        warnings_ok = set(warnings_list) == set(expected_warnings)

        if regex_ok and warnings_ok:
            print(f"Test {i:02d} passed")
            passed += 1
        else:
            print(f"Test {i:02d} FAILED:")
            print(f"  Input:          {py_regex!r}")
            print(f"  Flags:          {flags_str}")
            print(f"  Expected regex: {expected_js}")
            print(f"  Got regex:      {js_regex}")
            if not warnings_ok:
                print("  Expected warnings:")
                for w in expected_warnings:
                    print(f"    - {w}")
                print("  Got warnings:")
                for w in warnings_list:
                    print(f"    - {w}")
            failed += 1
        print()

    print(f"{passed} passed, {failed} failed out of {len(tests)}")
    return failed == 0


def _build_tests():
    """Return a list of test cases (regex, flags_str, expected_js, expected_warnings)."""
    tests = []

    def t(regex, flags_str, expected_js, expected_warnings=None):
        tests.append((regex, flags_str, expected_js, expected_warnings or []))

    # --- Basic patterns ---
    t(r"hello", "", r"/hello/")
    t(r"hello world", "", r"/hello world/")
    t(r"", "", r"//")

    # --- Character classes ---
    t(r"[a-z]", "", r"/[a-z]/")
    t(r"[^a-z]", "", r"/[^a-z]/")
    t(r"[]]", "", r"/[]]/")
    t(r"[^]]", "", r"/[^]]/")
    t(r"[\]]", "", r"/[\]]/")

    # --- Quantifiers ---
    t(r"a*", "", r"/a*/")
    t(r"a+", "", r"/a+/")
    t(r"a?", "", r"/a?/")
    t(r"a{3}", "", r"/a{3}/")
    t(r"a{3,}", "", r"/a{3,}/")
    t(r"a{3,5}", "", r"/a{3,5}/")

    # --- Anchors ---
    t(r"^start", "", r"/^start/")
    t(r"end$", "", r"/end$/")
    t(r"\bword\b", "", r"/\bword\b/")
    t(r"\Astart", "", r"/^start/",
      [r"\A and \Z anchors were converted to '^' and '$'. The semantics are not identical; "
       "review the resulting pattern carefully."])
    t(r"end\Z", "", r"/end$/",
      [r"\A and \Z anchors were converted to '^' and '$'. The semantics are not identical; "
       "review the resulting pattern carefully."])
    t(r"\Astart", "m", r"/^start/m",
      [r"\A and \Z anchors were converted to '^' and '$', but because the 'm' flag is set, "
       "their behaviour may differ (^ and $ will match line starts/ends)."])

    # --- Groups and references ---
    t(r"(group)", "", r"/(group)/")
    t(r"(?:non-cap)", "", r"/(?:non-cap)/")
    t(r"(group)\1", "", r"/(group)\1/")
    t(r"(?P<name>group)", "", r"/(?<name>group)/")
    t(r"(?P=name)", "", r"/\k<name>/",
      ["Named group reference '(?P=name)' is not directly supported in JavaScript. "
       "Converted to '\\k<name>', but may not work in all browsers."])

    # --- Lookarounds ---
    t(r"(?=pos)", "", r"/(?=pos)/")
    t(r"(?!neg)", "", r"/(?!neg)/")
    t(r"(?<=pos)", "", r"/(?<=pos)/",
      ["Lookbehind assertions have limited support in JavaScript."])
    t(r"(?<!neg)", "", r"/(?<!neg)/",
      ["Lookbehind assertions have limited support in JavaScript."])

    # --- Shorthand classes ---
    t(r"\d\D\w\W\s\S", "", r"/\d\D\w\W\s\S/")

    # --- Flags ---
    t(r"case", "i", r"/case/i")
    t(r"^multi$", "m", r"/^multi$/m")
    t(r".", "s", r"/./s")

    # --- Unicode property escapes (auto 'u' flag) ---
    t(r"\p{Greek}", "", r"/\p{Greek}/u",
      ["Unicode property escapes require the 'u' flag, which will be added automatically."])
    t(r"\P{ASCII}", "", r"/\P{ASCII}/u",
      ["Unicode property escapes require the 'u' flag, which will be added automatically."])
    t(r"\p{Greek}", "u", r"/\p{Greek}/u",
      ["Unicode property escapes require the 'u' flag, which will be added automatically."])

    # --- Atomic groups (warning only, no conversion) ---
    t(r"(?>atomic)", "", r"/(?>atomic)/",
      ["Atomic groups (?>...) are not supported in JavaScript. The pattern must be rewritten."])

    # --- Conditional patterns ---
    t(r"(?(1)then|else)", "", r"/(?(1)then|else)/",
      ["Conditional patterns are not supported in JavaScript."])

    # --- Verbose mode ---
    t(r"""(?x)
        \d+  # digits
        \s*  # optional whitespace
        \w+  # word chars
        """, "x", r"/\d+\s*\w+/")
    t(r"""(?x)
        [a-z ]+  # letters and space inside class
        """, "x", r"/[a-z ]+/")
    t(r"""(?x)
        \[hello\]  # escaped brackets
        """, "x", r"/\[hello\]/")

    # --- Invalid escape \N removed ---
    t(r"\N", "", r"//",
      [r"'\N' is not a valid regex escape and will be removed from the pattern."])
    t(r"a\Nb", "", r"/ab/",
      [r"'\N' is not a valid regex escape and will be removed from the pattern."])

    # --- Unbalanced parentheses (warning only) ---
    t(r"(unclosed", "", r"/(unclosed/",
      ["Parentheses are unbalanced; the regex may not work as expected."])
    t(r"unopened)", "", r"/unopened)/",
      ["Parentheses are unbalanced; the regex may not work as expected."])

    # --- Complex multi‑flag example ---
    t(r"^(?:(?P<word>\w+)\s*:\s*(?P<number>\d+)\s*(?:\#.*)?\n?)+$", "mx",
      r"/^(?:(?<word>\w+)\s*:\s*(?<number>\d+)\s*(?:#.*)?\n?)+$/m")

    # --- Realistic patterns ---
    t(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
      "", r"/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/")

    # --- Multiple warnings ---
    t(r"(?P=x)\A\d\Z(?>)", "m",
      r"/\k<x>^\d$(?>)/m",
      [
          "Named group reference '(?P=x)' is not directly supported in JavaScript. "
          "Converted to '\\k<x>', but may not work in all browsers.",
          r"\A and \Z anchors were converted to '^' and '$', but because the 'm' flag "
          "is set, their behaviour may differ (^ and $ will match line starts/ends).",
          "Atomic groups (?>...) are not supported in JavaScript. The pattern must be rewritten."
      ])

    return tests


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
