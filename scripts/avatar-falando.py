"""Caricatura falando: boca guiada pelo volume do áudio, piscadas, legendas e cartão de vídeo.
Uso: python3 scripts/avatar-falando.py AUDIO.wav LEGENDAS.txt SAIDA.mp4 [CLIPE_CARTAO.mp4]
LEGENDAS.txt: uma legenda por linha (tempo distribuído pelo comprimento do texto na fala detectada).
Para usar a voz real do dono, passe o .wav dela; nada mais muda."""
import sys, math, os, subprocess, glob, wave, shutil, numpy as np, cv2
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
W,H,FPS=1080,1920,30
audio,legf,out=sys.argv[1:4]; clip=sys.argv[4] if len(sys.argv)>4 else 'assets/avatar/video/avatar-animado.mp4'
TMP='/tmp/claude-0/work/falando'; shutil.rmtree(TMP,ignore_errors=True); os.makedirs(TMP+'/fr'); os.makedirs(TMP+'/card')
# ---- áudio -> envelope por quadro
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',audio,'-ar','16000','-ac','1',TMP+'/a.wav'],check=True)
w=wave.open(TMP+'/a.wav'); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768; sr=w.getframerate()
DUR=len(x)/sr; TAIL=1.2; TOTAL=DUR+TAIL; N=int(TOTAL*FPS)
hop=sr//FPS; rms=np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop]**2)+1e-9) if i*hop<len(x) else 0 for i in range(N)])
p=np.percentile(rms[rms>0.005],90) if (rms>0.005).any() else 1
op=np.clip(rms/p,0,1.15)**0.9; op=np.minimum(op,1)
sm=np.copy(op)
for i in range(1,N): sm[i]=max(op[i],sm[i-1]*0.55) if op[i]<sm[i-1] else 0.6*op[i]+0.4*sm[i-1]
speech=np.where(rms>0.01)[0]; t0=speech[0]/FPS if len(speech) else 0; t1=speech[-1]/FPS if len(speech) else DUR
lines=[l.strip() for l in open(legf,encoding='utf8') if l.strip()]
wts=np.array([len(l)+6 for l in lines],float); edges=np.concatenate([[0],np.cumsum(wts)])/wts.sum()
caps=[(t0+(t1-t0)*edges[i],t0+(t1-t0)*edges[i+1],l) for i,l in enumerate(lines)]
# ---- cartão de vídeo
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',clip,'-vf','crop=1080:608:0:560,scale=820:462,fps=15','-q:v','3',TMP+'/card/%04d.jpg'],check=True)
ncard=len(glob.glob(TMP+'/card/*.jpg'))
# ---- recursos
SRC=cv2.cvtColor(cv2.imread('assets/avatar/retrato-recorte.png',cv2.IMREAD_UNCHANGED),cv2.COLOR_BGRA2RGBA)
SH,SWd=SRC.shape[:2]
CY=(34,211,238); MG=(232,121,249); NAVY=(1,11,40)
F=lambda n,s: ImageFont.truetype(f'/usr/share/fonts/opentype/inter/Inter-{n}.otf',s)
fcap=F('ExtraBold',62); ftag=F('ExtraBold',34); fbrand=F('ExtraBold',54)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
dd=np.sqrt((xx-W/2)**2+(yy-H*0.5)**2)/(H*0.6); bb=np.clip(1-dd,0,1)[...,None]
BG=Image.fromarray((np.array(NAVY)*(1-bb)+np.array([30,40,100])*bb).astype(np.uint8)).convert('RGBA')
rng=np.random.default_rng(3); parts=[(rng.uniform(0,W),rng.uniform(0,H),rng.uniform(40,160),rng.uniform(2,6),rng.random()<.5) for _ in range(60)]
paths=[[(0,520),(170,520),(230,580),(330,580)],[(0,700),(120,700),(180,760)],[(0,1160),(200,1160),(260,1220),(380,1220)],[(0,1360),(140,1360),(200,1420)]]
gx=np.linspace(0,1,W); LL=Image.fromarray((np.tile(np.clip(1-gx/0.55,0,1),(H,1))*255).astype(np.uint8)); RL=Image.fromarray((np.tile(np.clip((gx-0.45)/0.55,0,1),(H,1))*255).astype(np.uint8))
CYI=Image.new('RGBA',(W,H),CY+(255,)); MGI=Image.new('RGBA',(W,H),MG+(255,))
# pele ao redor dos olhos/boca para tampar piscada
def skin(px,py):
    r=SRC[py-3:py+4,px-3:px+4,:3].reshape(-1,3); return tuple(int(v) for v in np.median(r,0))
EYES=[((547,460),skin(547,434)),((752,442),skin(752,416))]
def mouth_line(xv): return 707-(xv-555)*(35/250.0)
Y,X=np.mgrid[0:SH,0:SWd].astype(np.float32)
SRCB=cv2.blur(SRC,(31,1))
def talk_frame(o,blink):
    img=SRC.copy(); my=Y.copy(); apm=np.zeros(Y.shape,bool)
    if o>0.02:
        d=34*o; ml=mouth_line(X)
        wx=np.exp(-((X-680)/150)**2)
        below=Y-ml
        f=np.clip(below/26,0,1)*np.exp(-np.clip(below-26,0,None)/130)
        my=Y-d*wx*f
    if blink>0.02:
        for (cx,cy),_ in EYES:
            top=cy-48; a0=cy-20; a1=cy+12; ab=a0+blink*(a1-a0)*0.95
            reg=(np.abs(X-cx)<70)&(Y>top)&(Y<a1+6)
            srcy=np.where(Y<ab, top+(Y-top)*(a0-top)/max(ab-top,1), a0-3)
            wxe=np.clip(1-((np.abs(X-cx)-44)/26),0,1)*np.clip((a1+6-Y)/6,0,1)*np.clip((Y-top)/8,0,1)
            my=np.where(reg,my*(1-wxe)+srcy*wxe,my); apm|=reg&(Y>=ab)&(Y<=a1+2)&(wxe>0.3)
    if o>0.02 or blink>0.02:
        img=cv2.remap(img,X,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)
        if apm.any(): img=np.where(apm[...,None],cv2.remap(SRCB,X,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT),img)
    pil=Image.fromarray(img)
    if o>0.08:
        d=34*o; m=Image.new('L',(SWd,SH),0); md=ImageDraw.Draw(m)
        cx=680; cl=mouth_line(cx)+3
        rx=62+30*o
        md.ellipse((cx-rx,cl-1,cx+rx,cl+d*1.05),fill=255); m=m.filter(ImageFilter.GaussianBlur(1.6))
        cav=Image.new('RGBA',(SWd,SH),(0,0,0,0)); cd=ImageDraw.Draw(cav)
        cd.ellipse((cx-rx,cl-1,cx+rx,cl+d*1.05),fill=(52,14,16,255))
        cd.ellipse((cx-rx*0.62,cl+d*0.45,cx+rx*0.62,cl+d*1.05),fill=(150,60,64,255))
        cd.rounded_rectangle((cx-rx*0.58,cl-1,cx+rx*0.58,cl+d*0.26),radius=4,fill=(222,212,196,255))
        cav.putalpha(ImageChops.multiply(m,Image.new('L',(SWd,SH),255)))
        pil=pil.convert('RGBA'); a=pil.split()[3]; pil=Image.alpha_composite(pil,Image.merge('RGBA',(*cav.split()[:3],cav.split()[3])))
        pil.putalpha(a)
    return pil
blink_times=[1.6,4.9,8.3,11.6,15.2,18.4,21.5]
def blink_at(t):
    for bt in blink_times:
        u=(t-bt)/0.17
        if 0<=u<=1: return math.sin(u*math.pi)
    return 0
def draw_paths(dr,prog,col,mirror,alpha):
    for pth in paths:
        P=[(W-x_ if mirror else x_,y_) for x_,y_ in pth]
        segs=[math.dist(P[i],P[i+1]) for i in range(len(P)-1)]; tot=sum(segs); run=prog*tot; pts=[P[0]]; acc=0
        for i,s in enumerate(segs):
            if run>=acc+s: pts.append(P[i+1]); acc+=s
            else:
                t=(run-acc)/s; pts.append((P[i][0]+(P[i+1][0]-P[i][0])*t,P[i][1]+(P[i+1][1]-P[i][1])*t)); break
        if len(pts)>1: dr.line(pts,fill=col+(alpha,),width=5,joint='curve')
        xx_,yy_=pts[-1]; dr.ellipse((xx_-9,yy_-9,xx_+9,yy_+9),fill=col+(min(255,alpha+80),))
def wrap(td,text,font,maxw):
    words=text.split(); lns=[]; cur=''
    for wd in words:
        tr=(cur+' '+wd).strip()
        if td.textlength(tr,font=font)<=maxw: cur=tr
        else: lns.append(cur); cur=wd
    lns.append(cur); return lns
def render(fi):
    t=fi/FPS; pulse=0.5+0.5*math.sin(t*2*math.pi/2.2)
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(ov)
    prog=min(1,max(0,(t-0.3)/1.6)); al=int(110+60*pulse); draw_paths(dr,prog,CY,False,al); draw_paths(dr,prog,MG,True,al)
    for (px,py,sp,r,c) in parts:
        y=(py-sp*t)%H; xq=px+12*math.sin(t+px); dr.ellipse((xq-r,y-r,xq+r,y+r),fill=(CY if c else MG)+(150,))
    halo=Image.new('RGBA',(W//4,H//4),(0,0,0,0)); rr=(380+30*pulse)/4
    ImageDraw.Draw(halo).ellipse((W/8-rr,H*0.46/4-rr,W/8+rr,H*0.46/4+rr),fill=(96,81,235,int(130+50*pulse)))
    halo=halo.filter(ImageFilter.GaussianBlur(26)).resize((W,H),Image.BILINEAR)
    scene=Image.alpha_composite(BG,halo); scene=Image.alpha_composite(scene,ov)
    o=float(sm[min(fi,N-1)]); bl=blink_at(t)
    subj=talk_frame(o,bl)
    ent=min(1,t/0.8); ease=1-(1-ent)**3; SW=1500
    sc=(0.9+0.1*ease)*(1+0.010*math.sin(t*2*math.pi/3.0))
    s=subj.resize((int(SW*sc),int(SW*sc)),Image.BICUBIC).rotate(1.3*math.sin(t*2*math.pi/5.0)+0.8*o*math.sin(t*9),resample=Image.BICUBIC,expand=True)
    sx=(W-s.width)//2+int(8*math.sin(t*2*math.pi/4)); sy=H-s.height+190-int(6*math.sin(t*2*math.pi/3))+int((1-ease)*80)+int(6*o)
    lay=Image.new('RGBA',(W,H),(0,0,0,0)); lay.paste(s,(sx,sy)); a=lay.split()[3].point(lambda v:int(v*ease))
    sa=a.resize((W//2,H//2),Image.BILINEAR)
    edge=ImageChops.subtract(sa.filter(ImageFilter.MaxFilter(7)),sa)
    rim=Image.new('RGBA',(W//2,H//2),(0,0,0,0)); rim.paste(CYI.resize((W//2,H//2)),(0,0),ImageChops.multiply(edge,LL.resize((W//2,H//2)))); rim.paste(MGI.resize((W//2,H//2)),(0,0),ImageChops.multiply(edge,RL.resize((W//2,H//2))))
    gl=rim.filter(ImageFilter.GaussianBlur(11)).resize((W,H),Image.BILINEAR); k=0.7+0.5*pulse; gl.putalpha(gl.split()[3].point(lambda v:min(255,int(v*k))))
    rimf=rim.resize((W,H),Image.BILINEAR)
    lay.putalpha(a); scene=Image.alpha_composite(scene,gl); scene=Image.alpha_composite(scene,lay); scene=Image.alpha_composite(scene,rimf)
    tx=Image.new('RGBA',(W,H),(0,0,0,0)); td=ImageDraw.Draw(tx)
    # marca
    ba=min(1,max(0,(t-0.4)/0.6)); pr=[('1st',(242,244,250)),('genius',CY),('AI',MG)]
    wt=sum(td.textlength(q,font=fbrand) for q,_ in pr); bx=(W-wt)/2
    for q,c in pr: td.text((bx,56),q,font=fbrand,fill=c+(int(255*ba),)); bx+=td.textlength(q,font=fbrand)
    # cartão de vídeo
    cs=2.2; ce=min(1,max(0,(t-cs)/0.7)); cease=1-(1-ce)**3
    if ce>0:
        cardimg=Image.open(f'{TMP}/card/{(int((t-cs)*15))%ncard+1:04d}.jpg').convert('RGBA')
        cy0=170-int((1-cease)*420); bw=6
        brd=Image.new('RGBA',(820+2*bw,462+2*bw),CY+(255,)); gdt=Image.new('RGBA',brd.size,MG+(255,)); mk=Image.fromarray((np.tile(np.linspace(0,1,brd.width),(brd.height,1))*255).astype(np.uint8)); brd.paste(gdt,(0,0),mk)
        gcard=Image.new('RGBA',(W,H),(0,0,0,0)); gcard.paste(brd,((W-brd.width)//2,cy0-bw),None); gcard=gcard.filter(ImageFilter.GaussianBlur(18))
        tx=Image.alpha_composite(tx,gcard); tx.paste(brd,((W-brd.width)//2,cy0-bw)); tx.paste(cardimg,((W-820)//2,cy0))
        td=ImageDraw.Draw(tx)
        tag='▶ VÍDEO NOVO'; tw=td.textlength(tag,font=ftag)+44
        td.rounded_rectangle(((W-820)//2+20,cy0+20,(W-820)//2+20+tw,cy0+20+58),radius=29,fill=(232,121,249,235)); td.text(((W-820)//2+42,cy0+27),tag,font=ftag,fill=(1,11,40,255))
    # legenda
    for (c0,c1,txt) in caps:
        if c0-0.05<=t<=c1+0.15:
            fa=min(1,(t-(c0-0.05))/0.15,((c1+0.15)-t)/0.15+0.0) if True else 1; fa=max(0,min(1,fa))
            lns=wrap(td,txt,fcap,900); y=1640-int((len(lns)-1)*36)
            for ln in lns:
                tw=td.textlength(ln,font=fcap); td.text(((W-tw)/2,y),ln,font=fcap,fill=(255,255,255,int(255*fa)),stroke_width=7,stroke_fill=(1,11,40,int(255*fa))); y+=76
            break
    scene=Image.alpha_composite(scene,tx)
    if t>TOTAL-0.5: scene=Image.blend(scene,Image.new('RGBA',(W,H),NAVY+(255,)),((t-(TOTAL-0.5))/0.5)*0.85)
    scene.convert('RGB').save(f'{TMP}/fr/{fi:05d}.jpg',quality=93)
if __name__=='__main__':
    print('frames',N,'dur',round(TOTAL,1))
    with Pool(4) as pl: pl.map(render,range(N),chunksize=8)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',TMP+'/fr/%05d.jpg','-i',audio,'-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-preset','medium','-c:a','aac','-b:a','160k','-af','apad','-t',f'{TOTAL:.2f}','-movflags','+faststart',out],check=True)
    print('ok',out)
