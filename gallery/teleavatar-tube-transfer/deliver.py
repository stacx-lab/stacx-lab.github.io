"""Encode a completed master to staging, validate, then replace published assets."""
import concurrent.futures, json, shutil, subprocess
from build import HERE, REPO, sha256

def main():
    name='teleavatar-tube-transfer'; master=REPO/f'gallery/.masters/{name}.mp4'
    edit=json.loads((HERE/'edit.json').read_text()); n=round(edit['duration']*30)
    stage=HERE/'.cache/delivery';stage.mkdir(parents=True,exist_ok=True)
    encoders={'mp4':['-c:v','libx264','-preset','slow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart'],
              'webm':['-c:v','libvpx-vp9','-deadline','good','-cpu-used','3','-b:v','0','-crf','38','-row-mt','1']}
    def encode(item):
        ext,settings=item;path=stage/f'{name}.{ext}'
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(master),'-map','0:v:0','-an',*settings,'-threads','4',str(path)],check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=nb_read_frames:format=duration','-of','json',str(path)]))
        assert int(probe['streams'][0]['nb_read_frames'])==n
        assert abs(float(probe['format']['duration'])-edit['duration'])<.001
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
        print('Encoded and decoded',ext,flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(encode,encoders.items()))
    shutil.copy2(HERE/f'{name}.poster.jpg',stage/f'{name}.poster.jpg')
    target=REPO/f'public/media/gallery/{name}';target.mkdir(parents=True,exist_ok=True)
    for ext in ['mp4','webm','poster.jpg']: shutil.copy2(stage/f'{name}.{ext}',target/f'{name}.{ext}')
    files={ext:dict(bytes=(target/f'{name}.{ext}').stat().st_size,sha256=sha256(target/f'{name}.{ext}')) for ext in ['mp4','webm','poster.jpg']}
    record=dict(id=name,source=str(master.relative_to(REPO)),source_sha256=sha256(master),source_bytes=master.stat().st_size,
       mp4_sha256=files['mp4']['sha256'],duration_s=edit['duration'],fps=30,frame_count=n,width=1920,height=1080,playback_rate=1,
       model='gpt-6-astra',effort='high',environment='Real world',robot='TeleAvatar',
       metadata_source='GPT-6-Astra from entry 1; high effort from entry 3 before the user task. Robot display name confirmed by user.',
       source_first_pts_s=0,delivery_first_pts_s=0,files=files,encoder_settings=encoders,
       provenance=f'gallery/{name}/{name}.provenance.json')
    manifest=REPO/'public/media/gallery/manifest.json';data=json.loads(manifest.read_text())
    data['clips']=[c for c in data['clips'] if c['id']!=name]
    pos=next(i for i,c in enumerate(data['clips']) if c['id']=='abc-yam-cube')+1
    data['clips'].insert(pos,record);manifest.write_text(json.dumps(data,indent=2)+'\n')
    provenance=HERE/f'{name}.provenance.json';data=json.loads(provenance.read_text());data['delivery']=record
    provenance.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('Created local delivery assets',flush=True)
if __name__=='__main__':main()
