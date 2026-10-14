#!/usr/bin/env python3
"""Offline Go2 camera adapter; imports only reviewed repository rendering code."""
import argparse, base64, importlib.util, json, math, sys, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
spec = importlib.util.spec_from_file_location('cube_replay', HERE.parent/'abc-yam-cube/build.py')
shared = importlib.util.module_from_spec(spec); spec.loader.exec_module(shared)
from render_video import Renderer, LEFT, W, H, BG, SANS, BOLD, MONO, MONO_BOLD, elapsed_label
from session_source import sha256
import go2_d1
Timeline = shared.Timeline
utc = shared.utc
COLORS = dict(base='#3F7FD0', arm='#756EE4', gripper='#E8612C', d405='#1E9AA6', d435='#1E9AA6', host='#7A746A')

def load(root, edit):
    bundle = root / edit['bundle']
    log = next((bundle/'session').glob('2026*.jsonl'))
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
        paths=sorted((bundle/'images/embedded').glob(f'line-{i+1:04d}-*.png'))
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
    events=shared.compile_events(source,edit,timeline)
    for ev in events:
        args=ev.get('arguments',{}); title=ev['title']
        if title=='device': ids=[args.get('deviceID')] if args.get('deviceID') else ['arm','base']
        elif title=='devices': ids=[c['deviceID'] for c in args['calls']]
        elif title=='servo': ids=[args['device']]
        elif title=='device_stop': ids=[args['deviceID']] if args.get('deviceID') else ['arm','base']
        elif title=='read' and '/devices/' in args.get('path',''): ids=[args['path'].split('/devices/')[1].split('/')[0]]
        elif title=='relative_pose': ids=['arm']
        elif ev['kind']=='tool': ids=['host']
        else: ids=[]
        ev['devices']=ids
    return events

class ReplayRenderer(shared.ReplayRenderer):
    def __init__(self,*args):
        self.robots={}
        super().__init__(*args)
    def device_map(self,out,event):
        active=frozenset(event['devices'])
        if active not in self.robots: self.robots[active]=go2_d1.render((340,205),280,active,COLORS,'#CFC8BA',BG)
        rob,anchors=self.robots[active]; rx,ry=1170,126
        out.paste(rob,(rx,ry),rob); d=ImageDraw.Draw(out)
        d.text((1170,85),'Device map · Go2 + D1',font=self.small,fill='#7a7e76')
        for n,(dev,name) in enumerate([('base','base · Go2'),('arm','arm · D1'),('gripper','gripper'),('d405','d405 · wrist'),('d435','d435 · head'),('host','host compute')]):
            x,y=1630,132+n*32; on=dev in active; color=COLORS[dev] if on else '#CFC8BA'
            d.rounded_rectangle((x,y,1870,y+27),radius=8,fill=color if on else None,outline=color)
            d.text((x+12,y+3),name,font=self.small,fill='white' if on else '#7a7e76')
            if on and dev in anchors:
                ax,ay=anchors[dev];d.line([(x,y+13),(rx+ax+8,y+13),(rx+ax,ry+ay)],fill=color,width=1)
    def status(self,t):
        src=self.timeline.at(t)
        item=next(x for x in self.edit['status_overlay']['activity'] if x['start_source_s']<=src<=x['end_source_s'])
        action=item['text']
        if self.timeline.segment(t)['reason']=='Final verification': action='Two pieces in the bin'
        return item.get('autonomy','Autonomous'),elapsed_label(src,self.timeline.last_source),action

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    edit=json.loads((HERE/'edit.json').read_text());root=REPO.parent/'sources/go2-trash-clean'
    source=load(root,edit); timeline=Timeline(edit);events=compile_events(source,edit,timeline)
    renderer=ReplayRenderer(source,edit,events,timeline)
    for e in events:renderer.card(e)
    video=root/edit['recording'];fps=edit['clock']['fps']
    frame_index=lambda t:max(0,min(edit['clock']['frames']-1,math.floor(timeline.at(t)*fps+1e-7)))
    review=sorted(set(edit['review_times']+[0,edit['poster_time']]))
    times=review if args.preview else sorted(set(review+[i/30 for i in range(round(edit['duration']*30))]))
    cache=HERE/'.cache/frames'; shared.extract_frames(video,[frame_index(t) for t in times],cache,fps)
    def frame(t): return renderer.frame(t,Image.open(cache/f'{frame_index(t):06}.png').convert('RGB'))
    sheet=Image.new('RGB',(1440,425*math.ceil(len(review)/2)),BG)
    for i,t in enumerate(review):
        f=frame(t);x=i%2*720;y=i//2*425;sheet.paste(f.resize((720,405)),(x,y))
        ImageDraw.Draw(sheet).text((x+8,y+406),f'{t:.2f}s / source {timeline.at(t):.2f}s',font=renderer.small,fill='#30362e')
        f.save(HERE/f'go2-trash-clean.review-{t:06.2f}.jpg',quality=95)
    sheet.save(HERE/'go2-trash-clean.contact.jpg',quality=92)
    frame(edit['poster_time']).save(HERE/'go2-trash-clean.poster.jpg',quality=95)
    if not args.preview:
        master=REPO/'gallery/.masters/go2-trash-clean.mp4'
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
        status_overlay=edit['status_overlay'],device_map=edit['device_map'],speed_segments=timeline.segments,events=events,
        output_source_frames=[frame_index(i/30) for i in range(round(edit['duration']*30))],
        fonts={p.name:sha256(p) for p in [SANS,BOLD,MONO,MONO_BOLD]},
        model=source['metadata'][events[0]['entry']]['model'],effort=source['metadata'][events[0]['entry']]['effort'],
        notes=['Public text and verbatim tool excerpts only; no hidden thinking or system prompts.',
          'Character streaming reconstructed; result/image appearance follows recorded result timestamps.',
          'Asynchronous write results acknowledge submission, not physical completion; motion guards cover commanded duration.',
          'Continuous original recording from frame zero to second deposit verification, followed by a final hold. Later searching and user-requested crouch omitted; this is not a claim all trash was cleared.',
          'Human broom disturbance and operator inspection explicitly labeled. Original audio untouched; delivery silent.',
          'Device map is a static illustration based on supplied URDF/profile dimensions, not calibrated or live kinematics.',
          'No recorded robot-control code imported or executed; camera observations verified against archive hashes and embedded tool result data.'])
    (HERE/'go2-trash-clean.provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n')
    print(f'Validated {len(events)} events, {edit["duration"]} seconds',flush=True)
if __name__=='__main__':main()
