#!/usr/bin/env python3
"""Offline JSONL/camera adapter for the bundled Kinex session-video renderer.

Never imports or executes anything from the recorded workspace. Run from the
repository root with a Python environment containing Pillow:
  python gallery/abc-yam-cube/build.py --preview
  python gallery/abc-yam-cube/build.py
"""
import argparse
import base64
import bisect
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SKILL = REPO / '.agents/skills/kinex-session-video/scripts'
sys.path.insert(0, str(SKILL))
from render_video import Renderer, LEFT, W, H, BG, SANS, BOLD, MONO, MONO_BOLD, field, elapsed_label
from session_source import run_metadata, result_text, sha256


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def load(root, edit):
    rows = [json.loads(line) for line in (root / 'session.jsonl').read_text().splitlines()]
    origin = utc(edit['clock']['camera_start_utc'])
    results = {r['message']['toolCallId']: (i, r) for i, r in enumerate(rows)
               if r.get('message', {}).get('role') == 'toolResult'}
    metadata = run_metadata({'entries': rows})
    inventory = {r['file']: r for r in json.loads((root / 'image-inventory.json').read_text())}
    image_dir = HERE / '.cache/view-images'
    image_dir.mkdir(parents=True, exist_ok=True)
    for r in inventory.values():
        path = root / r['file']
        if sha256(path) != r['sha256']:
            raise ValueError(f'Image inventory mismatch: {path}')
        link = image_dir / path.name
        if not link.exists():
            link.symlink_to(path)
    return dict(root=HERE / '.cache', entries=rows, results=results, metadata=metadata,
                original=root, inventory=inventory, recording={'clock': 'external_camera'},
                origin=origin)


class Timeline:
    """Integrated linear speed ramps shared by footage, tool state and images."""
    def __init__(self, edit):
        self.segments = []
        source = output = 0.0
        for spec in edit['retime']:
            end = spec['end_source_s']
            duration = spec.get('hold_s')
            if duration is not None:
                assert end == source and duration > 0
                speed = end_speed = 0.0
            else:
                speed = spec['speed']
                end_speed = spec.get('end_speed', speed)
                assert speed >= 0 and end_speed >= 0 and speed + end_speed > 0 and end > source
                duration = 2 * (end - source) / (speed + end_speed)
            self.segments.append(dict(source_start_s=source, source_end_s=end,
                                      output_start_s=output, output_end_s=output + duration,
                                      speed=speed, end_speed=end_speed, reason=spec['reason']))
            source, output = end, output + duration
        assert edit['from_start'] and edit['continuous_source']
        assert abs(output - edit['duration']) < 1e-6, output
        assert abs(source - edit.get('end_source_s', edit['clock']['last_frame_s'])) < 1e-6
        self.duration = output
        self.last_source = source

    def segment(self, t):
        return self.segments[min(len(self.segments)-1, bisect.bisect_right(
            [s['output_end_s'] for s in self.segments], max(0, t)))]

    def speed_at(self, t):
        s = self.segment(t)
        fraction = min(1, max(0, (t-s['output_start_s'])/(s['output_end_s']-s['output_start_s'])))
        return s['speed'] + fraction*(s['end_speed']-s['speed'])

    def at(self, t):
        s = self.segment(t)
        dt = max(0, min(t - s['output_start_s'], s['output_end_s'] - s['output_start_s']))
        acceleration = (s['end_speed'] - s['speed']) / (s['output_end_s'] - s['output_start_s'])
        return min(s['source_end_s'], s['source_start_s'] + dt*s['speed'] + .5*acceleration*dt*dt)

    def output(self, source):
        source = min(self.last_source, max(0, source))
        # A result becomes visible at the beginning of its evidence hold.
        for s in self.segments:
            if s['source_start_s'] <= source <= s['source_end_s']:
                distance = source - s['source_start_s']
                if distance == 0:
                    return s['output_start_s']
                acceleration = (s['end_speed'] - s['speed']) / (s['output_end_s'] - s['output_start_s'])
                # Stable quadratic inverse of the shared, integrated speed ramp.
                final_speed = math.sqrt(max(0, s['speed']**2 + 2*acceleration*distance))
                dt = 2*distance / (s['speed'] + final_speed)
                return s['output_start_s'] + dt
        raise ValueError(source)


def compile_events(source, edit, timeline):
    events = []
    rows = source['entries']
    for spec in edit['events']:
        index = spec['entry']
        row = rows[index]
        message = row['message']
        start_source = max(0, utc(row['timestamp']) - source['origin'])
        event = dict(spec, entry_id=row['id'], source_timestamp=row['timestamp'],
                     run_metadata=source['metadata'][index], images=[], error=False,
                     start=timeline.output(start_source), source_call_s=start_source)
        if spec.get('kind') in ['user', 'assistant']:
            assert message['role'] == spec['kind']
            text = result_text(row)
            body = spec.get('text', text)
            assert body in text
            event.update(title='you' if spec['kind']=='user' else 'Kinex', body=body,
                         result='', source_result_s=start_source)
        else:
            call = [c for c in message['content'] if c['type']=='toolCall'][spec.get('call', 0)]
            ri, result = source['results'][call['id']]
            raw = result_text(result)
            args = call['arguments']
            body = json.dumps(args, ensure_ascii=False)
            if 'code_field' in spec:
                code = field(args, spec['code_field'])
                body = spec['code_excerpt']
                assert body in code, (index, 'nonverbatim code')
            elif 'arg_fields' in spec:
                body = json.dumps({k: field(args,k) for k in spec['arg_fields']}, ensure_ascii=False)
            display = spec.get('result_text', '')
            assert display in raw
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = {}
            if 'result_fields' in spec:
                display = json.dumps({k: field(parsed,k) for k in spec['result_fields']}, ensure_ascii=False)
            error = bool(result['message'].get('isError')) or (isinstance(parsed,dict) and bool(parsed.get('error')))
            if error and not display:
                display = str(parsed.get('error',raw)).splitlines()[-1][:150] if isinstance(parsed,dict) else raw[-150:]
            images = [c for c in result['message']['content'] if c['type']=='image']
            for number in spec.get('images', [0] if images else []):
                name = f'images/message-{ri:04}-{number+1:02}.png'
                record = source['inventory'][name]
                digest = hashlib.sha256(base64.b64decode(images[number]['data'])).hexdigest()
                assert digest == record['sha256'], (ri, 'result/image association')
                event['images'].append(dict(filename=Path(name).name, sha256=digest,
                                            entry_index=ri, device_id=spec.get('image_label','Camera observation')))
            end_source = max(start_source, utc(result['timestamp']) - source['origin'])
            event.update(kind='tool', title=call['name'], body=body, result=display,
                         error=error, tool_call_id=call['id'], arguments=args,
                         result_entry=ri, result_entry_id=result['id'],
                         source_result_s=end_source,
                         result_at=timeline.output(end_source))
        events.append(event)
    assert events[0]['entry'] == next(i for i,r in enumerate(rows) if r.get('message',{}).get('role')=='user')
    assert events[0]['start'] == 0
    for i,e in enumerate(events):
        end = events[i+1]['start'] if i+1<len(events) else timeline.duration
        assert end > e['start'], (e['entry'], 'event ordering')
        e['end'], e['duration'] = end, end-e['start']
        result_at = e.get('result_at', e['start']+.5)
        assert result_at <= end, (e['entry'], 'result overlaps next selected call')
        e['result_fraction'] = min(.99, max(.001,(result_at-e['start'])/e['duration']))
        e['typing_fraction'] = min(e['result_fraction']*.8, .24/e['duration'])
        # The clock retains idle time between actual calls; it is never advanced
        # by the terminal's reconstructed character animation.
        e['sim_start'] = timeline.at(e['start'])
        e['sim_end'] = timeline.at(e['end'])
    return events


class ReplayRenderer(Renderer):
    def __init__(self, source, edit, events, timeline):
        self.timeline = timeline
        super().__init__(source, edit, events)

    def state(self, t):
        i = max(0,min(len(self.events)-1,bisect.bisect_right([e['start'] for e in self.events],t)-1))
        e = self.events[i]
        return i,e,min(1,max(0,(t-e['start'])/e['duration'])),self.timeline.at(t)


    def status(self, t):
        spec = self.edit['status_overlay']
        segment = self.timeline.segment(t)
        source = self.timeline.at(t)
        elapsed = elapsed_label(source, self.timeline.last_source)
        if segment['speed'] == segment['end_speed'] == 0:
            action = spec['hold_labels'][segment['reason']]
        else:
            action = next(item['text'] for item in spec['activity']
                          if item['start_source_s'] <= source <= item['end_source_s'])
        return spec['autonomy'], elapsed, action


def extract_frames(video, indices, cache, fps, crop=None):
    """Seek only to original frames; no interpolation or generated motion."""
    crop_filter = f'crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},' if crop else ''
    framing = crop_filter + f'scale={LEFT[2]}:{LEFT[3]}:force_original_aspect_ratio=decrease:flags=lanczos,pad={LEFT[2]}:{LEFT[3]}:(ow-iw)/2:(oh-ih)/2:color=0xf3f0e9'
    cache.mkdir(parents=True,exist_ok=True)
    missing = [i for i in sorted(set(indices)) if not (cache/f'{i:06}.png').exists()]
    # One decode pass; select before scaling avoids emitting the full 70-minute
    # recording as hundreds of gigabytes of intermediate RGB frames.
    if len(missing) < 40:
        for index in missing:
            # Seek halfway between the preceding frame and the requested frame;
            # accurate seeking then selects the requested original CFR frame.
            seek = max(0, (index-.5)/fps)
            subprocess.run(['ffmpeg','-v','error','-ss',str(seek),'-i',str(video),
                            '-frames:v','1','-vf',
                            framing,
                            '-threads','1','-y',str(cache/f'{index:06}.png')],check=True)
        return
    if missing:
        def balanced_sum(parts):
            if len(parts) == 1:
                return parts[0]
            mid = len(parts)//2
            return '(' + balanced_sum(parts[:mid]) + '+' + balanced_sum(parts[mid:]) + ')'
        expression = balanced_sum([f'eq(n\\,{i})' for i in missing])
        filt = f'select={expression},' + framing
        filter_file = cache/'select.txt'
        filter_file.write_text(filt)
        proc = subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-vf',filt,
                                 '-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-threads','2','-'],stdout=subprocess.PIPE)
        try:
            size = LEFT[2]*LEFT[3]*3
            for n,index in enumerate(missing):
                data = proc.stdout.read(size)
                if len(data)!=size: raise RuntimeError(f'Missing original frame {index}')
                Image.frombytes('RGB',LEFT[2:],data).save(cache/f'{index:06}.png')
                if n%150==0:print(f'Extracted {n+1}/{len(missing)} exact source frames',flush=True)
            if proc.wait()!=0:raise RuntimeError('Source decode failed')
        finally:
            if proc.poll() is None:proc.terminate();proc.communicate()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=REPO.parent/'sources/abc-yam-cube')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    edit=json.loads((HERE/'edit.json').read_text())
    source=load(args.source.resolve(),edit)
    timeline=Timeline(edit)
    events=compile_events(source,edit,timeline)
    renderer=ReplayRenderer(source,edit,events,timeline)
    for e in events:renderer.card(e)
    video=args.source.resolve()/edit['recording']
    fps=edit['clock']['fps']
    frame_index=lambda t:min(edit['clock']['frames']-1,max(0,math.floor(timeline.at(t)*fps+1e-7)))
    times=sorted(set(edit['review_times']+[edit['poster_time'],0]))
    if not args.preview:times=sorted(set(times+[i/30 for i in range(round(edit['duration']*30))]))
    cache=HERE/'.cache/frames'
    extract_frames(video,[frame_index(t) for t in times],cache,fps)
    def frame(t):return renderer.frame(t,Image.open(cache/f'{frame_index(t):06}.png').convert('RGB'))
    review=sorted(set(edit['review_times']+[edit['poster_time'],0]))
    sheet=Image.new('RGB',(1920,565*math.ceil(len(review)/2)),BG)
    for i,t in enumerate(review):
        f=frame(t);x=i%2*960;y=i//2*565
        sheet.paste(f.resize((960,540),Image.Resampling.LANCZOS),(x,y))
        ImageDraw.Draw(sheet).text((x+12,y+543),f'{t:.2f}s / source {timeline.at(t):.2f}s',font=renderer.small,fill='#30362e')
        f.save(HERE/f'abc-yam-cube.review-{t:05.2f}.jpg',quality=95)
    sheet.save(HERE/'abc-yam-cube.contact.jpg',quality=92)
    frame(edit['poster_time']).save(HERE/'abc-yam-cube.poster.jpg',quality=95)
    if not args.preview:
        master=REPO/'gallery/.masters/abc-yam-cube.mp4'
        master.parent.mkdir(exist_ok=True)
        proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
                               '-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                               '-threads','4','-movflags','+faststart',str(master)],stdin=subprocess.PIPE)
        try:
            for i in range(round(edit['duration']*30)):
                proc.stdin.write(frame(i/30).tobytes())
                if i%300==0:print(f'Rendered {i/30:.0f}/{edit["duration"]}s',flush=True)
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError('Encode failed')
        finally:
            if proc.poll() is None:proc.terminate();proc.wait()
    provenance=dict(schema='kinex/session-video/external-1',duration_s=edit['duration'],fps=30,dimensions=[W,H],
                    source_session='session.jsonl',source_session_sha256=sha256(args.source/'session.jsonl'),
                    recording=video.name,recording_sha256=sha256(video),edit_sha256=sha256(HERE/'edit.json'),
                    environment='Real world',clock=edit['clock'],source_review=edit['source_review'],
                    device_map=edit['device_map'],status_overlay=edit['status_overlay'],compact_metadata=edit.get('compact_metadata', False),speed_segments=timeline.segments,events=events,
                    output_source_frames=[frame_index(i/30) for i in range(round(edit['duration']*30))],
                    fonts={p.name:sha256(p) for p in [SANS,BOLD,MONO,MONO_BOLD]},
                    notes=['Edited session replay; source code is read only and never executed.',
                           'Public messages and verbatim tool excerpts only. Hidden thinking and system prompts excluded.',
                           'External camera alignment is approximate; see clock anchors and uncertainty.',
                           'Character streaming is reconstructed; tool completion and images use recorded result timestamps.',
                           'Continuous source time from frame zero to the reviewed solved blue-face-up presentation; later table placement omitted at user request. Speed ramps and explicit holds use original frames, without interpolated motion.',
                           'Only selected public calls are displayed; omitted calls retain their source-time intervals.',
                           'Images are matched to their tool result by toolCallId and decoded image SHA-256.',
                           'At user request, the lower-left status line shows Autonomous, real recording elapsed time / retained source total (HH:MM:SS), and a brief editorial action grounded in public commands. The total ends at the selected solved presentation. No speed multiplier is displayed.',
                           'Model and effort appear only in the title subtitle. Duplicate session metadata and the bottom-right export clock are omitted at user request.',
                           'Silent export. Original audio remains in the untouched source recording.'])
    (HERE/'abc-yam-cube.provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    print(f'Validated {len(events)} public events, {edit["duration"]}s, continuous source 0–{timeline.last_source:.3f}s',flush=True)

if __name__=='__main__':main()
