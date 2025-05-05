"""Helper functions for the textual chat UI."""


def pretty_incomplete_json(s: str, indent=2):
    """
    Format a possibly incomplete JSON string with proper indentation.
    
    This function works even with partial or broken JSON, making it useful
    for streaming JSON responses.
    
    Args:
        s: The JSON string to prettify
        indent: The number of spaces to use for indentation
        
    Returns:
        A prettified version of the JSON string
    """
    out, level, in_str, esc = [], 0, False, False
    for c in s:
        if esc:
            out.append(c)
            esc = False
        elif c == '\\':
            out.append(c)
            esc = True
        elif c == '"':
            out.append(c)
            in_str = not in_str
        elif not in_str:
            if c in '{[':
                out += [c, '\n', ' ' * (indent * (level := level + 1))]
            elif c in '}]':
                level = max(0, level - 1)
                out += ['\n', ' ' * (indent * level), c]
            elif c == ',':
                out += [c, '\n', ' ' * (indent * level)]
            elif c == ':':
                out += [': ']
            else:
                out.append(c)
        else:
            out.append(c)

    return ''.join(out)