#!/usr/bin/env python3
"""Offline replay of the TeleAvatar transfer. Never executes recorded code."""
import argparse
import base64
import hashlib
import importlib.util
import json
import math
import subprocess
from itertools import groupby
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
NAME = 'teleavatar-tube-transfer'
SOURCE = HERE / '.cache/source/test-tube-transfer-2026-10-15'
RECORDING_ROOT = Path('/Users/mahaitong/Dropbox (Harvard University)/projects/kinex/demo6-dexteleop')
spec = importlib.util.spec_from_file_location('cube_replay', HERE.parent / 'abc-yam-cube/build.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
from render_video import LEFT, W, H, BG, SANS, BOLD, MONO, MONO_BOLD, elapsed_label
from session_source import sha256
from device_map import paste_device_map
Timeline, utc = shared.Timeline, shared.utc


def load(root, edit):
    checks = {}
    for line in (root / 'checksums.sha256').read_text().splitlines():
        digest, name = line.split(None, 1)
        checks[name.lstrip('*')] = digest
    log = root / 'session.jsonl'
    assert sha256(log) == checks['session.jsonl']
    manifest = json.loads((root / 'manifest.json').read_text())
    exported = {(r['record'] - 1, r['block']): r for r in manifest['images']}
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    results = {r['message']['toolCallId']: (i, r) for i, r in enumerate(rows)
               if r.get('message', {}).get('role') == 'toolResult'}
    meta, inventory = [], {}
    current = dict(model=None, effort=None)
    image_dir = HERE / '.cache/view-images'
    image_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(rows):
        if row['type'] == 'model_change':
            current['model'] = row['modelId']
        if row['type'] == 'thinking_level_change':
            current['effort'] = row['thinkingLevel']
        message = row.get('message', {})
        if message.get('role') == 'assistant':
            for field, key in [('model', 'model'), ('thinkingLevel', 'effort')]:
                if message.get(field): current[key] = message[field]
        meta.append(dict(current))
        number = 0
        for block, content in enumerate(message.get('content', [])):
            if not isinstance(content, dict) or content.get('type') != 'image': continue
            number += 1
            data = base64.b64decode(content['data'])
            digest = hashlib.sha256(data).hexdigest()
            record = exported[(i, block)]
            assert record['sha256'] == digest == sha256(root / record['path'])
            name = f'message-{i:04}-{number:02}.png'
            path = image_dir / name
            if not path.exists(): path.write_bytes(data)
            assert sha256(path) == digest
            inventory['images/' + name] = dict(sha256=digest, export_path=record['path'])
    return dict(root=HERE / '.cache', entries=rows, results=results, metadata=meta,
                inventory=inventory, recording={'clock': 'external_camera'},
                origin=utc(edit['clock']['camera_start_utc']), log=log)


def compile_events(source, edit, timeline):
    events = shared.compile_events(source, edit, timeline)
    for event in events:
        if event['kind'] != 'tool': continue
        result = source['entries'][event['result_entry']]
        raw = '\n'.join(c['text'] for c in result['message']['content'] if c['type'] == 'text')
        try: parsed = json.loads(raw)
        except ValueError: parsed = {}
        # exec reports process failure inside JSON, even when the MCP result succeeded.
        event['error'] = event['error'] or bool(parsed.get('exit_code', 0))
        assert event['source_result_s'] <= timeline.last_source
        event['active_devices'] = next(s.get('active_devices', []) for s in edit['events'] if s['entry'] == event['entry'])
    return events


class ReplayRenderer(shared.ReplayRenderer):
    def __init__(self, source, edit, events, timeline):
        super().__init__(source, edit, events, timeline)
        sizes = edit['status_overlay']['font_sizes']
        self.status_bold = ImageFont.truetype(BOLD, sizes['text'])
        self.status_mono = ImageFont.truetype(MONO, sizes['clock'])
        self.status_text = ImageFont.truetype(SANS, sizes['text'])
        # Filter only the annotation. The original timeline still drives every
        # recording frame, elapsed clock, and session event without alteration.
        minimum = math.ceil(edit['status_overlay']['speed_label_min_duration_s'] * 30)
        rounded = [round(timeline.speed_at(i / 30)) for i in range(round(edit['duration'] * 30))]
        self.speed_labels = []
        previous = rounded[0]
        for value, group in groupby(rounded):
            count = sum(1 for _ in group)
            if count >= minimum:
                previous = value
            self.speed_labels.extend([previous] * count)

    def displayed_speed(self, t):
        index = max(0, min(len(self.speed_labels) - 1, math.floor(t * 30 + 1e-7)))
        return self.speed_labels[index]

    def device_map(self, out, event):
        paste_device_map(self, out, event)

    def card(self, event, progress=1.0, t=0):
        return super().card(event, 1.0 if event['kind'] == 'user' else progress, t)

    def status(self, t):
        source = self.timeline.at(t)
        item = next(a for a in self.edit['status_overlay']['activity']
                    if a['start_source_s'] <= source <= a['end_source_s'])
        text = item['text']
        if self.timeline.segment(t)['reason'] == 'Final verification': text = 'Tube placed and released'
        autonomy = item.get('autonomy', 'Autonomous')
        if self.edit['status_overlay'].get('show_playback_speed'):
            autonomy += f' {self.displayed_speed(t)}×'
        return autonomy, elapsed_label(source, self.timeline.last_source), text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    edit = json.loads((HERE / 'edit.json').read_text())
    source = load(SOURCE, edit)
    timeline = Timeline(edit)
    events = compile_events(source, edit, timeline)
    renderer = ReplayRenderer(source, edit, events, timeline)
    for event in events: renderer.card(event)
    video = RECORDING_ROOT / edit['recording']
    fps = edit['clock']['fps']
    index = lambda t: max(0, min(edit['clock']['frames'] - 1, math.floor(timeline.at(t) * fps + 1e-7)))
    review = sorted(set(edit['review_times'] + [0, edit['poster_time']]))
    times = review if args.preview else sorted(set(review + [i / 30 for i in range(round(edit['duration'] * 30))]))
    cache = HERE / '.cache/frames'
    shared.extract_frames(video, [index(t) for t in times], cache, fps)

    def frame(t):
        return renderer.frame(t, Image.open(cache / f'{index(t):06}.png').convert('RGB'))

    sheet = Image.new('RGB', (1440, 425 * math.ceil(len(review) / 2)), BG)
    for i, t in enumerate(review):
        picture = frame(t)
        x, y = i % 2 * 720, i // 2 * 425
        sheet.paste(picture.resize((720, 405)), (x, y))
        ImageDraw.Draw(sheet).text((x + 8, y + 406), f'{t:.2f}s / source {timeline.at(t):.2f}s', font=renderer.small, fill='#30362e')
        picture.save(HERE / f'{NAME}.review-{t:06.2f}.jpg', quality=95)
    sheet.save(HERE / f'{NAME}.contact.jpg', quality=92)
    frame(edit['poster_time']).save(HERE / f'{NAME}.poster.jpg', quality=95)
    if not args.preview:
        master = REPO / f'gallery/.masters/{NAME}.mp4'
        master.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '1920x1080', '-r', '30', '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '19', '-pix_fmt', 'yuv420p', '-threads', '4', '-movflags', '+faststart', str(master)], stdin=subprocess.PIPE)
        try:
            for i in range(round(edit['duration'] * 30)):
                proc.stdin.write(frame(i / 30).tobytes())
                if i % 300 == 0: print(f'Rendered {i / 30:.0f}/{edit["duration"]}s', flush=True)
            proc.stdin.close()
            if proc.wait(): raise RuntimeError('Master encoding failed')
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait()
    provenance = dict(schema='kinex/session-video/external-1', duration_s=edit['duration'], fps=30, dimensions=[W, H],
        source_session_sha256=sha256(source['log']), recording=video.name, recording_sha256=sha256(video),
        edit_sha256=sha256(HERE / 'edit.json'), device_map_renderer_sha256=sha256(HERE / 'device_map.py'), clock=edit['clock'], source_review=edit['source_review'],
        pacing=edit['pacing'], status_overlay=edit['status_overlay'], device_map=edit['device_map'],
        speed_segments=timeline.segments, events=events,
        output_source_frames=[index(i / 30) for i in range(round(edit['duration'] * 30))],
        fonts={p.name: sha256(p) for p in [SANS, BOLD, MONO, MONO_BOLD]},
        robot='TeleAvatar', model='gpt-6-astra', effort='high',
        notes=['Public user text and verbatim tool excerpts only; no system prompts, hidden thinking, or recorded code executed.',
               'Character streaming reconstructed. Results and images first appear at their recorded completion time.',
               'Continuous source from frame zero. Original aspect ratio and full frame preserved; no synthesized frames.',
               'Original source and its audio unchanged; delivery is silent.',
               'Speed labels are rounded integers; changes shorter than 0.35 output seconds retain the previous stable label. Actual retiming is unchanged.',
               'Model from entry 1; high effort set in entry 3 before the task. Robot display name confirmed by user.',
               'Status label is fixed to Autonomous by user request. Visible tether handling and camera operator movement remain in footage and source-review records.',
               'Final state verified visually; no calibrated contact-force or seating-depth claim.'])
    provenance['source_frame_mapping_sha256'] = hashlib.sha256(json.dumps(provenance['output_source_frames']).encode()).hexdigest()
    (HERE / f'{NAME}.provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    print(f'Validated {len(events)} events, {edit["duration"]} seconds', flush=True)


if __name__ == '__main__': main()
