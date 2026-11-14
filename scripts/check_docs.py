#!/usr/bin/env python3
"""Check maintained documentation without requiring generated run artifacts."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


def headings(text):
    ids, seen = set(), {}
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        title = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', title)
        base = re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')
        count = seen.get(base, 0)
        seen[base] = count + 1
        ids.add(base if not count else f'{base}-{count}')
    return ids


def main():
    errors = []
    markdown = sorted({
        ROOT / 'README.md', ROOT / 'LICENSE.md', ROOT / 'AGENTS.md', ROOT / 'CLAUDE.md', ROOT / 'benchmarks/README.md',
        *(ROOT / 'docs').rglob('*.md'), *(ROOT / '.agents/skills').rglob('*.md'),
        *(ROOT / '.claude/skills').rglob('*.md'),
    })
    links, anchors, shells = [], {}, 0
    for path in markdown:
        text = path.read_text()
        anchors[path.resolve()] = headings(re.sub(r'```.*?```', '', text, flags=re.S))
        if re.search(r'[\u0400-\u04ff]', text):
            errors.append(f'Current documentation must use English: {path.relative_to(ROOT)}')
        for block in re.findall(r'```bash\n(.*?)```', text, re.S):
            shells += 1
            result = subprocess.run(['bash', '-n'], input=block, text=True, capture_output=True)
            if result.returncode:
                errors.append(f'Shell syntax in {path.relative_to(ROOT)}: {result.stderr.strip()}')
        without_code = re.sub(r'```.*?```', '', text, flags=re.S)
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', without_code):
            links.append((path, target.strip('<>')))
    local_count = 0
    for source, target in links:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        local_count += 1
        path = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
        if not path.exists():
            errors.append(f'Broken link: {source.relative_to(ROOT)} -> {target}')
        elif parsed.fragment and path in anchors and unquote(parsed.fragment) not in anchors[path]:
            errors.append(f'Unknown anchor: {source.relative_to(ROOT)} -> {target}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f'Documentation passed: {len(markdown)} Markdown files, {local_count} local links, {shells} Bash blocks.')


if __name__ == '__main__':
    main()
