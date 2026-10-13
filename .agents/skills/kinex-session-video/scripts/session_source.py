"""Read a pi export as data, never execute its HTML or recorded tool code."""
import base64
import bisect
import hashlib
import json
import re
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_source(root):
    root = Path(root).resolve()
    exports = list(root.glob('pi-session-*.html'))
    if len(exports) != 1:
        raise ValueError('Expected one pi-session HTML export in the source directory')
    match = re.search(r'<script\b[^>]*\bid=[\"\']session-data[\"\'][^>]*>(.*?)</script>', exports[0].read_text(), re.S)
    if not match:
        raise ValueError('Missing base64 session-data element')
    session = json.loads(base64.b64decode(match.group(1)))
    entries = session['entries']
    results = {e['message']['toolCallId']: (i, e) for i, e in enumerate(entries)
               if e.get('message', {}).get('role') == 'toolResult'}
    image_manifest = json.loads((root / 'view-images/manifest.json').read_text())
    if image_manifest.get('source_session_sha256') != sha256(exports[0]):
        raise ValueError('Image manifest belongs to a different session export')
    images = {}
    for record in image_manifest['images']:
        images.setdefault(record['entry_index'], []).append(record)
    recording = json.loads((root / 'manifest.json').read_text())
    frames = [json.loads(line) for line in (root / 'frames.jsonl').read_text().splitlines() if line.strip()]
    if not frames or any(b['source_time_s'] < a['source_time_s'] for a, b in zip(frames, frames[1:])):
        raise ValueError('Frame source times must be monotonic')
    return dict(root=root, export=exports[0], entries=entries, results=results, images=images,
                recording=recording, frames=frames, session_id=session['header'].get('id'))


def result_text(entry):
    return '\n'.join(c['text'] for c in entry.get('message', {}).get('content', []) if c.get('type') == 'text')


def measured_times(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('timestamp', 'time_s') and isinstance(child, (int, float)) and 0 <= child < 1e7:
                found.append(float(child))
            else:
                found.extend(measured_times(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(measured_times(child))
    return found


def clocks(source):
    current = 0.0
    out = []
    for entry in source['entries']:
        before = current
        if entry.get('message', {}).get('role') == 'toolResult':
            try:
                found = measured_times(json.loads(result_text(entry)))
                current = max([current] + found)
            except (ValueError, TypeError):
                pass
        out.append((before, current))
    return out


def run_metadata(source):
    """Resolve the recorded model/effort at each entry, including setup changes."""
    current = dict(model=None, effort=None)
    out = []
    for entry in source['entries']:
        if entry.get('type') == 'model_change':
            current['model'] = entry.get('modelId')
        elif entry.get('type') == 'thinking_level_change':
            current['effort'] = entry.get('thinkingLevel')
        message = entry.get('message', {})
        if message.get('role') == 'assistant':
            for key, recorded in [('model', 'model'), ('effort', 'thinkingLevel')]:
                if message.get(recorded) is not None:
                    current[key] = message[recorded]
        out.append(dict(current))
    return out


def source_frame(source, time_s):
    rows = source['frames']
    index = max(0, bisect.bisect_right([r['source_time_s'] for r in rows], time_s + 1e-7) - 1)
    return rows[index]['frame_start']


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Inspect public messages, tools, images and measured scene clocks; omit system and thinking blocks.')
    parser.add_argument('source')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = load_source(args.source)
    timing = clocks(source)
    rows = []
    for i, entry in enumerate(source['entries']):
        message = entry.get('message', {})
        if message.get('role') not in ('user', 'assistant'):
            continue
        for c in message.get('content', []):
            if c.get('type') == 'toolCall':
                result_index, result = source['results'][c['id']]
                rows.append(dict(entry=i, entry_id=entry['id'], timestamp=entry['timestamp'],
                                 tool=c['name'], arguments=c['arguments'], result_entry=result_index,
                                 result=result_text(result), sim_before=timing[i][0], sim_after=timing[result_index][1],
                                 images=source['images'].get(result_index, [])))
            elif c.get('type') == 'text':
                rows.append(dict(entry=i, role=message['role'], text=c['text'], sim_time=timing[i][0]))
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f'{len(rows)} public messages/tool calls -> {args.output}')
