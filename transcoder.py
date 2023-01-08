import re
from os import path, remove
import subprocess
from subprocess import Popen
from datetime import datetime

class Transcoder():
  def __init__(self, flavors, sub, prog):
    self.flavors = flavors
    self.sub = sub
    self.prog = prog

  def transcode(self, src, chapters = None):
    cmd = ['ffmpeg', '-n', '-hide_banner', '-nostdin', '-i', src]
    for flavor in self.flavors:
      if chapters is not None:
        cmd += ['-i', chapters, '-map_metadata', '1']
      codec = flavor['codec']
      dst = flavor['dst']
      cmd += ['-c:v', codec]
      cmd += ['-q:v', '0']
      cmd += ['-c:a', 'aac']
      cmd += ['-movflags', '+faststart']
      cmd += [dst]
    print(' '.join(cmd))
    
    ffmpeg = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    dur = 0
    while ffmpeg.poll() == None:
      l = ffmpeg.stdout.readline()
      dur_m = re.search(r'.*?Duration: (.*?)\.', l)
      fps_m = re.search(r'.*?fps= *(\d+).*?time= *([0-9:]+).*?speed= *([0-9\.]+)', l)
      if fps_m != None:
        fps = fps_m.group(1)
        t = fps_m.group(2)
        speed = fps_m.group(3)
        ts = datetime.strptime(t, "%H:%M:%S")
        ts = (ts - datetime(1900, 1, 1)).total_seconds()
        print(f'\r {ts}/{dur}: {src} ({fps}fps - x{speed})', end='')
        self.sub.config(text=f'Transcoding {ts}/{dur}: {path.basename(src)} ({fps}fps - x{speed})')
        if dur > 0:
          self.prog.config(value=round((ts*100)/dur))
      elif dur_m != None and dur == 0:
        t = dur_m.group(1)
        ts = datetime.strptime(t, "%H:%M:%S")
        dur = (ts - datetime(1900, 1, 1)).total_seconds()
    print('Done')
    self.sub.pack_forget()
    self.prog.pack_forget()
    if chapters is not None:
      remove(chapters)

if __name__ == '__main__':
  trans = Transcoder(codecs=['h264', 'h265'])
  trans.transcode()