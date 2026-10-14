"""Build the continuous red-cup edit from public evidence and reviewed camera anchors."""
import json,math
from build import HERE,REPO,load,utc,Timeline
root=REPO.parent/'sources/abc-yam-hang-mug-real'
clock=dict(camera_start_utc='2026-10-10T20:38:55.200Z',metadata_creation_utc='2026-10-10T20:38:53.000Z',
 camera_start_minus_metadata_s=2.2,fps=30000/1001,frames=64283,last_frame_s=64282*1001/30000,uncertainty_s=.8,
 method='Constant offset from three gripper-action anchors across 30 minutes; compared original camera frames with logged submission and requested action duration. Opening/late arm trajectories checked for consistency; slow servo ramps and settling make their visible onset less precise. No drift resolvable at this precision. Original entry ISO timestamps are used, not assistant generation-start fields.',
 anchors=[dict(entry=85,command_after_metadata_s=182.35,command_duration_s=2,observed_action_source_s=[180,182.5],description='First gripper closure around the cup'),
 dict(entry=252,command_after_metadata_s=846.84,command_duration_s=1.5,observed_action_source_s=[844.5,846.2],description='Release opens the jaws; cup drops at 845.3–845.9 s'),
 dict(entry=477,command_after_metadata_s=1985.82,command_duration_s=1.5,observed_action_source_s=[1983.5,1985.3],description='Final release transfers the cup to the peg; cup settles visibly at 1984–1985 s')])
device_map=json.loads((HERE.parent/'abc-yam-cube/edit.json').read_text())['device_map']
device_map['geometry_evidence']['files']=[]
device_map['geometry_evidence']['session_result_entries']=[13,14,15,19,20,21,22,46]
device_map['geometry_evidence']['note']='Same station geometry verified in the recorded read results: arm_1 can_right at y=-0.6096, arm_2 can_left at origin, matching wrist/overhead camera mounts and YAM URDF. Recorded files are evidence only and are never executed.'
device_map['description']='Two YAM arms on a bench; arm_1 is the right observation arm, arm_2 manipulates the red cup. Flange cameras and overhead camera match the session profiles. Static illustration, not live kinematics.'
edit=dict(title='Hang a red cup',subtitle='YAM × GPT-6-Astra · high · Real world',robot_label='YAM',environment='Real world',
 recording='DJI_20261010163853_0005_D.MP4',clock=clock,from_start=True,continuous_source=True,device_map=device_map,
 opening_context_note='The original task is displayed from output/source frame zero as opening context. Its recorded submission is source 4.181 s; all physical calls, results and observations retain their actual mapped timestamps. No pre-recording motion is invented.')
edit['recording_crop']=dict(source_dimensions=[1920,1080],xywh=[288,0,1440,1080],
 description='Static crop removes 15% from the left and 10% from the right, retaining full height; uniform scaling to the recording panel, without stretching. Requested to reduce empty margins and passing people at the left edge.')
source=load(root,edit);rows=source['entries'];origin=source['origin'];stamp=lambda r:utc(r['timestamp'])-origin
# End at the success report, before the arm-homing command in the same assistant message.
edit['end_source_s']=stamp(rows[494]);end_source=edit['end_source_s']
# All physical calls, including nested writes and omitted terminal cards, get protected windows.
windows=[]
for i,row in enumerate(rows):
 start=stamp(row)
 if start>=end_source:break
 for ci,call in enumerate(row.get('message',{}).get('content',[])):
  if not isinstance(call,dict) or call.get('type')!='toolCall':continue
  name=call['name'];args=call['arguments'];ri,res=source['results'][call['id']]
  raw='\n'.join(c.get('text','') for c in res['message']['content'] if c.get('type')=='text')
  try:parsed=json.loads(raw)
  except ValueError:parsed={}
  if res['message'].get('isError') or isinstance(parsed,dict) and parsed.get('error'):continue
  commands=[dict(deviceID=args['device'],action='servo',args=args)] if name=='servo' else args['calls'] if name=='devices' else [args] if name=='device' else []
  for cmd in commands:
   if cmd.get('action') not in ['servo','write']:continue
   device=cmd['deviceID'];finish=stamp(res)
   if cmd['action']=='write':finish=max(finish,start+cmd['args'].get('duration_s',1))
   # Extra guard covers approximate camera alignment and visible settling.
   a=max(0,start-1);b=min(end_source,finish+1.2)
   speed=min(12,(b-a)/.45);label='Aligning the cup'
   if device=='arm_1':speed=8;label='Positioning the right camera'
   if i==417:speed=6;label='Getting a direct handle view'
   if i==51:label='Approaching the cup'
   if 269<=i<=305:label='Replanning the grasp';speed=min(speed,9)
   if i in [91,98,313,320]:label='Lifting the cup';speed=5
   if device.startswith('gripper'):
    label='Grasping the cup' if i in [85,307,405] else 'Closing the camera gripper' if i==415 else 'Testing load transfer'
    speed=2
   if i==252:label='First release — cup slips';speed=1
   if i==477:label='Releasing onto the peg';speed=1.25
   if i in [458,487]:speed=3;label='Threading the handle deeper' if i==458 else 'Withdrawing to verify'
   windows.append(dict(start_source_s=a,end_source_s=b,speed=speed,entry=i,device=device,text=label))
windows.sort(key=lambda w:w['start_source_s'])
# The actual fall is protected even if command metadata were to change.
windows.append(dict(start_source_s=844,end_source_s=847.3,speed=1,entry=252,device='gripper_2',text='First release — cup slips'))
windows.sort(key=lambda w:w['start_source_s'])
selection=[(6,'user'),(18,4),(24,0),(28,'assistant'),(51,0),(55,0),(85,0),(91,0),(95,0),(109,0),(113,0),(185,0),(189,0),(215,0),(221,0),(240,0),(252,0),(258,0),(260,0),(262,'assistant'),(269,'assistant'),(273,0),(295,0),(307,0),(313,0),(317,0),(326,0),(330,0),(351,0),(373,0),(387,0),(401,0),(403,0),(405,0),(413,'assistant'),(417,0),(421,0),(428,0),(432,0),(444,0),(454,0),(458,0),(468,0),(474,0),(477,0),(483,0),(487,0),(491,0),(494,'assistant')]
events=[]
for i,kind in selection:
 spec=dict(entry=i)
 if isinstance(kind,str):spec['kind']=kind
 else:
  spec['call']=kind
  call=[c for c in rows[i]['message']['content'] if c.get('type')=='toolCall'][kind];a=call['arguments'];name=call['name']
  _,res=source['results'][call['id']];raw='\n'.join(c.get('text','') for c in res['message']['content'] if c.get('type')=='text')
  if name=='servo':spec['active_devices']=[a['device']]
  elif name=='devices':spec['active_devices']=[item['deviceID'] for item in a['calls']]
  elif name=='device':spec['active_devices']=[a['deviceID']]
  elif name=='device_stop':spec['active_devices']=[a['deviceID']] if a.get('deviceID') else ['arm_1','arm_2','gripper_1','gripper_2']
  elif name=='read' and '/devices/' in a.get('path',''):spec['active_devices']=[a['path'].split('/devices/')[1].split('/')[0]]
  if name=='read':
   spec['arg_fields']=['path']
   path=a['path'];spec['image_label']='Right wrist · camera_261122276271' if '261122276271' in path else 'Left wrist · camera_261922276652' if '261922276652' in path else 'Overhead · camera_261122276272' if '261122276272' in path else 'Recorded close-up · right wrist'
  if name=='device_stop':spec['result_text']=raw.splitlines()[0]
  if name=='servo':spec['result_fields']=['duration_s','actions_submitted']
 if i==269:spec['text']='I’ll recover the mug and use a deeper, verified insertion before releasing again.'
 if i==413:spec['text']='I’ve regrasped it and will check the handle from a more direct angle before trying again.'
 if i==494:spec['text']='The mug is now hanging from the peg and has stayed in place after the gripper withdrew.'
 events.append(spec)
edit['events']=events
# Keep each public recovery explanation and the new right-camera view readable.
holds={0:(1.0,'Original task'),end_source:(2.2,'Verified hanging cup')}
for i,duration,label in [(28,.5,'Initial observation'),(262,1.0,'First attempt failed'),(269,.9,'Replan after the fall'),(413,1.0,'Choose a clearer view')]:holds[stamp(rows[i])]=(duration,label)
for i,duration,label in [(24,.5,'Initial camera view'),(95,.3,'Cup grasped'),(258,.6,'Inspect the fallen cup'),(317,.4,'Cup recovered'),(401,.5,'Peg not bearing the weight'),(421,.8,'Direct view of the handle'),(483,.5,'Verify the release'),(491,.8,'Verify after withdrawal')]:
 spec=next(s for s in events if s['entry']==i);call=[c for c in rows[i]['message']['content'] if c.get('type')=='toolCall'][spec.get('call',0)];_,res=source['results'][call['id']]
 holds[stamp(res)]=(duration,label)
# Idle activity labels are independent of the selected session card.
phases=[(0,'Reading the task'),(20,'Inspecting the scene'),(80,'Planning the grasp'),(200,'Checking the grasp'),(250,'Inspecting hook alignment'),(600,'Checking handle clearance'),(844,'First release — cup slips'),(847.3,'Inspecting the failed attempt'),(904,'Replanning after the fall'),(1158,'Checking the recovered cup'),(1255,'Planning a deeper insertion'),(1490,'Checking peg support'),(1588,'Regrasping after the slip'),(1650,'Planning a clearer view'),(1707,'Checking the handle opening'),(1800,'Refining hook alignment'),(1955,'Checking the load transfer'),(1986,'Checking the hanging cup'),(2037,'Verifying after withdrawal')]
points={0,end_source,*[x[0] for x in phases]}
for w in windows:points.update([w['start_source_s'],w['end_source_s']])
activity=[]
for a,b in zip(sorted(points),sorted(points)[1:]):
 mid=(a+b)/2;active=[w for w in windows if w['start_source_s']<=mid<=w['end_source_s']]
 text=min(active,key=lambda w:w['speed'])['text'] if active else next(label for start,label in reversed(phases) if start<=mid)
 activity.append(dict(start_source_s=a,end_source_s=b,text=text))
edit['status_overlay']=dict(autonomy='Autonomous',activity=activity,hold_labels={label:label for duration,label in holds.values()},
 elapsed_time={'format':'HH:MM:SS / HH:MM:SS','clock':'Original camera recording, retained through success report before arm homing','total_source_s':end_source})
edit['status_overlay']['hold_labels']['Verified hanging cup']='Cup hanging — verified'
# Smooth all speed transitions. Min speed wins where physical windows overlap.
def make_plan(scale):
 def paced(w):
  if w['entry']==252:return 1.0
  if w['entry']==417:return 8.0
  if w['entry']==477:return 1.5
  if w['entry']==487:return 5.0
  if w['device'].startswith('gripper'):return 3.5
  return min(32, w['speed']*scale, (w['end_source_s']-w['start_source_s'])/.26)
 background=350
 points={0,end_source,*holds.keys()}
 for w in windows:points.update([w['start_source_s'],w['end_source_s']])
 bounds=sorted(points);intervals=[]
 for a,b in zip(bounds,bounds[1:]):
  mid=(a+b)/2;active=[w for w in windows if w['start_source_s']<=mid<=w['end_source_s']]
  w=min(active,key=paced) if active else None
  intervals.append((a,b,paced(w) if w else background,w['text'] if w else 'Stationary planning'))
 plan=[dict(end_source_s=0,hold_s=holds[0][0],reason=holds[0][1])]
 for j,(a,b,speed,reason) in enumerate(intervals):
  before=0 if a in holds else (intervals[j-1][2]+speed)/2 if j else 0
  after=0 if b in holds else (intervals[j+1][2]+speed)/2 if j+1<len(intervals) else 0
  ramp=min(.3,(b-a)/3)
  plan.extend([dict(end_source_s=a+ramp,speed=before,end_speed=speed,reason=reason),dict(end_source_s=b-ramp,speed=speed,end_speed=speed,reason=reason),dict(end_source_s=b,speed=speed,end_speed=after,reason=reason)])
  if b in holds:plan.append(dict(end_source_s=b,hold_s=holds[b][0],reason=holds[b][1]))
 return plan
def length(plan):
 total=0;prev=0
 for p in plan:
  total+=p['hold_s'] if 'hold_s' in p else 2*(p['end_source_s']-prev)/(p['speed']+p['end_speed']);prev=p['end_source_s']
 return total
low,high=1,8
assert length(make_plan(low))>60 and length(make_plan(high))<60
for _ in range(60):
 mid=(low+high)/2
 if length(make_plan(mid))>60:low=mid
 else:high=mid
plan=make_plan(high);duration=60
plan[-1]['hold_s']+=60-length(plan)
edit.update(retime=plan,duration=math.ceil(duration),source_review=dict(critical_moments=windows,
 emphasis=['Error recovery: initial release fails, cup is recovered and the insertion replanned; an additional unsupported release is detected before the final successful hang.',
 'Active sensing: right arm supplies wrist-camera views; after the unsuccessful load transfer, entry 413 requests a more direct angle and entry 417 moves the right arm, followed by the confirming view at entry 421.'],
 endpoint='Cup remains hanging after arm_2 withdraws; right-wrist observation and public success report retained. Later arm homing omitted.',
 framing='Static horizontal crop: source x=288..1728, full height 1080; 4:3 framing uniformly scaled to the recording panel. Robot arms, cup, rack and all task motions retained.',
 motion_method='All successful servo and nested device-write actions protected; asynchronous writes cover requested duration. Camera-clock guard: 1.0 s before and 1.2 s after. First fall and final release reviewed at half-/one-second resolution.',
 reviewed_files=['overview.jpg','clock-anchors.jpg','clock-wide.jpg','clock-fine.jpg','grip-anchors.jpg']))
timeline=Timeline(edit)
first_camera=next(t for t,(d,label) in holds.items() if label=='Initial camera view')
edit['poster_time']=timeline.output(first_camera)+.3
edit['review_times']=[0,0.8,edit['poster_time']]+[timeline.output(t) for t in [94,183,282,598,844.5,845.5,846.5,871,906,1131,1165,1590,1650,1690,1717,1984.5,1986,2034,2048]]+[edit['duration']-.2]
(HERE/'edit.json').write_text(json.dumps(edit,ensure_ascii=False,indent=2)+'\n')
print('Duration',edit['duration'],'motion windows',len(windows),'events',len(events))
