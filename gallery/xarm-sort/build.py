#!/usr/bin/env python3
"""Offline xArm JSONL/camera adapter. Never executes recorded task code."""
import argparse, base64, importlib.util, json, math, subprocess, hashlib
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
    log=root/'session.jsonl'
    checks={f['path']:f['sha256'] for f in json.loads((root/'manifest.json').read_text())['files']}
    assert sha256(log)==checks['session.jsonl']
    rows=[json.loads(line) for line in log.read_text().splitlines()]
    results={r['message']['toolCallId']:(i,r) for i,r in enumerate(rows) if r.get('message',{}).get('role')=='toolResult'}
    meta=[]; current=dict(model=None,effort=None)
    image_dir=HERE/'.cache/view-images';image_dir.mkdir(parents=True,exist_ok=True);inventory={}
    for i,r in enumerate(rows):
        if r['type']=='model_change':current['model']=r['modelId']
        if r['type']=='thinking_level_change':current['effort']=r['thinkingLevel']
        m=r.get('message',{})
        if m.get('role')=='assistant':
            if m.get('model'):current['model']=m['model']
            if m.get('thinkingLevel'):current['effort']=m['thinkingLevel']
        meta.append(dict(current))
        images=[c for c in m.get('content',[]) if c.get('type')=='image']
        for n,c in enumerate(images):
            data=base64.b64decode(c['data']);digest=hashlib.sha256(data).hexdigest()
            name=f'message-{i:04}-{n+1:02}.png';path=image_dir/name
            if not path.exists():path.write_bytes(data)
            assert sha256(path)==digest
            inventory['images/'+name]=dict(sha256=digest)
    return dict(root=HERE/'.cache',entries=rows,results=results,metadata=meta,inventory=inventory,
                recording={'clock':'external_camera'},origin=utc(edit['clock']['camera_start_utc']),log=log)

def compile_events(source,edit,timeline):
    events=shared.compile_events(source,edit,timeline)
    for e in events:
        a=e.get('arguments',{});ids=[]
        if e['title']=='device':ids=[a['deviceID']]
        elif e['title']=='exec':
            code=a.get('python','');file=a.get('file','')
            if file.endswith('move_stage.py'):
                ids=['xarm','third_person_camera']
                if any('grip' in s for s in a['args']['steps']):ids.append('gripper')
            elif 'wrist' in code or 'wrist' in file:ids=['wrist_camera','xarm']
            elif 'third_person_camera' in code:ids=['third_person_camera']
            else:ids=['host']
        elif e['title']=='device_stop':ids=['xarm','gripper']
        elif e['kind']=='tool':ids=['host']
        e['active_devices']=ids
    return events

class ReplayRenderer(shared.ReplayRenderer):
    def card(self,event,progress=1.0,t=0):
        return super().card(event,1.0 if event["kind"]=="user" else progress,t)
    def status(self,t):
        src=self.timeline.at(t)
        item=next(x for x in self.edit['status_overlay']['activity'] if x['start_source_s']<=src<=x['end_source_s'])
        action=item['text']
        if self.timeline.segment(t)['reason']=='Final verification':action='Five objects sorted'
        return item.get('autonomy','Autonomous'),elapsed_label(src,self.timeline.last_source),action

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    edit=json.loads((HERE/'edit.json').read_text());root=REPO.parent/'sources/xarm-sort'
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
        f.save(HERE/f'xarm-sort.review-{t:06.2f}.jpg',quality=95)
    sheet.save(HERE/'xarm-sort.contact.jpg',quality=92)
    frame(edit['poster_time']).save(HERE/'xarm-sort.poster.jpg',quality=95)
    if not args.preview:
        master=REPO/'gallery/.masters/xarm-sort.mp4'
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
        edit_sha256=sha256(HERE/'edit.json'),clock=edit['clock'],source_review=edit['source_review'],
        recording_crop=edit['recording_crop'],pacing=edit['pacing'],
        status_overlay=edit['status_overlay'],device_map=edit['device_map'],speed_segments=timeline.segments,events=events,
        output_source_frames=[frame_index(i/30) for i in range(round(edit['duration']*30))],
        fonts={p.name:sha256(p) for p in [SANS,BOLD,MONO,MONO_BOLD]},
        model='gpt-6-astra',effort='medium',
        notes=['Public text and verbatim tool excerpts only; no hidden thinking, system prompts, or recorded scripts executed.',
          'Character streaming reconstructed. Tool results and embedded observations appear at recorded completion times.',
          'Camera alignment inferred from first arm approach and final retreat, uncertainty 0.6 s; metadata creation time differs by about 2 s.',
          'Continuous source from frame zero through five visibly sorted objects and final camera result. Original audio untouched; all outputs silent.',
          'Opening user instruction predates recording by 4.075 s. Execution model GPT-6-Astra medium, changed before the repeated task and all tool calls; initial inactive configuration was GPT-5.5.',
          'Operator confirmations during setup are labeled. Subsequent sorting is autonomous.',
          'Device diagram uses factory link dimensions and recorded camera mounts; illustrative fixed pose, not calibrated or live kinematics.'])
    prov['source_frame_mapping_sha256']=hashlib.sha256(json.dumps(prov['output_source_frames']).encode()).hexdigest()
    (HERE/'xarm-sort.provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n')
    print(f'Validated {len(events)} events, {edit["duration"]} seconds',flush=True)
if __name__=='__main__':main()
