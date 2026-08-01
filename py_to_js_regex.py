"""
py_to_js_regex - Convert Python regular expressions to JavaScript-compatible form.
"""

import re
import sys
import argparse


class RegexConversionWarning(Warning):
    pass


class RegexConversionError(Exception):
    pass


def py_to_js_regex(py_regex, py_flags=0, verbose=False):
    """
    Convert a Python regular expression to its JavaScript equivalent.

    Args:
        py_regex (str): The Python regular expression pattern (no quotes, no 'r' prefix).
        py_flags (int): Integer representing Python regex flags.
        verbose (bool): If True, return detailed conversion steps.

    Returns:
        tuple: (js_regex, warnings_list, steps)
            js_regex (str): The converted JavaScript regular expression.
            warnings_list (list): List of warnings.
            steps (list): Conversion steps (if verbose).
    """
    warnings_list = []
    steps = []
    original_regex = py_regex

    if verbose:
        steps.append(f"Original Python regex: {original_regex}")

    try:
        # Handle verbose mode (VERBOSE flag) early
        if py_flags & re.VERBOSE:
            py_regex = handle_verbose_mode(py_regex)
            py_flags &= ~re.VERBOSE
            if verbose:
                steps.append(f"Handled verbose mode: {py_regex}")

        # Anchor warnings – must be checked before conversion removes \A / \Z
        if r'\A' in py_regex or r'\Z' in py_regex:
            if py_flags & re.MULTILINE:
                warnings_list.append(
                    r"\A and \Z anchors were converted to '^' and '$', but because the 'm' flag "
                    "is set, their behaviour may differ (^ and $ will match line starts/ends)."
                )
            else:
                warnings_list.append(
                    r"\A and \Z anchors were converted to '^' and '$'. The semantics are not "
                    "identical; review the resulting pattern carefully."
                )
            if verbose:
                steps.append(r"Warned about \A / \Z anchor conversion")

        # Convert Python‑specific syntax (named groups, basic anchors)
        js_regex = conservative_conversion(py_regex)
        if verbose and js_regex != py_regex:
            steps.append(f"Converted Python‑specific syntax: {js_regex}")

        # Handle named group references (backreferences)
        js_regex, ref_warnings = handle_named_group_references(js_regex)
        warnings_list.extend(ref_warnings)
        if verbose and ref_warnings:
            steps.append(f"Handled named group references: {js_regex}")

        # Handle atomic groups – warn, but do NOT convert (semantics are lost)
        atomic_warnings = warn_atomic_groups(js_regex)
        warnings_list.extend(atomic_warnings)
        if verbose and atomic_warnings:
            steps.append("Warned about atomic groups")

        # Handle Unicode property escapes – add 'u' flag automatically
        js_regex, unicode_warnings = detect_unicode_properties(js_regex)
        warnings_list.extend(unicode_warnings)
        if unicode_warnings:
            py_flags |= re.UNICODE  # ensures the 'u' flag is set later
            if verbose:
                steps.append("Detected Unicode property escapes; 'u' flag will be added")

        # Check lookbehind support
        if '(?<=' in js_regex or '(?<!' in js_regex:
            warnings_list.append("Lookbehind assertions have limited support in JavaScript.")
            if verbose:
                steps.append("Warned about lookbehind assertions")

        # Warn about unsupported escapes (\N)
        if r'\N' in js_regex:
            warnings_list.append(r"'\N' is not a valid regex escape and will be removed from the pattern.")
            js_regex = js_regex.replace(r'\N', '')   # remove invalid escape
            if verbose:
                steps.append("Removed invalid \\N escape")

        # Check for other unsupported features
        unsupported_warnings = check_unsupported_features(js_regex)
        warnings_list.extend(unsupported_warnings)
        if verbose and unsupported_warnings:
            steps.append("Checked for unsupported features")

        # Ensure balanced parentheses (only check, do not modify)
        if not are_parentheses_balanced(js_regex):
            warnings_list.append("Parentheses are unbalanced; the regex may not work as expected.")
            if verbose:
                steps.append("Warning: unbalanced parentheses detected")

        # Convert flags to JavaScript format
        js_flags = handle_flags(py_flags)
        if verbose:
            steps.append(f"Converted flags: {js_flags}")

        # Construct final JavaScript regex
        js_regex = f"/{js_regex}/{js_flags}"
        if verbose:
            steps.append(f"Final JavaScript regex: {js_regex}")

        return js_regex, warnings_list, steps

    except RegexConversionError as e:
        return None, [str(e)], steps


def conservative_conversion(regex):
    """
    Perform minimal conversions to make a Python regex valid in JavaScript.
    Does NOT strip quotes or prefixes, and does not alter optional groups.
    """
    # Named groups: (?P<name>...) → (?<name>...)
    js_regex = re.sub(r'\(\?P<(\w+)>', r'(?<\1>', regex)
    # Anchor conversion – keeps ^ and $; \A / \Z were already warned about.
    js_regex = js_regex.replace(r'\A', '^').replace(r'\Z', '$')
    # Unescape unnecessary backslashes (e.g., \# → #)
    js_regex = js_regex.replace(r'\#', '#')
    return js_regex


def handle_verbose_mode(regex):
    """
    Remove comments and whitespace from a Python VERBOSE regex.
    Comments are removed first, then whitespace outside character classes.
    """
    # Remove comments (lines starting with #, not escaped)
    lines = []
    for line in regex.split('\n'):
        # Find first unescaped # outside a character class
        in_class = False
        i = 0
        while i < len(line):
            if line[i] == '\\':
                i += 2   # skip escaped char
                continue
            if line[i] == '[':
                in_class = True
            elif line[i] == ']':
                in_class = False
            elif line[i] == '#' and not in_class:
                line = line[:i]
                break
            i += 1
        lines.append(line)
    stripped = '\n'.join(lines)

    # Remove whitespace characters that are not inside a character class
    result = []
    in_class = False
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if ch == '\\':
            # keep escaped character as-is
            result.append(ch)
            i += 1
            if i < len(stripped):
                result.append(stripped[i])
            i += 1
            continue
        if ch == '[' and not in_class:
            in_class = True
            result.append(ch)
        elif ch == ']' and in_class:
            in_class = False
            result.append(ch)
        elif ch.isspace() and not in_class:
            # skip whitespace outside classes
            pass
        else:
            result.append(ch)
        i += 1

    # Remove the (?x) flag if present
    clean = re.sub(r'\(\?x\)', '', ''.join(result))
    return clean.strip()


def handle_named_group_references(regex):
    r"""Convert Python named backreferences (?P=name) to \k<name>."""
    warnings = []

    def replace_named_ref(match):
        warnings.append(
            f"Named group reference '(?P={match.group(1)})' is not directly supported in JavaScript. "
            f"Converted to '\\k<{match.group(1)}>', but may not work in all browsers."
        )
        return f"\\k<{match.group(1)}>"

    regex = re.sub(r'\(\?P=(\w+)\)', replace_named_ref, regex)
    return regex, warnings


def warn_atomic_groups(regex):
    """Warn if atomic groups are present (no conversion – semantics change)."""
    warnings = []
    if r'(?>' in regex:
        warnings.append("Atomic groups (?>...) are not supported in JavaScript. The pattern must be rewritten.")
    return warnings


def detect_unicode_properties(regex):
    """Detect Unicode property escapes and emit a warning."""
    warnings = []
    if r'\p' in regex or r'\P' in regex:
        warnings.append("Unicode property escapes require the 'u' flag, which will be added automatically.")
    return regex, warnings


def check_unsupported_features(regex):
    """Check for patterns that JavaScript cannot handle."""
    warnings = []
    if r'(?(1)' in regex:
        warnings.append("Conditional patterns are not supported in JavaScript.")
    return warnings


def are_parentheses_balanced(regex):
    """Return True if parentheses are balanced, ignoring escaped ones and character classes."""
    stack = 0
    in_class = False
    i = 0
    while i < len(regex):
        ch = regex[i]
        if ch == '\\':
            i += 2   # skip escaped character
            continue
        if ch == '[':
            in_class = True
        elif ch == ']':
            in_class = False
        elif not in_class:
            if ch == '(':
                stack += 1
            elif ch == ')':
                if stack == 0:
                    return False
                stack -= 1
        i += 1
    return stack == 0


def handle_flags(py_flags):
    """Convert Python regex flags to JavaScript flag string."""
    js_flags = ''
    if py_flags & re.IGNORECASE:
        js_flags += 'i'
    if py_flags & re.MULTILINE:
        js_flags += 'm'
    if py_flags & re.DOTALL:
        js_flags += 's'
    if py_flags & re.UNICODE:
        js_flags += 'u'
    return js_flags


def parse_flags(flags_str):
    """Parse a string of flag letters into a Python flags integer."""
    flags = 0
    if 'i' in flags_str:
        flags |= re.IGNORECASE
    if 'm' in flags_str:
        flags |= re.MULTILINE
    if 's' in flags_str:
        flags |= re.DOTALL
    if 'x' in flags_str:
        flags |= re.VERBOSE
    if 'u' in flags_str:
        flags |= re.UNICODE
    return flags


def main():
    parser = argparse.ArgumentParser(description="Convert Python regex to JavaScript regex")
    parser.add_argument("regex", nargs='?', help="Python regex pattern")
    parser.add_argument("-f", "--flags", default="", help="Python regex flags (e.g., 'im')")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("-v", "--verbose", action="store_true", help="Output conversion steps")
    args = parser.parse_args()

    if args.test:
        # Import and run the test suite from an external test file
        try:
            from test_py_to_js_regex import run_tests
            run_tests()
        except ImportError:
            print("Error: test_py_to_js_regex.py not found.", file=sys.stderr)
            sys.exit(1)
    elif args.regex:
        try:
            py_flags = parse_flags(args.flags)
            js_regex, warnings_list, steps = py_to_js_regex(args.regex, py_flags, verbose=args.verbose)
            print(f"JavaScript regex: {js_regex}")
            if warnings_list:
                print("Warnings:")
                for w in warnings_list:
                    print(f"- {w}")
            if args.verbose:
                print("\nConversion steps:")
                for s in steps:
                    print(f"- {s}")
        except RegexConversionError as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
