"""Anima a caricatura (recorte + fundo neon) em vídeo vertical 1080x1920. Uso: python3 scripts/animar-avatar.py [saida.mp4]"""
import sys, math, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
W,H,FPS,DUR=1080,1920,30,9
N=FPS*DUR
out=sys.argv[1] if len(sys.argv)>1 else 'assets/avatar/video/avatar-animado.mp4'
cut=Image.open('assets/avatar/retrato-recorte.png').convert('RGBA')
SW=1500
subj0=cut.resize((SW,SW),Image.LANCZOS)
CY=(34,211,238); MG=(232,121,249); NAVY=(1,11,40)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
d=np.sqrt((xx-W/2)**2+(yy-H*0.5)**2)/(H*0.6)
base=np.clip(1-d,0,1)[...,None]
bgbase=(np.array(NAVY)*(1-base)+np.array([30,40,100])*base)
# trilhas de circuito (esquerda ciano, direita magenta)
paths=[[(0,520),(170,520),(230,580),(330,580)],[(0,700),(120,700),(180,760)],[(0,1160),(200,1160),(260,1220),(380,1220)],[(0,1360),(140,1360),(200,1420)],[(0,360),(120,360),(180,300)]]
def draw_paths(dr,prog,col,mirror,alpha):
    for p in paths:
        P=[(W-x if mirror else x,y) for x,y in p]
        segs=[math.dist(P[i],P[i+1]) for i in range(len(P)-1)]; tot=sum(segs); run=prog*tot*1.0
        pts=[P[0]]; acc=0
        for i,s in enumerate(segs):
            if run>=acc+s: pts.append(P[i+1]); acc+=s
            else:
                t=(run-acc)/s; pts.append((P[i][0]+(P[i+1][0]-P[i][0])*t,P[i][1]+(P[i+1][1]-P[i][1])*t)); break
        if len(pts)>1: dr.line(pts,fill=col+(alpha,),width=5,joint='curve')
        x,y=pts[-1]; dr.ellipse((x-9,y-9,x+9,y+9),fill=col+(min(255,alpha+80),))
rng=np.random.default_rng(3); parts=[(rng.uniform(0,W),rng.uniform(0,H),rng.uniform(40,160),rng.uniform(2,6),rng.random()<.5) for _ in range(60)]
font=ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',150)
fsmall=ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Medium.otf',52)
left=np.clip(1-(np.linspace(0,1,W)/0.55),0,1); right=np.clip((np.linspace(0,1,W)-0.45)/0.55,0,1)
leftL=Image.fromarray((np.tile(left,(H,1))*255).astype(np.uint8)); rightL=Image.fromarray((np.tile(right,(H,1))*255).astype(np.uint8))
cyan=Image.new('RGBA',(W,H),CY+(255,)); mag=Image.new('RGBA',(W,H),MG+(255,))
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-shortest','-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-preset','medium','-c:a','aac','-b:a','128k','-movflags','+faststart',out],stdin=subprocess.PIPE)
for f in range(N):
    t=f/FPS
    pulse=0.5+0.5*math.sin(t*2*math.pi/2.2)
    bg=Image.fromarray(bgbase.astype(np.uint8)).convert('RGBA')
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(ov)
    prog=min(1,max(0,(t-0.3)/1.6)); draw_paths(dr,prog,CY,False,int(110+60*pulse)); draw_paths(dr,prog,MG,True,int(110+60*pulse))
    for (px,py,sp,r,c) in parts:
        y=(py-sp*t)%H; x=px+12*math.sin(t+px); col=CY if c else MG
        dr.ellipse((x-r,y-r,x+r,y+r),fill=col+(150,))
    halo=Image.new('RGBA',(W,H),(0,0,0,0)); rr=380+30*pulse
    ImageDraw.Draw(halo).ellipse((W/2-rr,H*0.46-rr,W/2+rr,H*0.46+rr),fill=(96,81,235,int(130+50*pulse)))
    scene=Image.alpha_composite(bg,halo.filter(ImageFilter.GaussianBlur(110))); scene=Image.alpha_composite(scene,ov)
    # entrada: zoom + fade; depois respiração e leve giro
    ent=min(1,t/1.0); ease=1-(1-ent)**3
    sc=(0.88+0.12*ease)*(1+0.012*math.sin(t*2*math.pi/3.0))
    rot=1.6*math.sin(t*2*math.pi/5.0)
    s=subj0.resize((int(SW*sc),int(SW*sc)),Image.BICUBIC).rotate(rot,resample=Image.BICUBIC,expand=True)
    sx=(W-s.width)//2+int(10*math.sin(t*2*math.pi/4)); sy=H-s.height+190-int(8*math.sin(t*2*math.pi/3))+int((1-ease)*80)
    lay=Image.new('RGBA',(W,H),(0,0,0,0)); lay.paste(s,(sx,sy)); a=lay.split()[3]
    a=a.point(lambda v:int(v*ease))
    edge=ImageChops.subtract(a.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(2)),a)
    rim=Image.new('RGBA',(W,H),(0,0,0,0)); rim.paste(cyan,(0,0),ImageChops.multiply(edge,leftL)); rim.paste(mag,(0,0),ImageChops.multiply(edge,rightL))
    gl=rim.filter(ImageFilter.GaussianBlur(22)); k=0.7+0.5*pulse
    gl.putalpha(gl.split()[3].point(lambda v:min(255,int(v*k))))
    lay.putalpha(a); scene=Image.alpha_composite(scene,gl); scene=Image.alpha_composite(scene,lay); scene=Image.alpha_composite(scene,rim)
    # título
    ta=min(1,max(0,(t-1.2)/0.8)); 
    tx=Image.new('RGBA',(W,H),(0,0,0,0)); td=ImageDraw.Draw(tx)
    parts_t=[('1st',(242,244,250)),('genius',CY),('AI',MG)]
    wtot=sum(td.textlength(p,font=font) for p,_ in parts_t); x=(W-wtot)/2; y=150+int((1-ta)*30)
    for p,c in parts_t:
        td.text((x,y),p,font=font,fill=c+(int(255*ta),)); x+=td.textlength(p,font=font)
    sub='Agentes de IA que trabalham por você'; sa=min(1,max(0,(t-2.2)/0.8))
    td.text(((W-td.textlength(sub,font=fsmall))/2,340),sub,font=fsmall,fill=(179,184,202,int(255*sa)))
    glw=tx.filter(ImageFilter.GaussianBlur(14)); scene=Image.alpha_composite(scene,glw); scene=Image.alpha_composite(scene,tx)
    if t>DUR-0.5:
        fo=(t-(DUR-0.5))/0.5; scene=Image.blend(scene,Image.new('RGBA',(W,H),NAVY+(255,)),fo*0.8)
    ff.stdin.write(np.asarray(scene.convert('RGB')).tobytes())
ff.stdin.close(); ff.wait(); print('ok',out)
