"""Extract original camera frames for offline alignment and motion review."""
import argparse, concurrent.futures, json, math, subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
VIDEO=HERE.parent.parent.parent/'sources/abc-yam-hang-mug-real/DJI_20261010163853_0005_D.MP4'
FPS=30000/1001

def sheet(times,name):
    cache=HERE/'.cache/review';cache.mkdir(parents=True,exist_ok=True)
    def extract(t):
        index=math.floor(t*FPS);p=cache/f'{index:06}.jpg'
        if not p.exists():subprocess.run(['ffmpeg','-v','error','-y','-ss',str(max(0,(index-.5)/FPS)),'-i',str(VIDEO),'-frames:v','1','-vf','scale=960:540','-threads','1',str(p)],check=True)
        return p
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(extract,times))
    out=Image.new('RGB',(1920,570*math.ceil(len(times)/2)),'#f3f0e9');d=ImageDraw.Draw(out)
    font=ImageFont.truetype(str(HERE.parent.parent/'.agents/skills/kinex-session-video/assets/fonts/CommitMono-Regular.ttf'),20)
    for k,(t,p) in enumerate(zip(times,files)):
        x,y=k%2*960,k//2*570;out.paste(Image.open(p),(x,y));d.text((x+12,y+542),f'Original source {t:.2f}s',font=font,fill='black')
    out.save(HERE/f'{name}.jpg',quality=93)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('times',nargs='+',type=float);a=ap.parse_args();sheet(a.times,a.name)
