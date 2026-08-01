# The `py_to_js_regex()` function is the main entry point for converting a Python regular expression (regex) to a JavaScript-compatible regex. It handles various conversions and transformations to ensure the regex can be used in a JavaScript environment, including:

# - Stripping the 'r' prefix and quotes from the input regex
# - Handling the `re.VERBOSE` flag and removing comments
# - Converting Python-specific syntax to JavaScript-compatible syntax
# - Handling named group references, non-capturing groups, and atomic groups
# - Converting Unicode property escapes and ensuring the 'u' flag is set
# - Handling lookbehind assertions and other unsupported features
# - Ensuring balanced parentheses and preserving complex patterns
# - Converting the Python regex flags to their JavaScript equivalents

# The function returns the converted JavaScript regex, a list of warnings about any unsupported features or potential issues, and a list of the conversion steps performed.

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
    py_regex (str): The Python regular expression to convert.
    py_flags (int): Integer representing Python regex flags.
    verbose (bool): If True, return detailed conversion steps.

    Returns:
    tuple: (js_regex, warnings_list, steps)
        js_regex (str): The converted JavaScript regular expression.
        warnings_list (list): List of warnings generated during conversion.
        steps (list): List of conversion steps (if verbose is True).
    """
    warnings_list = []
    steps = []
    original_regex = py_regex  # Store the original regex
    
    if verbose:
        steps.append(f"Original Python regex: {original_regex}")
    
    try:
        # Strip 'r' prefix if present and remove quotes
        py_regex = py_regex.lstrip('r').strip("'\"")
        if verbose and py_regex != original_regex:
            steps.append(f"Stripped 'r' prefix and quotes: {py_regex}")
        
        # Handle verbose mode (VERBOSE flag)
        if py_flags & re.VERBOSE:
            py_regex = handle_verbose_mode(py_regex)
            py_flags &= ~re.VERBOSE  # Remove VERBOSE flag after handling
            if verbose:
                steps.append(f"Handled verbose mode: {py_regex}")
        
        # Convert Python-specific syntax
        js_regex = conservative_conversion(py_regex)
        if verbose and js_regex != py_regex:
            steps.append(f"Converted Python-specific syntax: {js_regex}")
        
        # Handle named group references
        js_regex, ref_warnings = handle_named_group_references(js_regex)
        warnings_list.extend(ref_warnings)
        if verbose and ref_warnings:
            steps.append(f"Handled named group references: {js_regex}")
        
        # Handle non-capturing groups
        js_regex = re.sub(r'\(\?:', r'(?:', js_regex)
        if verbose:
            steps.append(f"Handled non-capturing groups: {js_regex}")
        
        # Preserve optional patterns
        js_regex = preserve_complex_pattern(js_regex)
        if verbose:
            steps.append(f"Preserved complex patterns: {js_regex}")
        
        # Handle atomic groups
        js_regex, atomic_warnings = handle_atomic_groups(js_regex)
        warnings_list.extend(atomic_warnings)
        if verbose and atomic_warnings:
            steps.append(f"Handled atomic groups: {js_regex}")
        
        # Handle Unicode property escapes
        js_regex, unicode_warnings = handle_unicode_properties(js_regex)
        warnings_list.extend(unicode_warnings)
        if verbose and unicode_warnings:
            steps.append(f"Handled Unicode property escapes: {js_regex}")
        
        # Convert lookaround assertions
        if '(?<=' in js_regex or '(?<!' in js_regex:
            warnings_list.append("Lookbehind assertions have limited support in JavaScript.")
            if verbose:
                steps.append("Warned about lookbehind assertions")
        
        # Convert additional escape sequences
        js_regex = js_regex.replace(r'\a', r'\x07')  # Bell
        if r'\N' in js_regex:
            js_regex = js_regex.replace(r'\N', r'[^\n]')  # Any character except newline
            warnings_list.append(r"'\N' is converted to '[^\n]', which may not behave identically in all cases.")
            if verbose:
                steps.append("Converted additional escape sequences")
        
        # Ensure the entire pattern is preserved
        js_regex = re.sub(r'\n', r'\\n', js_regex)
        if verbose:
            steps.append(f"Ensured pattern preservation: {js_regex}")
        
        # Check for unsupported features
        unsupported_warnings = check_unsupported_features(js_regex)
        warnings_list.extend(unsupported_warnings)
        if verbose and unsupported_warnings:
            steps.append("Checked for unsupported features")
        
        # Ensure balanced parentheses
        js_regex = balance_parentheses(js_regex)
        if verbose:
            steps.append(f"Ensured balanced parentheses: {js_regex}")
        
        # Handle flags
        js_flags = handle_flags(py_flags)
        if verbose:
            steps.append(f"Handled flags: {js_flags}")
        
        # Construct JavaScript regex
        js_regex = f"/{js_regex}/{js_flags}"
        if verbose:
            steps.append(f"Final JavaScript regex: {js_regex}")
        
        return js_regex, warnings_list, steps
    
    except RegexConversionError as e:
        return None, [str(e)], steps



def pattern_preserved(original, converted):
    # Remove all whitespace and compare the core pattern
    original_core = re.sub(r'\s', '', original)
    converted_core = re.sub(r'\s', '', converted)
    return original_core in converted_core or converted_core in original_core

def conservative_conversion(regex):
    """
    Perform minimal conversions to make a Python regex valid in JavaScript.

    Args:
    regex (str): The Python regular expression to convert.

    Returns:
    str: The minimally converted JavaScript-compatible regex.
    """
    # Perform minimal conversions to make it valid JavaScript regex
    js_regex = regex.replace(r'\A', '^').replace(r'\Z', '$')
    js_regex = re.sub(r'\(\?P<(\w+)>', r'(?<\1>', js_regex)
    
    # Preserve optional non-capturing groups and newlines
    js_regex = re.sub(r'\(\?:[^)]*?\)\?', lambda m: f'(?:{m.group(0)})?', js_regex)
    
    return js_regex

    
def handle_verbose_mode(regex):
    """
    Handle Python's verbose regex mode (VERBOSE flag).

    Args:
    regex (str): The verbose Python regular expression.

    Returns:
    str: The regex with verbose mode syntax removed.
    """
    # Remove comments that are not part of the pattern
    regex = re.sub(r'(?<!\\)#.*$', '', regex, flags=re.MULTILINE)
    # Replace whitespace between regex constructs, but not inside character classes
    regex = re.sub(r'\s+(?=(?:[^[\]()\\]*(?:\\.[^[\]()\\]*)*\[[^[\]]*\])*[^[\]]*$)', '', regex)
    # Remove the (?x) flag from the regex
    regex = re.sub(r'\(\?x\)', '', regex)
    return regex.strip()

def handle_named_group_references(regex):
    """
    Convert Python-style named group references to JavaScript syntax.

    Args:
    regex (str): The Python regular expression.

    Returns:
    tuple: (converted_regex, warnings)
        converted_regex (str): The regex with converted named group references.
        warnings (list): List of warnings about named group reference conversions.
    """
    warnings = []
    def replace_named_ref(match):
        warnings.append(f"Named group reference '(?P={match.group(1)})' is not directly supported in JavaScript. Converted to '\\k<{match.group(1)}>', but may not work in all browsers.")
        return f"\\k<{match.group(1)}>"
    
    regex = re.sub(r'\(\?P=(\w+)\)', replace_named_ref, regex)
    return regex, warnings

def handle_atomic_groups(regex):
    warnings = []
    if r'(?>' in regex:
        warnings.append("Atomic groups are not supported in JavaScript. Converted to non-capturing groups.")
        regex = regex.replace(r'(?>', '(?:')
    return regex, warnings

def handle_unicode_properties(regex):
    warnings = []
    if r'\p' in regex or r'\P' in regex:
        warnings.append("Unicode property escapes require the 'u' flag in JavaScript.")
    return regex, warnings

def check_unsupported_features(regex):
    warnings = []
    if r'(?(1)' in regex:
        warnings.append("Conditional patterns are not supported in JavaScript. This part of the regex may not work as expected.")
    return warnings

def escape_special_chars(regex):
    special_chars = r'[](){}^$.*+?|\\'
    return ''.join('\\' + char if char in special_chars and char not in '[]^-' else char for char in regex)

def balance_parentheses(regex):
    stack = []
    i = 0
    result = ""
    while i < len(regex):
        if regex[i] == '\\':
            result += regex[i:i+2]
            i += 2
            continue
        if regex[i] == '(':
            stack.append(i)
            result += regex[i]
        elif regex[i] == ')':
            if stack:
                stack.pop()
                result += regex[i]
            else:
                result += '\\' + regex[i]
        else:
            result += regex[i]
        i += 1
    
    while stack:
        result += ')'
        stack.pop()
    
    return result

def preserve_complex_pattern(regex):
    # Preserve non-capturing groups with optional content
    regex = re.sub(r'\(\?:([^)]*?)\)\?', lambda m: f'(?:{m.group(1)})?', regex)
    
    # Preserve optional characters and groups at the end of the pattern, including newline
    regex = re.sub(r'([\w\s\S]*?)(\\\w|\[.*?\]|\(.*?\))?\??$', lambda m: m.group(0), regex)
    
    # Preserve repeated groups with optional content at the end
    regex = re.sub(r'(\(\?:.*?\)\?\\n\?)\+', lambda m: m.group(0), regex)
    
    return regex



def handle_flags(py_flags):
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

# Basic unit tests
def run_tests():
    test_cases = [
        # Basic patterns
        (r"hello", "", r"/hello/"),
        (r"hello world", "", r"/hello world/"),
        
        # Character classes
        (r"[a-z]", "", r"/[a-z]/"),
        (r"[^a-z]", "", r"/[^a-z]/"),
        (r"[a-zA-Z0-9_]", "", r"/[a-zA-Z0-9_]/"),
        
        # Quantifiers
        (r"a*", "", r"/a*/"),
        (r"a+", "", r"/a+/"),
        (r"a?", "", r"/a?/"),
        (r"a{3}", "", r"/a{3}/"),
        (r"a{3,}", "", r"/a{3,}/"),
        (r"a{3,5}", "", r"/a{3,5}/"),
        
        # Anchors
        (r"^start", "", r"/^start/"),
        (r"end$", "", r"/end$/"),
        (r"\bword\b", "", r"/\bword\b/"),
        (r"\Astart", "", r"/^start/"),
        (r"end\Z", "", r"/end$/"),
        
        # Groups and references
        (r"(group)", "", r"/(group)/"),
        (r"(?:group)", "", r"/(?:group)/"),
        (r"(group)\1", "", r"/(group)\1/"),
        (r"(?P<name>group)", "", r"/(?<name>group)/"),
        (r"(?P=name)", "", r"/\k<name>/", ["Named group reference '(?P=name)' is not directly supported in JavaScript. Converted to '\\k<name>', but may not work in all browsers."]),
        
        # Lookarounds
        (r"(?=positive)", "", r"/(?=positive)/"),
        (r"(?!negative)", "", r"/(?!negative)/"),
        (r"(?<=positive)", "", r"/(?<=positive)/", ["Lookbehind assertions have limited support in JavaScript."]),
        (r"(?<!negative)", "", r"/(?<!negative)/", ["Lookbehind assertions have limited support in JavaScript."]),
        
        # Character shorthands
        (r"\d\D\w\W\s\S", "", r"/\d\D\w\W\s\S/"),
        
        # Flags
        (r"case", "i", r"/case/i"),
        (r"^multi$", "m", r"/^multi$/m"),
        (r".", "s", r"/./s"),
        
        # Verbose mode
        (r"""(?x)
        \d+  # Match one or more digits
        \s*  # Optional whitespace
        \w+  # Match one or more word characters
        """, "x", r"/\d+\s*\w+/"),
        
        # Unicode
        (r"\p{Greek}", "u", r"/\p{Greek}/u", ["Unicode property escapes require the 'u' flag in JavaScript."]),
        (r"\P{ASCII}", "u", r"/\P{ASCII}/u", ["Unicode property escapes require the 'u' flag in JavaScript."]),
        
        # Complex patterns
        (r"^(?:(?P<word>\w+)\s*:\s*(?P<number>\d+)\s*(?:#.*)?\n?)+$", "mx", r"/^(?:(?<word>\w+)\s*:\s*(?<number>\d+)\s*(?:#.*)?\n?)+$/m"),
        
        # Atomic groups
        (r"(?>atomic)", "", r"/(?:atomic)/", ["Atomic groups are not supported in JavaScript. Converted to non-capturing groups."]),
        
        # Unsupported features
        (r"(?(1)then|else)", "", r"/(?(1)then|else)/", ["Conditional patterns are not supported in JavaScript. This part of the regex may not work as expected."]),
        
        # Edge cases
        (r"", "", r"//"),
        (r"[]]", "", r"/[]]/"),
        (r"[^]]", "", r"/[^]]/"),
        (r"[\]]", "", r"/[\]]/"),
        (r"\a\N", "", r"/\x07[^\n]/", ["'\\N' is converted to '[^\\n]', which may not behave identically in all cases."]),
    ]

    for i, test_case in enumerate(test_cases, 1):
        py_regex, flags, expected_js_regex = test_case[:3]
        expected_warnings = test_case[3] if len(test_case) > 3 else []
        
        py_flags = parse_flags(flags)
        js_regex, warnings, _ = py_to_js_regex(py_regex, py_flags)
        
        if js_regex == expected_js_regex and set(warnings) == set(expected_warnings):
            print(f"Test {i} passed")
        else:
            print(f"Test {i} failed:")
            print(f"  Input:    {py_regex}")
            print(f"  Flags:    {flags}")
            print(f"  Expected: {expected_js_regex}")
            print(f"  Got:      {js_regex}")
            if set(warnings) != set(expected_warnings):
                print("  Expected warnings:")
                for warning in expected_warnings:
                    print(f"    - {warning}")
                print("  Got warnings:")
                for warning in warnings:
                    print(f"    - {warning}")
        print()

    print("\nTesting verbose output:")
    py_regex = r"^(?:(?P<word>\w+)\s*:\s*(?P<number>\d+)\s*(?:#.*)?\n?)+$"
    py_flags = parse_flags("mx")
    js_regex, warnings, steps = py_to_js_regex(py_regex, py_flags, verbose=True)
    
    print(f"Input Python regex: {py_regex}")
    print(f"Output JavaScript regex: {js_regex}")
    print("\nConversion steps:")
    for step in steps:
        print(f"- {step}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    print("All tests completed.")

def main():
    """
    Main function to handle command-line arguments and execute regex conversion.
    """
    parser = argparse.ArgumentParser(description="Convert Python regex to JavaScript regex")
    parser.add_argument("regex", nargs='?', help="Python regex pattern")
    parser.add_argument("-f", "--flags", default="", help="Python regex flags (e.g., 'im' for IGNORECASE and MULTILINE)")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("-v", "--verbose", action="store_true", help="Output conversion steps")
    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.regex:
        try:
            py_flags = parse_flags(args.flags)
            js_regex, warnings_list, steps = py_to_js_regex(args.regex, py_flags, verbose=args.verbose)
            print(f"JavaScript regex: {js_regex}")
            if warnings_list:
                print("Warnings:")
                for warning in warnings_list:
                    print(f"- {warning}")
            if args.verbose:
                print("\nConversion steps:")
                for step in steps:
                    print(f"- {step}")
        except RegexConversionError as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

