#!/usr/bin/env python3
"""Check the external clock adapter and final deliverables without a browser."""
import json
import math
from pathlib import Path
import subprocess

from build import HERE, REPO, Timeline, ReplayRenderer, load, compile_events


def main():
    edit = json.loads((HERE / 'edit.json').read_text())
    source = load(REPO.parent / 'sources/abc-yam-cube', edit)
    timeline = Timeline(edit)
    events = compile_events(source, edit, timeline)
    sampled = [timeline.at(i/30) for i in range(round(edit['duration']*30))]
    assert sampled[0] == 0
    assert all(a <= b for a, b in zip(sampled, sampled[1:]))
    assert math.isclose(sampled[-1], timeline.last_source)
    for s in timeline.segments:
        a, b = s['output_start_s'], s['output_end_s']
        mid = (a+b)/2
        epsilon = min(1e-5, (b-a)/4)
        derivative = (timeline.at(mid+epsilon)-timeline.at(mid-epsilon))/(2*epsilon)
        assert math.isclose(derivative, (s['speed']+s['end_speed'])/2, abs_tol=1e-5), s
        assert math.isclose(derivative, timeline.speed_at(mid), abs_tol=1e-5), s
        assert math.isclose(timeline.at(a), s['source_start_s'], abs_tol=1e-6)
        assert math.isclose(timeline.at(b), s['source_end_s'], abs_tol=1e-6)
    for previous, current in zip(timeline.segments, timeline.segments[1:]):
        assert math.isclose(previous['end_speed'], current['speed'], abs_tol=1e-6), (previous, current)
    for s in timeline.segments:
        if s['source_end_s'] > s['source_start_s']:
            for f in [.1,.5,.9]:
                t = s['output_start_s'] + f*(s['output_end_s']-s['output_start_s'])
                assert math.isclose(timeline.output(timeline.at(t)), t, abs_tol=1e-6)
    assert max(s['source_end_s'] for s in timeline.segments) < 3743
    assert max(e['entry'] for e in events) == 442
    for e in events:
        if e['kind'] != 'tool':
            continue
        completion = e['start']+e['duration']*e['result_fraction']
        assert timeline.at(completion) >= e['source_result_s']-1e-5, (e['entry'], 'premature result')
        assert e['typing_fraction'] < e['result_fraction']
    renderer = ReplayRenderer(source, edit, events, timeline)
    for i in range(round(edit['duration']*30)):
        autonomy, elapsed, action = renderer.status(i/30)
        assert autonomy == 'Autonomous' and action and '×' not in elapsed
        shown, total = elapsed.split(' / ')
        parse = lambda value: sum(int(n)*mult for n,mult in zip(value.split(':'), [3600,60,1]))
        assert parse(shown) == math.floor(timeline.at(i/30)+1e-7)
        assert parse(total) == math.floor(timeline.last_source+1e-7)
    assert renderer.status(0)[1] == '00:00:00 / 01:02:22'
    assert renderer.status(edit['duration']-1)[1:] == ('01:02:22 / 01:02:22', 'Solved — blue face up')
    master = REPO / 'gallery/.masters/abc-yam-cube.mp4'
    files = [master] + [REPO / f'public/kinex/media/gallery/abc-yam-cube/abc-yam-cube.{ext}' for ext in ['mp4','webm']]
    timestamps = []
    for path in files:
        probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
             '-count_frames','-show_entries','stream=width,height,nb_read_frames:format=duration',
             '-of','json',str(path)]))
        s = probe['streams'][0]
        assert (s['width'], s['height'], int(s['nb_read_frames'])) == (1920,1080,round(edit['duration']*30))
        assert abs(float(probe['format']['duration'])-edit['duration']) < .001
        data = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
             '-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
        pts = [float(f['best_effort_timestamp_time']) for f in data['frames']]
        assert len(pts) == round(edit['duration']*30)
        normalized = [t-pts[0] for t in pts]
        assert max(abs(t-i/30) for i,t in enumerate(normalized)) < .0011
        timestamps.append(dict(file=str(path.relative_to(REPO)),first_pts_s=pts[0],frames=len(pts)))
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
        print(f"Validated {path.name}: 1080p, {len(pts)} frames, {edit['duration']} seconds, full decode")
    (HERE / 'validation.json').write_text(json.dumps(dict(
        timeline='Continuous from source frame zero through solved blue-face-up presentation; every speed boundary, ramp derivative and inverse checked.',
        terminal='No selected tool result or camera image precedes its mapped source result timestamp.',
        status='Every frame displays Autonomous, real elapsed / retained source total in HH:MM:SS, and a short action. Displayed seconds match the recording clock; no speed multiplier appears.',
        files=timestamps,webm_timestamp_tolerance_s=.0011),indent=2)+'\n')

if __name__ == '__main__':
    main()
