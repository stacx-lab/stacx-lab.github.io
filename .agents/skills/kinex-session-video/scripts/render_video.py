#!/usr/bin/env python3
"""Deterministic split-screen replay from an evidence-linked editorial timeline."""
import argparse
import bisect
import json
import math
from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont
from session_source import load_source, clocks, run_metadata, source_frame, sha256, result_text

W, H = 1920, 1080
LEFT = (40, 124, 1088, 816)
RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H = 1170, 124, 710, 832
BG, INK, MUTED = '#f3f0e9', '#30362e', '#7a7e76'
PENDING, DONE, ERROR = '#e1e6eb', '#deebe1', '#f3ded8'
FONT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
MONO = FONT_DIR / 'CommitMono-Regular.ttf'
MONO_BOLD = FONT_DIR / 'CommitMono-Bold.ttf'
SANS = FONT_DIR / 'Lato-Regular.ttf'
BOLD = FONT_DIR / 'Lato-Bold.ttf'


def compile_retime(event):
    """Create one monotonic clock map shared by video, tool state and speed label."""
    duration = event['duration']
    plan = event.get('retime')
    if plan:
        typing = plan['typing_s']
        hold = plan['result_hold_s']
        if typing <= 0 or hold <= 0 or typing + hold >= duration:
            raise ValueError('Retime needs positive typing/execution/result durations')
        cursor, source_t = typing, event['sim_start']
        knots = [{'at_s': typing, 'source_s': source_t}]
        segments = []
        for segment in plan['segments']:
            target = event['sim_end'] if segment['end_source_s'] == 'end' else segment['end_source_s']
            speed = segment['speed']
            if not math.isfinite(speed) or speed <= 0 or target <= source_t or target > event['sim_end'] + 1e-6:
                raise ValueError('Retime must advance source time with a positive finite speed')
            ramp = {}
            if 'start_speed' in segment or 'end_speed' in segment:
                v0, v1 = segment.get('start_speed'), segment.get('end_speed')
                if (v0 is None or v1 is None or not all(math.isfinite(v) and v >= 0 for v in (v0, v1))
                        or not math.isclose(speed, (v0 + v1) / 2, rel_tol=1e-9, abs_tol=1e-9)):
                    raise ValueError('Speed ramps require nonnegative endpoints and their positive mean speed')
                ramp = dict(start_speed=v0, end_speed=v1, interpolation='linear_speed')
            end = cursor + (target - source_t) / speed
            segments.append(dict(start_s=cursor, end_s=end, source_start_s=source_t,
                                 source_end_s=target, speed=speed, reason=segment['reason'], **ramp))
            knots.append(dict(at_s=end, source_s=target))
            cursor, source_t = end, target
        if abs(source_t - event['sim_end']) > 1e-6 or abs(cursor + hold - duration) > 1e-5:
            raise ValueError(f"Entry {event['entry']}: retime must cover the motion and fit its event duration")
        event['typing_fraction'], event['result_fraction'] = typing / duration, cursor / duration
    else:
        a, b = event.get('typing_fraction', .25), event.get('result_fraction', .76)
        if not 0 < a < b < 1:
            raise ValueError('Require 0 < typing_fraction < result_fraction < 1')
        knots = [dict(at_s=a * duration, source_s=event['sim_start']),
                 dict(at_s=b * duration, source_s=event['sim_end'])]
        segments = [dict(start_s=a * duration, end_s=b * duration,
                         source_start_s=event['sim_start'], source_end_s=event['sim_end'],
                         speed=(event['sim_end'] - event['sim_start']) / ((b-a) * duration),
                         reason='Recorded tool execution')]
    event['motion_keyframes'], event['speed_segments'] = knots, segments


def scene_clock(event, local_s):
    knots = event['motion_keyframes']
    if local_s < knots[0]['at_s']:
        return event['sim_start'], 0.0
    for segment in event['speed_segments']:
        if local_s < segment['end_s']:
            if segment.get('interpolation') == 'linear_speed':
                dt = local_s - segment['start_s']
                acceleration = (segment['end_speed'] - segment['start_speed']) / (segment['end_s'] - segment['start_s'])
                return (segment['source_start_s'] + segment['start_speed'] * dt + .5 * acceleration * dt * dt,
                        segment['start_speed'] + acceleration * dt)
            return segment['source_start_s'] + (local_s - segment['start_s']) * segment['speed'], segment['speed']
    return event['sim_end'], 0.0


def field(value, path):
    for key in path.split('.'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def wrap(text, width=61):
    return '\n'.join(part for line in text.split('\n') for part in
                     (textwrap.wrap(line, width, replace_whitespace=False, drop_whitespace=False) or ['']))


def compile_events(source, edit):
    events, elapsed, previous = [], 0.0, -1.0
    previous_entry = -1
    times = clocks(source)
    metadata = run_metadata(source)
    for spec in edit['events']:
        if spec['duration'] <= 0 or spec['entry'] < previous_entry:
            raise ValueError('Events must have positive durations and preserve session order')
        previous_entry = spec['entry']
        entry = source['entries'][spec['entry']]
        message = entry['message']
        event = dict(spec, start=elapsed, entry_id=entry['id'], source_timestamp=entry['timestamp'],
                     run_metadata=metadata[spec['entry']], images=[])
        elapsed += spec['duration']
        event['end'] = elapsed
        if spec.get('kind', 'tool') in ('user', 'assistant'):
            candidates = [c['text'] for c in message['content'] if c['type'] == 'text']
            assert message['role'] == spec['kind']
            body = '\n'.join(candidates).strip()
            if 'text' in spec:
                if spec['text'] not in body:
                    raise ValueError(f"Entry {spec['entry']}: text must be a verbatim excerpt")
                body = spec['text']
            event.update(kind=spec['kind'], title='you' if spec['kind'] == 'user' else 'Kinex', body=body, result='', error=False)
            sim_start = sim_end = times[spec['entry']][0]
        else:
            calls = [c for c in message['content'] if c['type'] == 'toolCall']
            call = calls[spec.get('call', 0)]
            result_index, result = source['results'][call['id']]
            args = call['arguments']
            body = json.dumps({k: v for k, v in args.items() if v is not None}, ensure_ascii=False)
            if 'code_field' in spec:
                code = field(args, spec['code_field'])
                lines = code.splitlines()
                body = '\n'.join(lines[n - 1] for n in spec['code_lines']) if 'code_lines' in spec else code
                if 'code_excerpt' in spec:
                    if spec['code_excerpt'] not in code:
                        raise ValueError('Code excerpt must occur verbatim in the source')
                    body = spec['code_excerpt']
            if 'arg_fields' in spec:
                body = json.dumps({k: field(args, k) for k in spec['arg_fields']}, ensure_ascii=False)
            # Long local paths are display-only shortened; full arguments stay in provenance.
            if call['name'] == 'read':
                body = Path(args['path']).name if args['path'].startswith('/tmp/') else args['path']
            raw = result_text(result)
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = None
            error = bool(result['message'].get('isError')) or raw.startswith('PyToolError:') or (isinstance(parsed, dict) and bool(parsed.get('error')))
            result_display = ''
            if 'result_fields' in spec:
                result_display = json.dumps({p: field(parsed, p) for p in spec['result_fields']}, ensure_ascii=False)
            elif 'result_text' in spec:
                if spec['result_text'] not in raw:
                    raise ValueError(f"Entry {spec['entry']}: result text is not in original output")
                result_display = spec['result_text']
            elif error:
                result_display = parsed.get('error', '') if isinstance(parsed, dict) else raw.splitlines()[-1][:120]
            records = source['images'].get(result_index, [])
            for record in records:
                path = source['root'] / 'view-images' / record['filename']
                if sha256(path) != record['sha256']:
                    raise ValueError(f'Image checksum mismatch: {path}')
            event.update(kind='tool', title=call['name'], body=body, result=result_display, error=bool(error),
                         tool_call_id=call['id'], arguments=args, result_entry=result_index,
                         result_entry_id=result['id'], images=records)
            sim_start, sim_end = times[spec['entry']][0], times[result_index][1]
            # Some consecutive calls have only a shared later clock observation.
            # Display them as a sequence instead of inventing a per-call boundary.
            if spec.get('following_calls'):
                if 'end_clock_entry' not in spec:
                    raise ValueError('A grouped sequence needs a measured end_clock_entry')
                event['grouped_calls'] = []
                for selected in spec['following_calls']:
                    index = selected['entry']
                    if index <= previous_entry or index >= spec['end_clock_entry']:
                        raise ValueError('Grouped calls must be ordered before their measured endpoint')
                    extra_entry = source['entries'][index]
                    extra = [c for c in extra_entry['message']['content'] if c['type'] == 'toolCall'][selected.get('call', 0)]
                    extra_index, extra_result = source['results'][extra['id']]
                    extra_raw = result_text(extra_result)
                    excerpt = selected.get('result_text', '')
                    if excerpt not in extra_raw:
                        raise ValueError('Grouped result must be a verbatim excerpt')
                    extra_body = json.dumps(extra['arguments'], ensure_ascii=False)
                    if 'code_field' in selected:
                        extra_code = field(extra['arguments'], selected['code_field'])
                        extra_body = selected.get('code_excerpt', extra_code)
                        if extra_body not in extra_code:
                            raise ValueError('Grouped code excerpt must occur verbatim in the source')
                    event['body'] += '\n' + extra['name'] + ' ' + extra_body
                    if excerpt:
                        event['result'] += '\n' + excerpt
                    event['error'] |= bool(extra_result['message'].get('isError')) or '"error"' in extra_raw or extra_raw.startswith('PyToolError:')
                    event['title'] += ' → ' + extra['name']
                    event['grouped_calls'].append(dict(entry=index, entry_id=extra_entry['id'], tool_call=extra,
                                                      result_entry=extra_index, result_entry_id=extra_result['id']))
                    previous_entry = index
                event['group_clock_note'] = 'Ordered call sequence with a shared measured endpoint; individual execution boundaries are unavailable.'
            # An error can lack a clock. A reviewed next observation is an explicit endpoint.
            if 'end_clock_entry' in spec:
                sim_end = times[spec['end_clock_entry']][1]
                event['clock_note'] = 'Endpoint from subsequent measured observation; in-call motion timing interpolated.'
        if 'start_clock_entry' in spec:
            sim_start = times[spec['start_clock_entry']][1]
            event['clock_note'] = 'Held at the explicitly selected measured scene-clock anchor.'
        event['sim_start'], event['sim_end'] = sim_start, sim_end
        compile_retime(event)
        if sim_start < previous - 1e-6 or sim_end < sim_start - 1e-6:
            raise ValueError(f"Nonmonotonic source time at entry {spec['entry']}")
        if sim_end > source['frames'][-1]['source_time_s'] + 0.11:
            raise ValueError('Event exceeds recording coverage')
        event['cut'] = sim_start - previous > 0.15 and previous >= 0
        previous = sim_end
        events.append(event)
    if abs(elapsed - edit['duration']) > 1e-6:
        raise ValueError(f'Event durations total {elapsed}, expected {edit["duration"]}')
    if edit.get('from_start'):
        first_user = next(i for i, e in enumerate(source['entries'])
                          if e.get('message', {}).get('role') == 'user')
        if (not events or events[0]['entry'] != first_user or events[0]['kind'] != 'user'
                or abs(events[0]['sim_start'] - source['frames'][0]['source_time_s']) > 1e-6):
            raise ValueError('From-start videos must open with the first user task at the first recorded frame')
    if edit.get('continuous_source') and any(abs(b['sim_start'] - a['sim_end']) > 1e-6
                                             for a, b in zip(events, events[1:])):
        raise ValueError('Continuous videos cannot omit source time between events')
    return events


class Renderer:
    def __init__(self, source, edit, events):
        self.source, self.edit, self.events = source, edit, events
        self.panel_y = 350 if edit.get('device_map') else RIGHT_Y
        self.panel_h = RIGHT_H - (self.panel_y - RIGHT_Y)
        self.font = ImageFont.truetype(MONO, 17)
        self.tool_font = ImageFont.truetype(MONO_BOLD, 17)
        self.body_font = ImageFont.truetype(SANS, 22)
        self.label_font = ImageFont.truetype(BOLD, 18)
        self.small = ImageFont.truetype(SANS, 17)
        self.title = ImageFont.truetype(SANS, 42)
        self.heading = ImageFont.truetype(BOLD, 26)
        self.complete_cards = {}
        self.images = {}
        for event in events:
            for record in event['images']:
                path = source['root'] / 'view-images' / record['filename']
                im = Image.open(path).convert('RGB')
                im.thumbnail((610, 348), Image.Resampling.LANCZOS)
                self.images[record['filename']] = im
        self.background = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(self.background)
        d.text((40, 28), edit['title'], font=self.title, fill=INK)
        d.text((42, 86), edit['subtitle'], font=self.body_font, fill=MUTED)
        d.text((RIGHT_X, 34), 'Kinex', font=self.heading, fill=INK)
        if not edit.get('device_map'):
            d.text((RIGHT_X, 84), 'Session replay · code, tools & observations', font=self.small, fill=MUTED)
        d.line((1148, 124, 1148, 1033), fill='#d6d6ce', width=1)
        d.line((40, 1046, 1880, 1046), fill='#d6d6ce', width=1)

    def card(self, event, progress=1.0, t=0):
        finished = progress >= 1
        cache_key = event['start']
        if finished and cache_key in self.complete_cards:
            return self.complete_cards[cache_key]
        is_tool = event['kind'] == 'tool'
        typed_at = event.get('typing_fraction', .25)
        result_at = event.get('result_fraction', .76)
        done = finished or progress >= result_at
        text = wrap(event['body'])
        if not finished:
            count = min(len(text), int(len(text) * progress / typed_at))
            text = text[:count]
        lines = text.split('\n')
        if len(lines) > 16:
            raise ValueError(f"Entry {event['entry']}: select a shorter code excerpt ({len(lines)} lines)")
        result = wrap(event['result']) if done else ''
        if result and not finished:
            n = int(len(result) * min(1, (progress - result_at) / max(.01, 1 - result_at)))
            result = result[:n]
        result_lines = result.split('\n') if result else []
        pics = event['images'] if done else []
        h = 50 + len(lines) * 24 + (len(result_lines) * 24 + 14 if result else 0)
        h += sum(self.images[r['filename']].height + 29 for r in pics)
        if h > self.panel_h:
            raise ValueError(f"Entry {event['entry']}: card exceeds the visible session panel; shorten the excerpt")
        bg = (ERROR if event['error'] else DONE) if done else PENDING
        if not is_tool:
            bg = '#eae7df' if event['kind'] == 'user' else '#faf8f3'
        im = Image.new('RGB', (RIGHT_W, h + 12), '#faf8f3')
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, RIGHT_W, h), fill=bg)
        title = event['title']
        d.text((17, 12), title, font=self.tool_font, fill=INK)
        if 'code_field' in event:
            x = 32 + d.textlength(title, font=self.tool_font)
            d.text((x, 14), 'code excerpt', font=self.small, fill=MUTED)
        if is_tool:
            status = 'error' if event['error'] and done else ('done' if done else 'running')
            d.text((RIGHT_W - 108, 14), status, font=self.small, fill=MUTED)
            if not done:
                angle = int(t * 360) % 360
                d.arc((RIGHT_W - 31, 17, RIGHT_W - 17, 31), angle, angle + 270, fill='#6b7f94', width=2)
            else:
                d.ellipse((RIGHT_W - 27, 20, RIGHT_W - 19, 28), fill='#a45d51' if event['error'] else '#5e8262')
        y = 42
        for line in lines:
            color = '#675797' if line.lstrip().startswith(('from ', 'import ', 'return ', 'def ')) else INK
            d.text((17, y), line, font=self.font, fill=color)
            y += 24
        if result:
            y += 10
            for line in result_lines:
                d.text((17, y), line, font=self.font, fill='#53664f' if not event['error'] else '#984c42')
                y += 24
        for record in pics:
            pic = self.images[record['filename']]
            clock = record.get('capture_timestamp_s')
            label = record.get('device_id') or 'image'
            if clock is not None:
                label += f' · {clock:.2f} s'
            d.text((17, y + 2), label, font=self.small, fill=MUTED)
            y += 27
            im.paste(pic, (17, y))
            y += pic.height + 2
        if finished:
            self.complete_cards[cache_key] = im
        return im

    def device_map(self, out, event):
        """Draw the source-specific setup supplied by the reviewed edit."""
        config = self.edit.get('device_map')
        if not config:
            return
        d = ImageDraw.Draw(out)
        active = set(event.get('active_devices', []))
        ox, oy = RIGHT_X, 80
        def points(values):
            return [(ox + x, oy + y) for x, y in values]
        for shape in config['shapes']:
            color = '#557f88' if shape.get('device') in active else '#b4b7af'
            p = points(shape['points'])
            if shape['kind'] == 'line':
                d.line(p, fill=color, width=shape.get('width', 3), joint='curve')
            elif shape['kind'] == 'polygon':
                d.polygon(p, fill='#e8e8df', outline=color, width=2)
            elif shape['kind'] == 'joint':
                x, y = p[0]
                radius = shape.get('radius', 7)
                d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=BG, outline=color, width=3)
        for device in config['devices']:
            color = '#416e78' if device['id'] in active else '#92978d'
            fill = '#dce9e7' if device['id'] in active else '#eeede6'
            x, y = device['label']
            width = d.textlength(device['id'], font=self.small) + 20
            anchor = points([device['anchor']])[0]
            edge = ox+x+width if x < 200 else ox+x
            if device.get('leader', True):
                d.line([anchor, (edge, oy+y+14)], fill=color, width=2)
            d.rounded_rectangle((ox+x, oy+y, ox+x+width, oy+y+29), radius=6, fill=fill)
            d.text((ox+x+10, oy+y+5), device['id'], font=self.small, fill=color)

    def state(self, t):
        index = min(len(self.events) - 1, bisect.bisect_right([e['start'] for e in self.events], t) - 1)
        event = self.events[index]
        progress = min(1, max(0, (t - event['start']) / event['duration']))
        sim, _ = scene_clock(event, progress * event['duration'])
        return index, event, progress, sim

    def frame(self, t, recording):
        index, event, progress, sim = self.state(t)
        out = self.background.copy()
        out.paste(recording, LEFT[:2])
        self.device_map(out, event)
        d = ImageDraw.Draw(out)
        metadata = event['run_metadata']
        model = metadata['model'] or 'not recorded'
        effort = metadata['effort'] or 'not recorded'
        d.text((RIGHT_X + 115, 42), f'Model: {model} · Effort: {effort}', font=self.small, fill=MUTED)
        cards = [self.card(e) for e in self.events[max(0, index - 5):index]]
        cards.append(self.card(event, progress, t))
        content_h = sum(card.height for card in cards)
        content = Image.new('RGB', (RIGHT_W, max(self.panel_h, content_h)), '#faf8f3')
        y = 0
        for card in cards:
            content.paste(card, (0, y)); y += card.height
        # Track the newest content; nothing is blanked between calls.
        offset = max(0, content_h - self.panel_h)
        out.paste(content.crop((0, offset, RIGHT_W, offset + self.panel_h)), (RIGHT_X, self.panel_y))
        d.line((RIGHT_X, 982, RIGHT_X + RIGHT_W, 982), fill='#a3b0c7', width=2)
        d.text((RIGHT_X + 7, 991), '›', font=self.body_font, fill=INK)
        d.text((RIGHT_X + 31, 996), 'Kinex session', font=self.small, fill=MUTED)
        environment = 'Simulator' if self.source['recording']['clock'] == 'simulation' else self.edit.get('environment', 'not recorded')
        d.text((RIGHT_X, 1024), f'{model} · {effort} effort · {environment}', font=self.small, fill=MUTED)
        clock = f'{t:04.1f} / {self.edit["duration"]:.0f} s'
        if self.edit.get('show_playback_speed'):
            _, speed = scene_clock(event, progress * event['duration'])
            speed_label = (f'{speed:.1f}×' if speed >= .1 else f'{speed:.2f}×') if speed > 1e-6 else 'Frame held'
            clock = f'{speed_label}  ·  {clock}'
        d.text((1880 - d.textlength(clock, font=self.small), 1053), clock, font=self.small, fill=MUTED)
        return out


class VideoReader:
    def __init__(self, path):
        self.proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(path), '-vf',
                                      f'scale={LEFT[2]}:{LEFT[3]}:force_original_aspect_ratio=decrease:flags=lanczos,pad={LEFT[2]}:{LEFT[3]}:(ow-iw)/2:(oh-ih)/2:color=0xf3f0e9', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '2', '-'], stdout=subprocess.PIPE)
        self.index = -1
        self.image = None

    def frame(self, index):
        if index < self.index:
            raise ValueError('Recording would seek backwards')
        count = LEFT[2] * LEFT[3] * 3
        while self.index < index:
            data = self.proc.stdout.read(count)
            if len(data) != count:
                raise ValueError(f'Recording ended before frame {index}')
            self.image = Image.frombytes('RGB', LEFT[2:], data)
            self.index += 1
        return self.image

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        # Drain any buffered frames while FFmpeg finishes its trailer, avoiding
        # an expected early stop being reported as a broken output pipe.
        self.proc.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('edit', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--preview', action='store_true', help='Render a contact sheet only')
    args = parser.parse_args()
    source = load_source(args.source)
    edit = json.loads(args.edit.read_text())
    events = compile_events(source, edit)
    renderer = Renderer(source, edit, events)
    for event in events:
        renderer.card(event)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    video = source['root'] / edit.get('recording', 'third_person.mp4')
    reader = VideoReader(video)
    poster_time = edit.get('poster_time', 0)
    if not 0 <= poster_time < edit['duration']:
        raise ValueError('Poster time must be inside the video')
    sample_times = sorted(set(edit.get('review_times', [i * edit['duration'] / 10 for i in range(10)]) + [poster_time]))
    samples = []
    encoder = None
    try:
        if args.preview:
            for t in sample_times:
                sim = renderer.state(t)[3]
                frame = renderer.frame(t, reader.frame(source_frame(source, sim)))
                samples.append((t, frame))
        else:
            encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                        '-s', f'{W}x{H}', '-r', str(args.fps), '-i', '-', '-an', '-c:v', 'libx264',
                                        '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-threads', '4',
                                        '-movflags', '+faststart', str(args.output)], stdin=subprocess.PIPE)
            sample_indices = {round(t * args.fps): t for t in sample_times}
            for index in range(round(edit['duration'] * args.fps)):
                t = index / args.fps
                sim = renderer.state(t)[3]
                frame = renderer.frame(t, reader.frame(source_frame(source, sim)))
                encoder.stdin.write(frame.tobytes())
                if index in sample_indices:
                    samples.append((t, frame.copy()))
                if index % (args.fps * 5) == 0:
                    print(f'Rendered {t:.0f}/{edit["duration"]:.0f}s', flush=True)
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError('Video encoder failed')
    finally:
        reader.close()
        if encoder and encoder.poll() is None:
            encoder.terminate(); encoder.wait()
    sheet = Image.new('RGB', (960 * 2, 565 * math.ceil(len(samples) / 2)), BG)
    for i, (t, frame) in enumerate(samples):
        im = frame.resize((960, 540), Image.Resampling.LANCZOS)
        x, y = (i % 2) * 960, (i // 2) * 565
        sheet.paste(im, (x, y))
        ImageDraw.Draw(sheet).text((x + 12, y + 542), f'{t:.1f}s', font=renderer.small, fill=INK)
    sheet.save(args.output.with_suffix('.contact.jpg'), quality=92)
    if samples:
        min(samples, key=lambda sample: abs(sample[0] - poster_time))[1].save(args.output.with_suffix('.poster.jpg'), quality=95)
    provenance = dict(schema='kinex/session-video/1', source_session=source['export'].name,
                      source_session_sha256=sha256(source['export']), recording=video.name, recording_sha256=sha256(video),
                      frames_sha256=sha256(source['root'] / 'frames.jsonl'), edit_sha256=sha256(args.edit),
                      duration_s=edit['duration'], fps=args.fps, dimensions=[W, H], source_clock=source['recording']['clock'],
                      fonts={p.name: sha256(p) for p in [SANS, BOLD, MONO, MONO_BOLD]},
                      notes=['Edited replay, not a live connection. Original public text and tool code excerpts; omitted calls are not replayed.',
                             'Character streaming is reconstructed: the export does not contain token arrival times.',
                             'Video frames mapped through frames.jsonl; explicit piecewise speed maps interpolate measured scene-clock endpoints.',
                             'Provenance speeds are source-clock seconds per output second, not agent wall-clock acceleration; zero denotes a held frame.',
                             'Scene clock holds while code streams. At explicit cuts, both panels jump to the same recorded stage.',
                             'Embedded camera images are checksum-verified source bytes, scaled only for layout.',
                             'No source code was executed and no robot or simulator was controlled.'], events=events)
    provenance['device_map'] = edit.get('device_map')
    provenance['source_review'] = edit.get('source_review')
    provenance['environment'] = 'Simulator' if source['recording']['clock'] == 'simulation' else edit.get('environment', 'not recorded')
    args.output.with_suffix('.provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2))
    print(f'Validated {len(events)} events; duration {edit["duration"]}s', flush=True)


if __name__ == '__main__':
    main()
