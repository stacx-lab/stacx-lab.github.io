"""Author a continuous edit from original calls, motion evidence and reviewed footage."""
import json
import re
import yaml
from build import HERE, SOURCE, load, utc, Timeline, sha256

edit = dict(title='Transferring a test tube', robot_label='TeleAvatar',
    subtitle='TeleAvatar × GPT-6-Astra · high · Real world', environment='Real world',
    recording='DJI_20261015033335_0035_D.MP4', from_start=True, continuous_source=True, end_source_s=1348,
    clock=dict(camera_start_utc='2026-10-15T07:33:37.000Z', fps=30000/1001, frames=40734,
        last_frame_s=40733*1001/30000, metadata_creation_utc='2026-10-15T07:33:35Z', uncertainty_s=.75,
        method='Constant offset from first arm approach and final withdrawal, reviewed in half-second source samples.',
        anchors=[dict(entry=67, event='First arm approach', source_window_s=[158,159],
                      plan_epoch_s=1792049775.499717138, inferred_source_s=158.499717138),
                 dict(entry=178, event='Final open-gripper withdrawal', source_window_s=[1335.5,1336.5],
                      plan_epoch_s=1792050953.121566290, inferred_source_s=1336.121566290)],
        note='Visual alignment is approximate, not subframe. Plan filenames are creation times, not servo start times; review windows include command/start uncertainty.'))
source = load(SOURCE, edit)
rows, origin = source['entries'], source['origin']

def public(row):
    return '\n'.join(c['text'] for c in row['message']['content'] if c['type']=='text')

def tool(index):
    call = next(c for c in rows[index]['message']['content'] if c['type']=='toolCall')
    ri, result = source['results'][call['id']]
    return call, ri, result

# User-requested visual abstraction. Preserve the recorded geometry as evidence,
# while the drawing follows the homepage illustration rather than metric scale.
profiles = {key: yaml.safe_load(public(rows[i])) for key, i in
            [('right_arm',17),('left_arm',18),('left_wrist_stereo',26),('right_wrist_stereo',27)]}
devices = [dict(id=name) for name in ['head_stereo','lift_velocity','base',
    'right_arm','left_arm','right_wrist_stereo','left_wrist_stereo','right_gripper','left_gripper']]
edit['device_map'] = dict(devices=devices, renderer='device_map.py',
    reference='src/components/DeviceDiagram.astro, adapted to the user-supplied robot abstraction',
    description='User-requested rounded robot abstraction with wheeled base, torso, articulated arms, camera lenses and grippers. Exact recorded device IDs are highlighted in purple. Illustrative topology, not calibrated geometry or live kinematics.',
    geometry_evidence={key:dict(extrinsics=p.get('extrinsics'),frames=p.get('intrinsics',{}).get('frames'),
                              chain=p.get('intrinsics',{}).get('model',{}).get('chain')) for key,p in profiles.items()},
    source_entries=[17,18,26,27])

selected = [5,32,39,63,65,67,72,78,82,84,86,88,92,96,100,108,110,116,118,126,128,136,140,144,148,152,156,162,166,170,174,176,178]
events = []
for i in selected:
    spec = dict(entry=i)
    if i==5:
        spec.update(kind='user', text=public(rows[i]))
        events.append(spec)
        continue
    call, ri, result = tool(i)
    args = call['arguments']
    raw = public(result)
    parsed = {}
    try: parsed = json.loads(raw)
    except ValueError: pass
    ids = [name for name in [d['id'] for d in devices] if re.search(r'\b'+name+r'\b', json.dumps(args))]
    # Camera defaults in the recorded motion helper, explicitly verified from returned paths.
    files = parsed.get('result',{}).get('file',[]) if isinstance(parsed.get('result'),dict) else []
    if isinstance(files,str): files=[files]
    for path in files:
        for name in ['head_stereo','right_wrist_stereo','left_wrist_stereo']:
            if '/'+name+'/' in path and name not in ids: ids.append(name)
    spec['active_devices'] = ids
    if call['name']=='exec': spec['arg_fields']=['description']
    if i in [128,136,156,162,174]: spec['arg_fields'] += ['args.delta','args.linear_speed']
    if i==32: spec['arg_fields']=['calls.0']
    if i==39:
        spec.update(code_field='python',code_excerpt="r=call('triangulate',camera='head_stereo',left_pixel=[493,643],right_pixel=[404,640]);print(r)")
    if i==65: spec['arg_fields']=['edits.0.newText'];spec['result_text']=raw.strip()
    if i in [63,100]:
        spec['result_text']='no motion submitted' if i==63 else 'IK discontinuity'
        assert spec['result_text'] in raw
    if call['name']=='device_stop': spec['arg_fields']=['deviceID','reason']
    images = [c for c in result['message']['content'] if c['type']=='image']
    if images:
        num = 0
        if i==67: num=2
        if i==178: num=4
        if i in [78,84,86] and len(images)>=4: num=2
        label = 'head_stereo'
        if files and num<len(files):
            label = next((s for s in ['left_wrist_stereo','right_wrist_stereo','head_stereo'] if s in files[num]),'Camera observation')
        if i==32: label='head_stereo'
        spec.update(images=[num],image_label=label+' · left eye')
    events.append(spec)
edit['events'] = events

# Protect every submitted arm plan using measured feedback clocks. World times
# are monotonic: the result sample pairs that clock to the epoch feedback clock.
windows = []
for path in sorted((SOURCE/'evidence').glob('tube-transfer-*.json')):
    if path.name.endswith('.result.json'): continue
    plan = json.loads(path.read_text())
    result_path = path.with_name(path.stem+'.result.json')
    if not plan.get('submission_attempted') or not result_path.exists(): continue
    result = json.loads(result_path.read_text())
    state = result['result']['state']
    sample = next(iter(state['samples'].values()))
    clock_offset = sample['timestamp'] - state['observed_world_s']
    start = plan['submitted_world_s'] + clock_offset - origin
    end = state['finished_observed_world_s'] + clock_offset - origin
    entry = next(i for i,r in enumerate(rows) if r.get('message',{}).get('role')=='toolResult' and path.name in public(r))
    call_entry = next(i for i,r in enumerate(rows) if any(c.get('type')=='toolCall' and c['id']==rows[entry]['message']['toolCallId'] for c in r.get('message',{}).get('content',[]) if isinstance(c,dict)))
    text = tool(call_entry)[0]['arguments'].get('description','Arm movement')
    speed = 7.0 if call_entry<126 else 4.5
    if call_entry in [78,84,86,178]: speed=4.0
    windows.append(dict(start_source_s=max(0,start-1),end_source_s=min(1348,end+1),speed=speed,
        entry=call_entry,text=text,kind='arm',plan=path.name,plan_sha256=sha256(path),
        result_sha256=sha256(result_path),timing='Epoch feedback minus observed monotonic world time; submission through observed completion, with 1 s guards.'))

# Base, lift and gripper-only commands lack saved arm-plan timelines. Protect
# their entire call/result windows, a conservative bound on physical motion.
for i in [45,78,80,84,88,90,92,96,108,112,116,122,176]:
    call, ri, result = tool(i)
    start, end = utc(rows[i]['timestamp'])-origin, utc(result['timestamp'])-origin
    text = call['arguments'].get('description','Opening the gripper')
    windows.append(dict(start_source_s=max(0,start-1),end_source_s=min(1348,end+1),speed=4 if i in [78,80,84,176] else 7,
                        entry=i,text=text,kind='other-command',timing='Complete call/result interval plus 1 s guards.'))

human = [(82,93),(151,159),(351,359),(397,406),(560,570)]
for a,b in human:
    windows.append(dict(start_source_s=a,end_source_s=b,speed=10,text='Operator clears the tether',kind='human'))
for a,b in [(0,6),(35,50),(435,450),(544,558),(600,628),(1178,1212)]:
    windows.append(dict(start_source_s=a,end_source_s=b,speed=10,text='Recording camera repositions',kind='camera'))
windows.sort(key=lambda w:w['start_source_s'])

holds = {0:(2,'Original task'),1348:(2.5,'Final verification')}
for i,seconds in [(32,.8),(63,.6),(67,.4),(84,.4),(86,.5),(140,.7),(148,.7),(152,.5),(178,.8)]:
    _,_,res=tool(i)
    holds[utc(res['timestamp'])-origin]=(seconds,'Inspect the evidence')

breaks=[(0,'Reading the task'),(17,'Inspecting the source rack'),(95,'Correcting the approach plan'),
        (157,'Approaching the tube'),(192,'Positioning the observation wrist'),(235,'Testing the first grasp'),
        (266,'Correcting fingertip reach'),(306,'Regrasping and lifting'),(357,'Finding the destination rack'),
        (425,'Approaching the counter'),(465,'Planning countertop clearance'),(505,'Raising the lift and arm'),
        (580,'Positioning the wrist camera'),(640,'Aligning with the empty hole'),(705,'Beginning slow insertion'),
        (845,'Inspecting the guide rim'),(900,'Checking possible resistance'),(1025,'Retracting and correcting'),
        (1090,'Inserting through the guides'),(1200,'Checking the lower guide'),(1314,'Releasing the tube'),
        (1335,'Withdrawing the open gripper'),(1346.367,'Tube placed and released')]
points={0,1348,*[a for a,_ in breaks]}
for a,b in human:points.update([a,b])
activity=[]
for a,b in zip(sorted(points),sorted(points)[1:]):
    mid=(a+b)/2
    assisted=any(x<=mid<=y for x,y in human)
    activity.append(dict(start_source_s=a,end_source_s=b,
        autonomy='Human assistance' if assisted else 'Autonomous',
        text='Operator clears the tether' if assisted else next(text for start,text in reversed(breaks) if start<=mid)))
edit['status_overlay']=dict(activity=activity,elapsed_time=dict(format='HH:MM:SS / HH:MM:SS',total_source_s=1348,clock='Original DJI recording'))

def make_plan(factor):
    bounds={0,1348,*holds}
    for w in windows:bounds.update([w['start_source_s'],w['end_source_s']])
    intervals=[]
    for a,b in zip(sorted(bounds),sorted(bounds)[1:]):
        matching=[w for w in windows if w['start_source_s']<=(a+b)/2<=w['end_source_s']]
        w=min(matching,key=lambda w:w['speed']) if matching else None
        intervals.append((a,b,w['speed']*factor if w else 180,w['text'] if w else 'Stationary planning'))
    plan=[dict(end_source_s=0,hold_s=holds[0][0],reason=holds[0][1])]
    for j,(a,b,speed,reason) in enumerate(intervals):
        before=0 if a in holds else min(intervals[j-1][2],speed) if j else 0
        after=0 if b in holds else min(intervals[j+1][2],speed) if j+1<len(intervals) else 0
        ramp=min(.5,(b-a)/3)
        plan += [dict(end_source_s=a+ramp,speed=before,end_speed=speed,reason=reason),
                 dict(end_source_s=b-ramp,speed=speed,end_speed=speed,reason=reason),
                 dict(end_source_s=b,speed=speed,end_speed=after,reason=reason)]
        if b in holds:plan.append(dict(end_source_s=b,hold_s=holds[b][0],reason=holds[b][1]))
    previous=total=0
    for s in plan:
        total+=s['hold_s'] if 'hold_s' in s else 2*(s['end_source_s']-previous)/(s['speed']+s['end_speed'])
        previous=s['end_source_s']
    return plan,total

target=75
low,high=.25,4
assert make_plan(low)[1]>target>make_plan(high)[1]
for _ in range(60):
    mid=(low+high)/2
    if make_plan(mid)[1]>target:low=mid
    else:high=mid
factor=(low+high)/2
plan,total=make_plan(factor)
plan[-1]['hold_s']+=target-total
for w in windows:w['speed']*=factor
edit.update(duration=target,retime=plan,pacing=dict(target_duration_s=target,motion_fit_factor=factor,stationary_speed=180,
    note='Every submitted arm plan and base/lift/gripper call protected. Insertion and release slowest. Camera repositioning and human tether handling retained. Smooth speed ramps; no source gaps.'),
    source_review=dict(critical_moments=windows,
        review='272 source frames at 5 s intervals across the full run; first arm approach and final withdrawal at 0.5 s intervals; initial/final external frames and selected inline observations.',
        endpoint='Tube upright and independently supported after open-gripper withdrawal. Final stereo evidence returned at source 1346.367 s; end at source 1348 s with 2.5 s hold.',
        framing='Original 16:9 full frame, letterboxed into the recording column. All camera movement is from original footage.',
        human_assistance=human,model_evidence='GPT-6-Astra from entry 1, high effort from entry 3 before the task; all assistant metadata checked.'))
timeline=Timeline(edit)
edit['poster_time']=timeline.output(utc(rows[33]['timestamp'])-origin)+.3
edit['review_times']=[0,edit['poster_time']]+[timeline.output(s) for s in [90,130,170,205,285,320,340,380,430,550,730,890,1030,1120,1208,1320,1348]]+[target-.1]
(HERE/'edit.json').write_text(json.dumps(edit,ensure_ascii=False,indent=2)+'\n')
print('Duration',target,'events',len(events),'protected windows',len(windows),'motion factor',factor)
