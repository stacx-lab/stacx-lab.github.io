"""Author a continuous recording map with protected physical-command windows."""
import json, math
from build import HERE, REPO, load, utc, Timeline
root=REPO.parent/'sources/go2-trash-clean'
old=json.loads((root/'edit.json').read_text())
edit=dict(title='Collecting litter',subtitle='Go2 + D1 × GPT-6-Astra · medium · Real world',robot_label='Go2 + D1',environment='Real world',
 bundle=old['bundle'],recording='DJI_20261011161453_0013_D.MP4',clock=dict(old['clock'],camera_start_utc='2026-10-11T20:14:55.200Z',uncertainty_s=.2,last_frame_s=(69172-1)*1001/30000),
 from_start=True,continuous_source=True,end_source_s=2155.6,device_map={'description':'Go2 + D1 silhouette from the supplied go2_d1.py URDF/profile dimensions; fixed illustrative pose, not live kinematics.'})
source=load(root,edit);rows=source['entries'];origin=source['origin']
windows=[]
for i,row in enumerate(rows):
 start=utc(row['timestamp'])-origin
 if start>edit['end_source_s']:break
 for c in row.get('message',{}).get('content',[]):
  if c.get('type')!='toolCall':continue
  a=c['arguments'];name=c['name']
  if not (name=='servo' or name=='device' and a.get('action')=='write'):continue
  ri,res=source['results'][c['id']]; end=utc(res['timestamp'])-origin
  raw='\n'.join(x.get('text','') for x in res['message']['content'] if x.get('type')=='text')
  try:parsed=json.loads(raw)
  except ValueError:parsed={}
  if res['message'].get('isError') or parsed.get('error'):continue
  dev=a.get('deviceID',a.get('device'))
  # Write responses acknowledge an asynchronous action before its physical end.
  if name=='device':end=max(end,start+a.get('args',{}).get('duration_s',3))
  start=max(0,start-.5);end=min(edit['end_source_s'],end+.8)
  speed=min(8,(end-start)/.55);label='Positioning the arm'
  if dev=='base':label='Walking toward the bin' if 800<start<1200 or start>1800 else 'Repositioning the base'
  if dev=='gripper':speed=1.5;label='Grasping the paper' if a['args']['actions'][0]<0 else 'Releasing into the bin'
  if i in [272,490]:speed=2.5;label='Lifting the paper'
  if i in [250,260,468,478]:speed=4;label='Adjusting the grasp'
  windows.append(dict(start_source_s=start,end_source_s=end,speed=speed,entry=i,text=label))
windows.append(dict(start_source_s=306,end_source_s=311,speed=1,entry=None,text='Paper moved by a broom',autonomy='Human disturbance'))
windows.sort(key=lambda x:x['start_source_s'])
# Editorial intervals also cover omitted terminal calls.
breaks=[(0,'Inspecting the scene'),(150,'Locating the paper'),(310.999,'Planning the grasp'),(350,'Attempting the first grasp'),(383,'Recovering arm motion'),(450,'Relocating the paper'),(640,'Repositioning the grasp'),(750,'Checking the grasp'),(800,'Planning the route'),(1000,'Locating the bin'),(1165,'Verifying the first deposit'),(1200,'Searching for more litter'),(1487,'Checking the wrist'),(1517,'Stopping for inspection'),(1574.23,'Resuming after the check'),(1600,'Locating the second piece'),(1725,'Checking the grasp'),(1800,'Planning the return'),(2000,'Aligning with the bin'),(2132,'Verifying the second deposit')]
points={0,edit['end_source_s'],1552.7,1574.23}
for a,b in zip(breaks,breaks[1:]):points.add(b[0])
for w in windows:points.update([w['start_source_s'],w['end_source_s']])
activity=[]
for a,b in zip(sorted(points),sorted(points)[1:]):
 mid=(a+b)/2;act=next((w for w in windows if w['start_source_s']<=mid<=w['end_source_s']),None)
 text=act['text'] if act else next(label for start,label in reversed(breaks) if start<=mid)
 autonomy=act.get('autonomy','Autonomous') if act else 'Autonomous'
 if 1552.7<=mid<=1574.23:autonomy='Operator check';text='Paused for inspection'
 activity.append(dict(start_source_s=a,end_source_s=b,text=text,autonomy=autonomy))
edit['status_overlay']=dict(activity=activity,elapsed_time={'format':'HH:MM:SS / HH:MM:SS','clock':'Original recording, retained through second deposit verification','total_source_s':edit['end_source_s']})
# Keep the old selection's verbatim evidence, but schedule it on actual call/result clocks.
events=[]
for s in old['events']:
 if s['entry']>566 or s['entry']==126 and s.get('kind')=='assistant':continue
 spec={k:v for k,v in s.items() if k in ['entry','kind','call','text','code_field','code_excerpt','arg_fields','result_fields','result_text']}
 row=rows[s['entry']];msg=row['message']
 if spec.get('kind') not in ['user','assistant']:
  call=[c for c in msg['content'] if c.get('type')=='toolCall'][0];args=call['arguments']
  ri,res=source['results'][call['id']]
  raw='\n'.join(c.get('text','') for c in res['message']['content'] if c.get('type')=='text')
  if call['name']=='read':spec['arg_fields']=['path'];spec['image_label']='d435 · head camera' if '/d435/' in args.get('path','') else 'd405 · wrist camera'
  if call['name']=='bash':
   command=args['command'];spec.update(code_field='command',code_excerpt=command if len(command)<450 else command.splitlines()[0])
  if call['name']=='device_stop':spec['result_text']=raw.splitlines()[0]
 events.append(spec)
edit['events']=events
# Extra holds retain readable task, misses, recovery prompt, and final evidence.
operator_time=utc(rows[453]['timestamp'])-origin
holds={0:(1.5,'Original task'),operator_time:(1.5,'Operator confirmation'),2155.6:(2.2,'Final verification')}
for entry in [18,114,158,182,254,276,364,442,494]:
 ev=next((s for s in events if s['entry']==entry),None)
 if ev:
  call=next(c for c in rows[entry]['message']['content'] if c.get('type')=='toolCall');_,res=source['results'][call['id']]
  t=utc(res['timestamp'])-origin;holds[t]=(.65,'Inspect camera or recovery result')
# Piecewise speed ramps use a shared source map and ease every change; no skipped frames/time intervals.
def make_plan(background):
 boundaries={0,edit['end_source_s'],*holds.keys()}
 for w in windows:boundaries.update([w['start_source_s'],w['end_source_s']])
 intervals=[];bounds=sorted(boundaries)
 for a,b in zip(bounds,bounds[1:]):
  mid=(a+b)/2;w=next((w for w in windows if w['start_source_s']<=mid<=w['end_source_s']),None)
  intervals.append((a,b,w['speed'] if w else background,w['text'] if w else 'Stationary planning'))
 plan=[]
 if 0 in holds:plan.append(dict(end_source_s=0,hold_s=holds[0][0],reason=holds[0][1]))
 for j,(a,b,speed,reason) in enumerate(intervals):
  before=0 if a in holds else (intervals[j-1][2]+speed)/2 if j else 0
  after=0 if b in holds else (intervals[j+1][2]+speed)/2 if j+1<len(intervals) else 0
  ramp=min(.35,(b-a)/3)
  plan.extend([dict(end_source_s=a+ramp,speed=before,end_speed=speed,reason=reason),dict(end_source_s=b-ramp,speed=speed,end_speed=speed,reason=reason),dict(end_source_s=b,speed=speed,end_speed=after,reason=reason)])
  if b in holds:plan.append(dict(end_source_s=b,hold_s=holds[b][0],reason=holds[b][1]))
 return plan
plan=make_plan(120)
duration=sum(p.get('hold_s',0) if 'hold_s' in p else 0 for p in plan)
prev=0
for p in plan:
 if 'hold_s' not in p:duration+=2*(p['end_source_s']-prev)/(p['speed']+p['end_speed'])
 prev=p['end_source_s']
# End on a complete frame boundary by extending the final hold.
plan[-1]['hold_s']+=math.ceil(duration)-duration
edit.update(retime=plan,duration=math.ceil(duration),source_review=dict(critical_moments=windows,disturbances=old['disturbances'],
 endpoint='Second paper visibly released; final wrist-camera result confirms deposit. Ends before retraction/searching. Two pieces collected, not all trash cleared.',
 framing='Entire original 16:9 recording letterboxed without crop or zoom.',
 motion_method='Every successful servo/device-write interval protected, including omitted calls; asynchronous writes extended by commanded duration plus 0.8s. Reviewed source motion and human disturbance.'))
timeline=Timeline(edit)
edit['poster_time']=timeline.output(utc(rows[19]['timestamp'])-origin)+.2
edit['review_times']=[0,edit['poster_time']]+[timeline.output(t) for t in [200,282,307,309,367,450,655,724,741,1163,1518,1574.23,1695,1721,1773,2130,2155.6]]+[edit['duration']-.2]
(HERE/'edit.json').write_text(json.dumps(edit,ensure_ascii=False,indent=2)+'\n')
print('Duration',edit['duration'],'motions',len(windows),'events',len(events))
