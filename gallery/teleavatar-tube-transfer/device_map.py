"""Rounded device abstraction adapted from the homepage robot illustration."""
from PIL import Image, ImageDraw, ImageFont
from render_video import BG, SANS, BOLD, RIGHT_X

SCALE = 3


def draw_device_map(active):
    image = Image.new('RGB', (710*SCALE, 260*SCALE), BG)
    draw = ImageDraw.Draw(image)
    transform = lambda p: ((345+(p[0]-280)*.68)*SCALE, (12+(p[1]-127)*.68)*SCALE)
    background, edge, accent = '#f8f7f2', '#96968f', '#7967c5'

    def color(device): return accent if device in active else edge
    def fill(device): return '#ece8f8' if device in active else background
    def box(bounds, device, radius=7, solid=None):
        a, b = transform(bounds[:2]), transform(bounds[2:])
        draw.rounded_rectangle((*a,*b), radius=radius*.68*SCALE,
            fill=solid or fill(device), outline=color(device), width=2*SCALE)
    def line(points, device, width=3, ink=None):
        points=[transform(p) for p in points]
        stroke=ink or color(device)
        size=max(1,round(width*.68*SCALE))
        draw.line(points,fill=stroke,width=size,joint='curve')
        for x,y in points:
            r=size/2
            draw.ellipse((x-r,y-r,x+r,y+r),fill=stroke)
    def circle(x,y,r,device,solid=False):
        x,y=transform((x,y));r*=.68*SCALE
        draw.ellipse((x-r,y-r,x+r,y+r),fill=color(device) if solid else fill(device),
                     outline=color(device),width=max(1,round(1.5*SCALE)))
    def text(point, content, size=13, ink='#74746e', bold=False):
        draw.text(transform(point),content,font=ImageFont.truetype(BOLD if bold else SANS,size*SCALE),fill=ink,anchor='mm')

    # Full wheeled base, telescoping torso, rounded links and camera lenses.
    a,b=transform((137,444)),transform((423,474))
    draw.ellipse((*a,*b),fill='#eae8e1')
    box((176,379,200,443),'base',9,solid='#b6b4ad')
    box((360,379,384,443),'base',9,solid='#b6b4ad')
    box((254,330,306,376),'lift_velocity',0)
    box((190,375,370,442),'base',18)
    for points in [[(210,388),(350,388)],[(213,431),(347,431)]]:
        line(points,'base',2,ink='#d7d4cb')
    circle(221,407,4,'base',True);circle(339,407,4,'base',True)
    text((280,410),'Base',12,bold=True)
    box((242,177,318,336),'lift_velocity',15)
    for points in [[(258,193),(258,239)],[(302,193),(302,239)],
                   [(257,281),(303,281)],[(257,291),(303,291)],[(257,301),(303,301)]]:
        line(points,'lift_velocity',2,ink='#d7d4cb')
    text((280,259),'Torso',12,bold=True)
    line([(280,177),(280,154)],'lift_velocity',7)

    anchors={}
    for side in ['right','left']:
        mirror=lambda x: x if side=='right' else 560-x
        elbow=(177,257) if side=='right' else (183,266)
        wrist=(187,309) if side=='right' else (205,313)
        points=[(mirror(x),y) for x,y in [(242,211),(211,211),elbow,wrist]]
        arm=side+'_arm'
        line(points,arm,29)
        line(points,arm,25,ink=fill(arm))
        for (x,y),r in [((211,211),15),(elbow,13),(wrist,10)]:
            circle(mirror(x),y,r,arm)
        for (x,y),r in [((211,211),5),(elbow,4)]:circle(mirror(x),y,r,arm,True)
        wx,wy=mirror(wrist[0]),wrist[1]
        gripper=side+'_gripper'
        box((wx-14,wy+10,wx+14,wy+29),gripper,4)
        for direction in [-1,1]:
            line([(wx+direction*11,wy+29),(wx+direction*16,wy+37),
                  (wx+direction*16,wy+45),(wx+direction*11,wy+48)],gripper,7)
        camera=side+'_wrist_stereo'
        box((wx-24,wy-26,wx+24,wy),camera,7)
        circle(wx,wy-13,8,camera);circle(wx,wy-13,3,camera,True)
        anchors[arm]=(mirror(211),211)
        anchors[camera]=(wx,wy-13)
        anchors[gripper]=(wx,wy+35)
    box((256,127,304,153),'head_stereo',7)
    circle(280,140,8,'head_stereo');circle(280,140,3,'head_stereo',True)
    anchors.update(head_stereo=(304,140),lift_velocity=(254,350),base=(370,413))

    # Exact recorded device IDs stay outside the silhouette, aligned in two rails.
    labels=[('head_stereo',500,4),('lift_velocity',8,4),('base',500,218)]
    for side,x in [('right',8),('left',500)]:
        labels += [(side+'_arm',x,65),(side+'_wrist_stereo',x,116),(side+'_gripper',x,168)]
    font=ImageFont.truetype(SANS,16*SCALE)
    for device,x,y in labels:
        selected=device in active
        width=draw.textlength(device,font=font)+20*SCALE
        if x==8: x=(195*SCALE-width)/SCALE
        bounds=(x*SCALE,y*SCALE,x*SCALE+width,(y+28)*SCALE)
        anchor=transform(anchors[device])
        end=(bounds[2] if x<250 else bounds[0],(y+14)*SCALE)
        # Route the lift label around the outside of the arm.
        route=[anchor,end]
        if device=='lift_velocity':route=[anchor,(225*SCALE,anchor[1]),(225*SCALE,18*SCALE),end]
        draw.line(route,fill='#b6a9dc' if selected else '#ccc9c1',width=SCALE,joint='curve')
        draw.rounded_rectangle(bounds,radius=6*SCALE,fill='#e9e3f6' if selected else '#eeece5')
        draw.text(((x+10)*SCALE,(y+5)*SCALE),device,font=font,fill=accent if selected else '#85857e')
    return image.resize((710,260),Image.Resampling.LANCZOS)


def paste_device_map(renderer, out, event):
    active=frozenset(event.get('active_devices',[]))
    if not hasattr(renderer,'device_map_cache'):renderer.device_map_cache={}
    if active not in renderer.device_map_cache:renderer.device_map_cache[active]=draw_device_map(active)
    out.paste(renderer.device_map_cache[active],(RIGHT_X,80))
