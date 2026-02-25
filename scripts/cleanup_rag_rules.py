import json
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / 'instance' / 'rag_db' / 'rules.json'

TRUNCATE_LEN = 50


def truncate_val(s: str) -> str:
    s = str(s)
    if len(s) > TRUNCATE_LEN:
        return s[:TRUNCATE_LEN-3] + '...'
    return s


def process_content(content: str) -> str:
    lines = content.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Normalize sample header
        if line.strip().lower().startswith('sample values'):
            # change header to indicate up to 1 each
            out.append('Sample Values (per column, up to 1 each):')
            i += 1
            # process sample lines until blank or Example Rows or Note
            while i < n:
                l = lines[i]
                if not l.strip():
                    # blank line -> finished sample section
                    out.append('')
                    i += 1
                    break
                if l.strip().lower().startswith('example rows') or l.strip().lower().startswith('note:'):
                    # don't append example rows; break to let outer loop handle Note
                    break
                # process sample line e.g. '- col: val1, val2'
                if l.strip().startswith('-') and ':' in l:
                    try:
                        left, right = l.split(':', 1)
                        col = left.strip().lstrip('-').strip()
                        vals = right.strip()
                        # take first value before comma
                        first = vals.split(',', 1)[0].strip()
                        first = truncate_val(first)
                        out.append(f"- {col}: {first}")
                    except Exception:
                        # fallback: keep original truncated
                        out.append(truncate_val(l))
                else:
                    out.append(l)
                i += 1
            # continue without increment (we already positioned i)
            continue
        # Skip any Example Rows blocks entirely
        if line.strip().lower().startswith('example rows'):
            # skip until blank line or Note
            i += 1
            while i < n:
                l = lines[i]
                if not l.strip() or l.strip().lower().startswith('note:'):
                    break
                i += 1
            # do not append the Example Rows header or its lines
            continue
        # Replace note about truncation to 50 chars
        if line.strip().lower().startswith('note:'):
            out.append('Note: Auto-captured sample values (values truncated to 50 chars)')
            i += 1
            continue
        # default: copy line
        out.append(line)
        i += 1

    return '\n'.join(out)


def main():
    if not RULES_PATH.exists():
        print(f"Rules file not found: {RULES_PATH}")
        return
    try:
        data = json.loads(RULES_PATH.read_text())
    except Exception as e:
        print(f"Failed to read rules.json: {e}")
        return

    changed = False
    for item in data:
        content = item.get('content', '')
        new_content = process_content(content)
        if new_content != content:
            item['content'] = new_content
            changed = True

    if changed:
        RULES_PATH.write_text(json.dumps(data, indent=2))
        print(f"Updated rules file: {RULES_PATH}")
    else:
        print("No changes needed")


if __name__ == '__main__':
    main()
