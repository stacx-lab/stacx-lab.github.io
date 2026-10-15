"""Author an evidence-linked continuous edit from saved stage timestamps."""
import json, math
from pathlib import Path
from build import HERE, REPO, load, utc, Timeline
root=REPO.parent/'sources/xarm-sort'
edit=dict(title='Sorting objects by color',subtitle='xArm 7 × GPT-6-Astra · medium · Real world',environment='Real world',
 recording='DJI_20261015021430_0034_D.MP4',from_start=True,continuous_source=True,end_source_s=1079,
 clock=dict(camera_start_utc='2026-10-15T06:14:33.000Z',fps=30000/1001,frames=34400,last_frame_s=34399*1001/30000,
 uncertainty_s=.6,method='Constant offset inferred from arm motion at beginning and end, compared with recorded command/stage timestamps.',
 anchors=[dict(event='First approach begins',entry=89,source_window_s=[319.5,320.5],session_utc='2026-10-15T06:19:52.703Z'),
          dict(event='Final withdrawal begins',stage='065-final-retreat',source_window_s=[1073.5,1074.5],session_utc='2026-10-15T06:32:26.830Z')],
 metadata_creation_utc='2026-10-15T06:14:31Z',note='Creation metadata is 2 s earlier than inferred source origin. Visual anchors support constant offset; synchronization is not subframe precision.'))
edit['recording_crop']=dict(xywh=[96,0,1728,1080],original_dimensions=[1920,1080],note='User-requested mild side crop: 96 px (5%) from each side; full vertical frame retained, with no stretching. Checked left-basket approach, gripper extremes, and final arrangement.')
source=load(root,edit); rows=source['entries'];origin=source['origin']
# Dimensioned schematic: shoulder height .264 m, upper arm .294 m, forearm .351 m;
# flange-to-grasp-center .200 m, wrist camera mounted at [.059,-.011,.035] m.
pts=[(85,232),(85,172),(87,165),(126,107),(135,105),(205,140),(224,150)]
shapes=[dict(kind='line',device='xarm',points=pts,width=17)]
shapes += [dict(kind='joint',device='xarm',points=[p],radius=8) for p in pts]
shapes += [dict(kind='polygon',device='xarm',points=[(59,232),(111,232),(119,242),(51,242)]),
 dict(kind='polygon',device='gripper',points=[(213,153),(236,153),(236,178),(213,178)]),
 dict(kind='line',device='gripper',points=[(214,176),(213,199),(219,199)],width=4),
 dict(kind='line',device='gripper',points=[(235,176),(237,199),(231,199)],width=4),
 dict(kind='polygon',device='wrist_camera',points=[(241,143),(263,143),(263,155),(241,155)]),
 dict(kind='polygon',device='third_person_camera',points=[(305,58),(341,58),(341,75),(305,75)]),
 dict(kind='line',device='third_person_camera',points=[(323,75),(323,115)],width=3)]
edit['device_map']=dict(description='Seven-joint fixed schematic using factory geometry from session entry 80 and camera/gripper mounts from entries 16, 17, 94. Not live or calibrated kinematics.',
 dimensions_m=dict(shoulder=.264,upper_arm=.294,forearm=.351,gripper_tcp=.2),shapes=shapes,
 devices=[dict(id=n,label=label,anchor=anchor,leader=True) for n,label,anchor in [
 ('xarm',(8,18),(126,107)),('gripper',(370,180),(225,184)),('wrist_camera',(370,135),(252,149)),
 ('third_person_camera',(370,62),(323,66)),('host',(370,18),(350,30))]])
windows=[]
for p in sorted((root/'task-images/color-sort').glob('*-state.json')):
 r=json.loads(p.read_text());end=r['timestamp']-origin;duration=r.get('result',{}).get('duration_s',2)
 label=p.name.split('-state')[0];n=int(label[:3]);speed=12
 if any(s in label for s in ['grasp','deeper','closed','close','release']):speed=4.2
 if n in [6,12,22,40,61]:speed=5
 text='Positioning the arm'
 if 'yellow' in label:text='Retrying the corn grasp' if n>=8 and n<=12 else 'Sorting the corn'
 if 'cube' in label:text='Recovering the red cube' if n>=37 else 'First red cube attempt'
 if 'blue' in label:text='Blue figure to left basket'
 if 'pineapple' in label:text='Pineapple to right basket'
 if 'multicolor' in label:text='Multicolor to left basket'
 if n==65:text='Verifying the final placement'
 windows.append(dict(start_source_s=max(0,end-duration-.7),end_source_s=min(edit['end_source_s'],end+.7),speed=speed,text=text,stage=label,state_file_sha256=__import__('hashlib').sha256(p.read_bytes()).hexdigest()))
windows += [dict(start_source_s=152.7,end_source_s=156.5,speed=5,text='Opening the gripper',stage='initial-open'),
 dict(start_source_s=515.2,end_source_s=522.2,speed=1.5,text='Cube slips from the grasp',stage='visually-reviewed-slip')]
windows.sort(key=lambda w:w['start_source_s'])
selected=[4,22,26,50,60,69,75,86,89,91,98,102,104,106,108,110,112,114,116,124,126,128,132,134,136,138,140,142,144,146,150,152,154,156,158,160,162,164,166]
events=[]
for i in selected:
 m=rows[i]['message'];spec=dict(entry=i)
 if i in [4,60,116]:
  spec.update(kind='user' if i==4 else 'assistant',text='\n'.join(c['text'] for c in m['content'] if c['type']=='text'))
 else:
  call=next(c for c in m['content'] if c['type']=='toolCall');a=call['arguments'];ri,res=source['results'][call['id']]
  raw='\n'.join(c['text'] for c in res['message']['content'] if c['type']=='text');parsed={}
  try:parsed=json.loads(raw)
  except ValueError:pass
  imgs=[c for c in res['message']['content'] if c['type']=='image']
  if call['name']=='exec':spec['arg_fields']=['description']
  if i in [104,138,162]:spec['arg_fields']+=['args.steps.1.tcp']
  if i in [104,162]:spec['arg_fields']+=['args.steps.1.q']
  if call['name']=='question':spec.update(arg_fields=['questions.1.question'],result_text='Any blue goes left')
  if call['name']=='device_stop':spec['arg_fields']=['reason'];spec['result_text']='xarm: stopped (halt; affects xarm)'
  if imgs:spec.update(images=[len(imgs)-1],image_label='wrist_camera' if 'wrist' in a.get('description','') else 'third_person_camera')
  if parsed.get('error'):
   spec['result_text']='buffer_failed' if i==75 else 'IK'
   if spec['result_text'] not in raw:spec['result_text']=parsed['error'].splitlines()[-1][-180:]
  if i in [102,160]:spec['result_text']=parsed['output'].splitlines()[0].split(']')[0]+']'
 events.append(spec)
edit['events']=events
# Each selected image is the actual returned image; no image is shown before its tool result.
holds={0:(1.5,'Original task'),1079:(2,'Final verification')}
for i,secs in [(60,1),(116,1.5)]:holds[utc(rows[i]['timestamp'])-origin]=(secs,'Public recovery explanation')
for i,secs in [(22,.65),(91,.4),(98,.4),(104,.4),(110,.4),(138,.4),(158,.4)]:
 call=next(c for c in rows[i]['message']['content'] if c['type']=='toolCall');_,res=source['results'][call['id']]
 holds[utc(res['timestamp'])-origin]=(secs,'Inspect the result')
breaks=[(0,'Reading the task'),(45,'Inspecting the scene'),(74,'Confirming the sorting rule'),(101,'Checking gripper geometry'),
 (178,'Operator setup confirmation'),(220,'Measuring object locations'),(288,'Recovering controller state'),(319,'Planning the first grasp'),
 (349,'Inspecting the missed grasp'),(392,'Planning a rotated grasp'),(478,'Locating the red cube'),(526,'Replanning the transfer'),
 (565,'Reassessing displaced objects'),(620,'Locating the blue figure'),(712,'Planning a deeper cube grasp'),(790,'Locating the pineapple'),
 (915,'Locating the multicolor figure'),(946,'Planning the final grasp'),(1078.5,'Five objects sorted')]
points={0,edit['end_source_s'],74.9,101.3,178.6,203.1,*[a for a,b in breaks]}
for w in windows:points.update([w['start_source_s'],w['end_source_s']])
activity=[]
for a,b in zip(sorted(points),sorted(points)[1:]):
 mid=(a+b)/2;ws=[w for w in windows if w['start_source_s']<=mid<=w['end_source_s']]
 text=min(ws,key=lambda w:w['speed'])['text'] if ws else next(v for k,v in reversed(breaks) if k<=mid)
 autonomy='Operator input' if 74.9<=mid<=101.3 or 178.6<=mid<=203.1 else 'Autonomous'
 activity.append(dict(start_source_s=a,end_source_s=b,text=text,autonomy=autonomy))
edit['status_overlay']=dict(activity=activity,elapsed_time=dict(format='HH:MM:SS / HH:MM:SS',total_source_s=1079,clock='Original DJI recording'))
# Fit motion to exactly 60 s while leaving the observed cube slip at its reviewed speed.
# All physical stages remain protected; only stationary gaps use the background rate.
def make_plan(factor):
 bounds={0,1079,*holds}
 for w in windows:bounds.update([w['start_source_s'],w['end_source_s']])
 intervals=[]
 for a,b in zip(sorted(bounds),sorted(bounds)[1:]):
  ws=[w for w in windows if w['start_source_s']<=(a+b)/2<=w['end_source_s']]
  speed=lambda w:w['speed']*(1 if w['stage']=='visually-reviewed-slip' else factor)
  w=min(ws,key=speed) if ws else None
  intervals.append((a,b,speed(w) if w else 180,w['text'] if w else 'Stationary planning'))
 plan=[dict(end_source_s=0,hold_s=holds[0][0],reason=holds[0][1])]
 for j,(a,b,speed,reason) in enumerate(intervals):
  before=0 if a in holds else min(intervals[j-1][2],speed) if j else 0
  after=0 if b in holds else min(intervals[j+1][2],speed) if j+1<len(intervals) else 0
  ramp=min(.45,(b-a)/3)
  plan += [dict(end_source_s=a+ramp,speed=before,end_speed=speed,reason=reason),dict(end_source_s=b-ramp,speed=speed,end_speed=speed,reason=reason),dict(end_source_s=b,speed=speed,end_speed=after,reason=reason)]
  if b in holds:plan.append(dict(end_source_s=b,hold_s=holds[b][0],reason=holds[b][1]))
 prev=total=0
 for p in plan:
  total+=p['hold_s'] if 'hold_s' in p else 2*(p['end_source_s']-prev)/(p['speed']+p['end_speed']);prev=p['end_source_s']
 return plan,total
low,high=.5,4
assert make_plan(low)[1]>60>make_plan(high)[1]
for _ in range(60):
 mid=(low+high)/2
 if make_plan(mid)[1]>60:low=mid
 else:high=mid
factor=(low+high)/2
plan,total=make_plan(factor)
plan[-1]['hold_s']+=60-total
for w in windows:
 if w['stage']!='visually-reviewed-slip':w['speed']*=factor
edit['pacing']=dict(target_duration_s=60,stationary_speed=180,motion_fit_factor=factor,
 note='Stationary planning and ordinary travel compressed most; grasp/contact slower, cube slip held at 1.5x, two-second final evidence hold.')
edit.update(retime=plan,duration=60,source_review=dict(critical_moments=windows,
 review='Full-run samples every 5 s, half-second anchor samples at 318–328 and 1070–1080 s; all 60 saved physical-stage states plus initial opening reviewed. Corn miss, gripper rotation, cube slip, regrasp, all deposits retained.',
 endpoint='All five objects visibly in assigned baskets; final return image available. Ends before subsequent stop and textual summary.',
 framing='Mild horizontal crop: 5% from each side, full height preserved. Baskets, objects and gripper remain visible; basket left/right follows the task camera, which differs from external camera viewpoint.',
 model_evidence='Entry 8 switches to gpt-6-astra before repeated user task at entry 9 and all executed tool calls; medium persists from entry 2. Opening initial task shown with execution-model subtitle.'))
timeline=Timeline(edit)
edit['poster_time']=timeline.output(utc(rows[23]['timestamp'])-origin)+.25
edit['review_times']=[0,edit['poster_time']]+[timeline.output(s) for s in [345,390,437,476,519,521,565,670,702,707,737,788,911,1005,1079]]+[edit['duration']-.1]
(HERE/'edit.json').write_text(json.dumps(edit,indent=2)+'\n')
print('Duration',edit['duration'],'events',len(events),'physical stages',len(windows))
