import subprocess, sys, wave, math
from pathlib import Path
from PIL import Image
from render import make_clip
from config import WORK

# No API keys required: validates FFmpeg, image pipeline and local file handling.
img=WORK/'selftest.jpg'
Image.new('RGB',(1080,1920),(12,18,28)).save(img)
# 1 second mono WAV at 24 kHz
wav=WORK/'selftest.wav'
with wave.open(str(wav),'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
    for i in range(24000):
        v=int(8000*math.sin(2*math.pi*440*i/24000))
        w.writeframesraw(v.to_bytes(2,'little',signed=True))
out=make_clip({'path':str(img),'type':'image'},1,999)
subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height','-of','default=nw=1',str(out)],check=True)
print('SELF-TEST PASS:', out)
