import os
import re
import shutil
import sys
import glob
from threading import Thread
import subprocess
from subprocess import Popen
from time import sleep
import tkinter as tk
import tkinter.ttk as ttk
from dotenv import load_dotenv

from uploader import Uploader
from transcoder import Transcoder
from datetime import datetime

DATE_OVERRIDE=None
DATE_OVERRIDE='2022-04-16'

load_dotenv()

SOURCE_BASE = os.getenv('SOURCE_BASE')
VID_BASE = os.getenv('VID_BASE')
ARCHIVE_AUDIO_BASE = os.getenv('ARCHIVE_AUDIO_BASE')
ARCHIVE_VIDEO_BASE = os.getenv('ARCHIVE_VIDEO_BASE')
SIKULI_PATH = os.getenv('SIKULI_PATH')
SIKULI_SCRIPT_PATH = os.getenv('SIKULI_SCRIPT_PATH')
ZIP_PATH = os.getenv('ZIP_PATH')

SFTP_BACKUP = {
  'host': os.getenv('SFTP_BACKUP_HOST'),
  'port': os.getenv('SFTP_BACKUP_PORT'),
  'user': os.getenv('SFTP_BACKUP_USER'),
  'key': os.getenv('SFTP_BACKUP_KEY'),
  'dir': os.getenv('SFTP_BACKUP_DIR'),
}
SFTP_DVD = {
  'host': os.getenv('SFTP_DVD_HOST'),
  'port': os.getenv('SFTP_DVD_PORT'),
  'user': os.getenv('SFTP_DVD_USER'),
  'key': os.getenv('SFTP_DVD_KEY'),
  'dir': os.getenv('SFTP_DVD_DIR'),
}

class Automation(tk.Tk):
  def __init__(self, **kwargs):
    self.tc = 0
    self.threads = []
    self.win = tk.Tk()
    self.win.title('Shutting Down')

    window_width = 400
    window_height = 200
    screen_width = self.win.winfo_screenwidth()
    screen_height = self.win.winfo_screenheight()
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
    self.win.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    self.win.resizable(False, False)
    self.win.attributes('-topmost', 1)
    self.win.attributes('-alpha', 0.9)
    self.win.protocol('WM_DELETE_WINDOW', self.close)

    self.header = tk.Label(text='')
    self.prog = ttk.Progressbar(self.win, length=300)

    self.sub = tk.Label(text='')
    self.prog2 = ttk.Progressbar(self.win, length=300)
    self.sub2 = tk.Label(text='')

    self.header.pack()
    self.prog.pack(expand=True)

    self.main_thread()

  def close(self):
    sys.exit()

  def is_running(self, name):
    return (name in os.popen(f"tasklist /fi \"IMAGENAME eq {name}\"").read())

  def main_thread(self):
    t = Thread(target=self.close_apps)
    self.threads.append(t)
    t.start()

  def close_apps(self):
    print('Closing Things')
    self.header.config(text='Closing Things')
    cnt = 5
    i = 0
    self.sikuli = Popen([
      "java",
      "-jar",
      SIKULI_PATH,
      "-r",
      SIKULI_SCRIPT_PATH
    ])
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('voicemeeterpro.exe'):
      self.header.config(text='Closing Voice Meeter')
      print('VoiceMeeter')
      os.system(f"taskkill /im \"voicemeeterpro.exe\"")
      while self.is_running('voicemeeterpro.exe'):
        sleep(0.5)
        
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('obs64.exe'):
      self.header.config(text='Closing OBS')
      print('OBS')
      os.system(f"taskkill /im \"obs64.exe\"")
      while self.is_running('obs64.exe'):
        sleep(0.5)
        
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('chrome.exe'):
      self.header.config(text='Closing Chrome')
      print('Chrome')
      os.system(f"taskkill /im \"chrome.exe\"")
      while self.is_running('chrome.exe'):
        sleep(0.5)
        
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('Waveform 11 (64-bit).exe'):
      self.header.config(text='Closing Waveform')
      print('Waveform')
      # os.system(f"taskkill /im \"Waveform 11 (64-bit).exe\"")
      while self.is_running('Waveform 11 (64-bit).exe'):
        sleep(0.5)
        
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('Livestream Studio Core.exe'):
      self.header.config(text='Closing Livestream')
      print('Livestream')
      # os.system(f"taskkill /im \"Livestream Studio Core.exe\"")
      while self.is_running('Livestream Studio Core.exe'):
        sleep(0.5)

    self.sikuli.terminate()
    self.sub.pack_forget()
    self.prog.pack_forget()
    self.zip()
    self.transcode()
    if self.tc < 1:
      self.header.config(text='Error, no file found, wrong date?')
      print('No file found.')
      self.win.quit()

  def zip(self):
    self.header.config(text='Archiving Recording')
    date = DATE_OVERRIDE if DATE_OVERRIDE != None else datetime.now().strftime(r'%Y-%m-%d')
    fn = glob.glob(f'{SOURCE_BASE}\\{date}*')
    for f in fn:
      self.tc += 1
      t = Thread(target=self.zip_thread, args=(os.path.basename(f),))
      self.threads.append(t)
      t.start()

  def zip_thread(self, fn):
    if not os.path.exists(f'{ARCHIVE_AUDIO_BASE}\\{fn}.7z'):
      prog = ttk.Progressbar(length=300)
      sub = tk.Label(text=f'Zipping {fn}')
      prog.pack()
      sub.pack()
      print(f'Starting zip {fn}')
      cmd = Popen([
        ZIP_PATH,
        "a",
        "-t7z",
        # "-sdel",
        "-bsp1",
        "-mx9",
        f"{ARCHIVE_AUDIO_BASE}\\{fn}.7z",
        f"{SOURCE_BASE}\\{fn}"
      ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
      while cmd.poll() == None:
        m = re.search(r"^ *([0-9]+)% [0-9]+ \+ (.*$)", cmd.stdout.readline())
        if m != None:
          print(m.group(0))
          prog['value'] = m.group(1)
          sub.config(text=m.group(2))
      print('Done')
      sub.pack_forget()
      prog.pack_forget()

    self.upload(SFTP_BACKUP, f'{ARCHIVE_AUDIO_BASE}\\{fn}.7z', 'audio')

  def transcode(self):
    date = DATE_OVERRIDE if DATE_OVERRIDE != None else datetime.now().strftime(r'%Y-%m-%d')
    fn = glob.glob(f'{VID_BASE}\\{date}*')
    for f in fn:
      self.tc += 3
      sub = tk.Label(text='')
      prog = ttk.Progressbar(length=300)
      prog.pack(expand=True)
      sub.pack()
      t = Thread(target=self.transcode_thread, args=(os.path.basename(f), sub, prog))
      self.threads.append(t)
      t.start()

  def transcode_thread(self, f, sub, prog):
    date = f[0:10]
    if not os.path.exists(f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw'):
      os.makedirs(f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw')
    trans = Transcoder(flavors=[
      {'codec': 'libx264', 'dst': f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4'},
      {'codec': 'libx265', 'dst': f'{ARCHIVE_VIDEO_BASE}\\hevc\\{date}.mp4'}
    ], sub=sub, prog=prog)
    trans.transcode(src=f'{VID_BASE}\\{f}')
    print('Archive source video')
    shutil.move(f'{VID_BASE}\\{f}', f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw\\{f}')
    print('Archive source video: done')
    
    self.upload(SFTP_BACKUP, f'{ARCHIVE_VIDEO_BASE}\\hevc\\{date}.mp4', f'hevc')
    self.upload(SFTP_BACKUP, f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4', f'h264/{date}')
    self.upload(SFTP_DVD, f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4')

  def upload(self, config, src, dst = ''):
    print('Upload')
    self.header.config(text='Uploading to backup server')
    sub = tk.Label(text="")
    prog = ttk.Progressbar(length=300)
    prog.pack(expand=True)
    sub.pack()
    t = Thread(target=self.uploader, args=(config, src, dst, sub, prog))
    self.threads.append(t)
    t.start()

  def uploader(self, config, src, dst, sub, prog):
    up = Uploader(config, src, dst, sub, prog)
    up.upload()
    self.done()

  def done(self):
    self.tc -= 1
    if self.tc < 1:
      print('All is done - do the shutdown here')
      self.win.destroy()

if __name__ == '__main__':
  if not os.path.exists('.env'):
    print('ENV file missing, please copy .env.sample to .env and modify as needed.')
    quit()
  app = Automation()
  app.win.mainloop()