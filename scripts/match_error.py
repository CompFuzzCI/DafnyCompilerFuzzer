import re
import sys
import hashlib

# Regex patterns
JavaErrorPatterns = [r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n', r'error: .*\n', r'Exception in thread \"main\" java\.lang\..+\n', r'Caused by: java\.lang\..+\n', r'System.NotImplementedException: The method or operation is not implemented.',r'\[Program halted\] .*\n']
CSErrorPatterns = [r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n', r'error CS\d{4}: .+\n',r'System.NotImplementedException: The method or operation is not implemented.',r'\[Program halted\] .*\n']
RustErrorPatterns = [r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n', r'error\[E\d{4}\]',r'System.NotImplementedException: The method or operation is not implemented.',r'\[Program halted\] .*\n']
PythonErrorPatterns = [ r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n',
    r'SyntaxError: .+\n', r'NameError: .+\n', r'TypeError: .+\n', r'IndexError: .+\n', 
    r'ValueError: .+\n', r'KeyError: .+\n', r'AttributeError: .+\n', r'IndentationError: .+\n', 
    r'ImportError: .+\n', r'IOError: .+\n', r'AssertionError: .+\n', r'EOFError: .+\n', 
    r'FloatingPointError: .+\n', r'GeneratorExit: .+\n', r'MemoryError: .+\n', 
    r'NotImplementedError: .+\n', r'OSError: .+\n', r'OverflowError: .+\n', 
    r'ReferenceError: .+\n', r'RuntimeError: .+\n', r'StopIteration: .+\n', 
    r'TabError: .+\n', r'SystemError: .+\n', r'SystemExit: .+\n', r'UnboundLocalError: .+\n', 
    r'UnicodeError: .+\n', r'UnicodeEncodeError: .+\n', r'UnicodeDecodeError: .+\n', 
    r'UnicodeTranslateError: .+\n',r'System.NotImplementedException: The method or operation is not implemented.',
    r'\[Program halted\] .*\n'
]
JavaScriptErrorPatterns = [ r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n',
    r'SyntaxError: .+\n', r'TypeError: .+\n', r'RangeError: .+\n', r'ReferenceError: .+\n', 
    r'URIError: .+\n', r'EvalError: .+\n', r'InternalError: .+\n', r'AggregateError: .+\n',r'System.NotImplementedException: The method or operation is not implemented.',
    r'\[Program halted\] .*\n'
]
GoErrorPatterns = [ r'Error: .*\n', r'Process terminated\. .*\n', r'Unhandled exception\. .+\n', r'Unhandled exception: .+\n',r'System.NotImplementedException: The method or operation is not implemented.', r'.*:\d+:\d+: .*\n', r'\[Program halted\] .*\n', r'fatal error: .*\n']

# Map language identifiers to their respective regex patterns
error_patterns = {
    'rs': RustErrorPatterns,
    'cs': CSErrorPatterns,
    'js': JavaScriptErrorPatterns,
    'py': PythonErrorPatterns,
    'java': JavaErrorPatterns,
    'go': GoErrorPatterns
}

def match_error(fuzzd_log):
    result = {
        'miscompilation': False,
        'rs': set(),
        'cs': set(),
        'js': set(),
        'py': set(),
        'java': set(),
        'go': set(),
        'dafny': set()
    }
    try:
        with open(fuzzd_log, 'r') as log_file:
            log_content = log_file.read()

            # Define the delimiters
            delimiters = r'--------------------------------- COMPILE FAILED -------------------------------|' \
                         r'--------------------------------- EXECUTE FAILED -------------------------------|' \
                         r'--------------------------------- EXECUTE SUCCEEDED -------------------------------'
            
            # Split the log_content by the specified delimiters
            sections = re.split(delimiters, log_content)

            # Check compilation failure  
            if sections[1]:
                # Split the section by the language identifier
                split_content = re.split(r'(rs|cs|js|py|java|go):\n', sections[1])
                for lang, content in zip(split_content[1::2], split_content[2::2]):
                    patterns = error_patterns.get(lang, [])
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            match = match.rstrip('\n')
                            match = re.sub(r"'[^']*'", '', match)
                            match = re.sub(r'"[^"]*"', '', match)
                            if lang == 'go' and pattern == GoErrorPatterns[4]:
                                match = match.split(':')[3:]
                                match[0] = match[0].lstrip()
                                match = ':'.join(match)
                                match = match.split('at')[0]
                            result[lang].add(match)
                
            # Check execution failure
            if sections[2]:
                # Split the section by the language identifier
                split_content = re.split(r'(rs|cs|js|py|java|go):\n', sections[2])
                for lang, content in zip(split_content[1::2], split_content[2::2]):
                    patterns = error_patterns.get(lang, [])
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            match = match.rstrip('\n')
                            match = re.sub(r"'[^']*'", '', match)
                            match = re.sub(r'"[^"]*"', '', match)
                            if lang == 'go' and pattern == GoErrorPatterns[5]:
                                match = match.split(':')[3:]
                                match[0] = match[0].lstrip()
                                match = ':'.join(match)
                                match = match.split('at')[0]
                            result[lang].add(match)
                            
            if "Different output: true" in log_content:
                result['miscompilation'] = True
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    

    common_errors = set(result['cs']).intersection(result['js'], result['py'], result['java'], result['go'])
    if common_errors:
        result['dafny'] = list(common_errors)
        for lang in ['rs', 'cs', 'js', 'py', 'java', 'go']:
            result[lang] = {error for error in result[lang] if error not in common_errors}

    return result

if __name__ == "__main__":
    all_lang_output = match_error(sys.argv[1])
    lang = sys.argv[2]
    if lang != "miscompilation":
        sorted_bug = sorted(all_lang_output[lang])
        concatenated_bug = ''.join(sorted_bug)
        hashed_bug = hashlib.md5(concatenated_bug.encode()).hexdigest()
        print(hashed_bug)
    else:
        print(all_lang_output['miscompilation'])