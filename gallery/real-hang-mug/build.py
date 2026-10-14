#!/usr/bin/env python3
"""Offline dual-YAM red-cup camera adapter; imports only reviewed repository rendering code."""
import argparse, base64, importlib.util, json, math, sys, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
spec = importlib.util.spec_from_file_location('cube_replay', HERE.parent/'abc-yam-cube/build.py')
shared = importlib.util.module_from_spec(spec); spec.loader.exec_module(shared)
from render_video import Renderer, LEFT, W, H, BG, SANS, BOLD, MONO, MONO_BOLD, elapsed_label
from session_source import sha256
Timeline = shared.Timeline
utc = shared.utc
def load(root, edit):
    bundle = root
    log = next((bundle/'sessions').glob('2026*.jsonl'))
    checks = {f['path']:f['sha256'] for f in json.loads((bundle/'manifest.json').read_text())['files']}
    assert sha256(log) == checks[str(log.relative_to(bundle))]
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    results = {r['message']['toolCallId']:(i,r) for i,r in enumerate(rows) if r.get('message',{}).get('role')=='toolResult'}
    meta=[]; current=dict(model=None,effort=None)
    for r in rows:
        if r['type']=='model_change': current['model']=r['modelId']
        if r['type']=='thinking_level_change': current['effort']=r['thinkingLevel']
        m=r.get('message',{})
        if m.get('role')=='assistant':
            if m.get('model'): current['model']=m['model']
            if m.get('thinkingLevel'): current['effort']=m['thinkingLevel']
        meta.append(dict(current))
    image_dir=HERE/'.cache/view-images'; image_dir.mkdir(parents=True,exist_ok=True)
    inventory={}
    for i,r in enumerate(rows):
        images=[c for c in r.get('message',{}).get('content',[]) if isinstance(c,dict) and c.get('type')=='image']
        paths=sorted((bundle/'recorded-views').glob(f'*-line-{i+1}.png'))
        if images:
            assert len(paths)==len(images)
        for n,(c,p) in enumerate(zip(images,paths)):
            digest=sha256(p)
            assert digest==checks[str(p.relative_to(bundle))]
            import hashlib
            assert digest==hashlib.sha256(base64.b64decode(c['data'])).hexdigest()
            name=f'message-{i:04}-{n+1:02}.png'
            link=image_dir/name
            if not link.exists(): link.symlink_to(p.resolve())
            inventory['images/'+name]=dict(sha256=digest)
    return dict(root=HERE/'.cache', entries=rows, results=results, metadata=meta, inventory=inventory,
                recording={'clock':'external_camera'}, origin=utc(edit['clock']['camera_start_utc']),log=log)

def compile_events(source, edit, timeline):
    # The task is shown as opening context over frame zero, 4.18 s before its
    # original submission timestamp. Only this editorial display start changes.
    first=edit['events'][0]['entry'];original=source['entries'][first]
    rows=list(source['entries']);rows[first]=dict(original,timestamp=edit['clock']['camera_start_utc'])
    events=shared.compile_events(dict(source,entries=rows),edit,timeline)
    events[0].update(source_timestamp=original['timestamp'],
        source_call_s=utc(original['timestamp'])-source['origin'],
        opening_context=True,opening_context_note=edit['opening_context_note'])
    return events

class ReplayRenderer(shared.ReplayRenderer):
    def status(self,t):
        src=self.timeline.at(t)
        spec=self.edit['status_overlay'];seg=self.timeline.segment(t)
        if seg['speed']==seg['end_speed']==0:action=spec['hold_labels'][seg['reason']]
        else:action=next(x['text'] for x in spec['activity'] if x['start_source_s']<=src<=x['end_source_s'])
        return 'Autonomous',elapsed_label(src,self.timeline.last_source),action

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    edit=json.loads((HERE/'edit.json').read_text());root=REPO.parent/'sources/abc-yam-hang-mug-real'
    source=load(root,edit); timeline=Timeline(edit);events=compile_events(source,edit,timeline)
    renderer=ReplayRenderer(source,edit,events,timeline)
    for e in events:renderer.card(e)
    video=root/edit['recording'];fps=edit['clock']['fps']
    frame_index=lambda t:max(0,min(edit['clock']['frames']-1,math.floor(timeline.at(t)*fps+1e-7)))
    review=sorted(set(edit['review_times']+[0,edit['poster_time']]))
    times=review if args.preview else sorted(set(review+[i/30 for i in range(round(edit['duration']*30))]))
    crop=edit['recording_crop']['xywh']
    cache=HERE/('.cache/frames-crop-'+'-'.join(map(str,crop)))
    shared.extract_frames(video,[frame_index(t) for t in times],cache,fps,crop=crop)
    def frame(t): return renderer.frame(t,Image.open(cache/f'{frame_index(t):06}.png').convert('RGB'))
    sheet=Image.new('RGB',(1440,425*math.ceil(len(review)/2)),BG)
    for i,t in enumerate(review):
        f=frame(t);x=i%2*720;y=i//2*425;sheet.paste(f.resize((720,405)),(x,y))
        ImageDraw.Draw(sheet).text((x+8,y+406),f'{t:.2f}s / source {timeline.at(t):.2f}s',font=renderer.small,fill='#30362e')
        f.save(HERE/f'real-hang-mug.review-{t:06.2f}.jpg',quality=95)
    sheet.save(HERE/'real-hang-mug.contact.jpg',quality=92)
    frame(edit['poster_time']).save(HERE/'real-hang-mug.poster.jpg',quality=95)
    if not args.preview:
        master=REPO/'gallery/.masters/real-hang-mug.mp4'
        proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart',str(master)],stdin=subprocess.PIPE)
        try:
            for i in range(round(edit['duration']*30)):
                proc.stdin.write(frame(i/30).tobytes())
                if i%300==0: print(f'Rendered {i/30:.0f}/{edit["duration"]}s',flush=True)
            proc.stdin.close()
            if proc.wait():raise RuntimeError('Master encoding failed')
        finally:
            if proc.poll() is None:proc.terminate();proc.wait()
    prov=dict(schema='kinex/session-video/external-1',duration_s=edit['duration'],fps=30,dimensions=[W,H],
        source_session_sha256=sha256(source['log']),recording=video.name,recording_sha256=sha256(video),
        edit_sha256=sha256(HERE/'edit.json'),clock=edit['clock'],source_review=edit['source_review'],recording_crop=edit['recording_crop'],
        status_overlay=edit['status_overlay'],opening_context_note=edit['opening_context_note'],device_map=edit['device_map'],speed_segments=timeline.segments,events=events,
        output_source_frames=[frame_index(i/30) for i in range(round(edit['duration']*30))],
        fonts={p.name:sha256(p) for p in [SANS,BOLD,MONO,MONO_BOLD]},
        model=source['metadata'][events[0]['entry']]['model'],effort=source['metadata'][events[0]['entry']]['effort'],
        notes=['source_review.critical_moments speeds describe baseline editorial priorities; speed_segments records the final one-minute retiming.',
          'Public text and verbatim tool excerpts only; no hidden thinking or system prompts.',
          'Character streaming reconstructed; result/image appearance follows recorded result timestamps.',
          'Asynchronous write results acknowledge submission, not physical completion; motion guards cover commanded duration.',
          'Continuous original recording from frame zero through the verified hanging cup and public success report; later arm homing is omitted. Opening task displayed as context before its recorded submission; see opening_context_note.',
          'Failed first release, recovery, unsuccessful load transfer, right-arm camera repositioning, and final verified release are retained. Original audio untouched; delivery silent.',
          'Device map matches the session-returned YAM profiles and URDF dimensions; static illustration, not calibrated or live kinematics.',
          'No recorded robot-control code imported or executed; camera observations verified against archive hashes and embedded tool result data.'])
    (HERE/'real-hang-mug.provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n')
    print(f'Validated {len(events)} events, {edit["duration"]} seconds',flush=True)
if __name__=='__main__':main()
