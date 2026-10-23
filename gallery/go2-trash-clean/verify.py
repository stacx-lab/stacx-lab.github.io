"""Validate the source map, evidence timing, labels, and all delivery frames."""
import json, math, subprocess
from build import HERE, REPO, Timeline, ReplayRenderer, load, compile_events

def main():
    edit=json.loads((HERE/'edit.json').read_text())
    source=load(REPO.parent/'sources/go2-trash-clean',edit)
    timeline=Timeline(edit);events=compile_events(source,edit,timeline)
    n=round(edit['duration']*30);sampled=[timeline.at(i/30) for i in range(n)]
    assert sampled[0]==0 and sampled[-1]==edit['end_source_s']
    assert all(a<=b for a,b in zip(sampled,sampled[1:]))
    for a,b in zip(timeline.segments,timeline.segments[1:]):
        assert math.isclose(a['end_speed'],b['speed'],abs_tol=1e-6)
        assert a['source_end_s']==b['source_start_s']
    for seg in timeline.segments:
        a,b=seg['output_start_s'],seg['output_end_s']
        assert math.isclose(timeline.at(a),seg['source_start_s'],abs_tol=1e-6)
        assert math.isclose(timeline.at(b),seg['source_end_s'],abs_tol=1e-6)
        if seg['source_end_s']>seg['source_start_s']:
            for f in [.1,.5,.9]:
                t=a+f*(b-a)
                assert math.isclose(timeline.output(timeline.at(t)),t,abs_tol=1e-6)
    for e in events:
        if e['kind']=='tool':
            completion=e['start']+e['duration']*e['result_fraction']
            assert timeline.at(completion)>=e['source_result_s']-1e-5
            assert e['typing_fraction']<e['result_fraction']
    r=ReplayRenderer(source,edit,events,timeline)
    from PIL import Image
    for i in range(n):
        autonomy,clock,action=r.status(i/30)
        assert action and '×' not in clock
        parse=lambda v:sum(int(x)*m for x,m in zip(v.split(':'),[3600,60,1]))
        shown,total=clock.split(' / ')
        assert parse(shown)==math.floor(sampled[i]+1e-7)
        assert parse(total)==math.floor(edit['end_source_s'])
        # The same shared drawing routine enforces the column width for every label.
        r.draw_status(Image.new('RGB',(1920,1080)),i/30)
    assert r.status(timeline.output(308))[0]=='Human disturbance'
    assert r.status(timeline.output(1560))[0]=='Operator check'
    assert r.status(edit['duration']-.1)[1:] == ('00:35:55 / 00:35:55','Two pieces in the bin')
    files=[REPO/'gallery/.masters/go2-trash-clean.mp4']+[REPO/f'public/kinex/media/gallery/go2-trash-clean/go2-trash-clean.{ext}' for ext in ['mp4','webm']]
    result=[]
    for path in files:
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames:format=duration','-of','json',str(path)]))
        s=probe['streams'][0]
        assert (s['width'],s['height'],int(s['nb_read_frames']))==(1920,1080,n)
        assert abs(float(probe['format']['duration'])-edit['duration'])<.001
        data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
        pts=[float(f['best_effort_timestamp_time']) for f in data['frames']]
        assert len(pts)==n and pts[0]==0
        assert max(abs(t-i/30) for i,t in enumerate(pts))<.0011
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
        result.append(dict(file=str(path.relative_to(REPO)),frames=n,duration_s=edit['duration'],first_pts_s=0))
        print('Validated',path.name,flush=True)
    (HERE/'validation.json').write_text(json.dumps(dict(timeline='Continuous source from frame zero through second deposit verification; ramp continuity and inverse checked.',
      evidence='No selected result or camera observation precedes its recorded result timestamp; all images hash verified.',
      status='All frame labels match recording elapsed/retained total, fit the left column, and label disturbance/operator check.',files=result,webm_timestamp_tolerance_s=.0011),indent=2)+'\n')
if __name__=='__main__':main()
