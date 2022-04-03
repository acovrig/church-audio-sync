from cgitb import text
import os
import re
import sys
import glob
from threading import Thread
import subprocess
from time import sleep
from subprocess import Popen
import tkinter as tk
import tkinter.ttk as ttk

from pkg_resources import SOURCE_DIST
from uploader import Uploader
from datetime import date, datetime

SOURCE_BASE='C:\\Users\\acovrig\\Documents'
ARCHIVE_BASE='R:'
SIKULI_PATH='C:\\src\\sikulixide-2.0.5.jar'
SIKULI_SCRIPT_PATH='C:\\Users\\acovrig\\Documents\\tmp.sikuli'
# ZIP_PATH='C:\\Program Files\\7-Zip\\7zG.exe'
ZIP_PATH='C:\\Program Files\\7-Zip\\7z.exe'

SFTP_HOST = '192.168.5.76'
SFTP_PORT = 22
SFTP_USER = 'acovrig'
SFTP_KEY = 'C:\\Users\\acovrig\\.ssh\\id_rsa'
UPLOAD_DIR = '/mnt/user/projects/tmp'

class Automation(tk.Tk):
  def __init__(self, **kwargs):
    self.should_quit = False
    self.tc = 0
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
    self.should_quit = True
    sys.exit()

  def is_running(self, name):
    return (name in os.popen(f"tasklist /fi \"IMAGENAME eq {name}\"").read())

  def main_thread(self):
    t = Thread(target=self.close_apps)
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
    if self.is_running('voicemeeter8x64.exe'):
      self.header.config(text='Closing Voice Meeter')
      print('VoiceMeeter')
      os.system(f"taskkill /im \"voicemeeter8x64.exe\"")
      while self.is_running('voicemeeter8x64.exe'):
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
    #   os.system(f"taskkill /im \"chrome.exe\"")
    #   while self.is_running('chrome.exe'):
    #     sleep(0.5)
        
    i += 1
    self.prog['value'] = cnt * i
    if self.is_running('Waveform 11 (64-bit).exe'):
      self.header.config(text='Closing Waveform')
      print('Waveform')
      # os.system(f"taskkill /im \"Waveform 11 (64-bit).exe\"")
      while self.is_running('Waveform 11 (64-bit).exe'):
        sleep(0.5)

    self.sikuli.terminate()
    self.sub.pack_forget()
    self.prog.pack_forget()
    self.zip()

  def zip(self):
    self.header.config(text='Archiving Recording')
    if os.path.exists(f"{ARCHIVE_BASE}\\del3.7z"):
      os.unlink(f"{ARCHIVE_BASE}\\del3.7z")
    date = datetime.now().strftime(r'%Y-%m-%d')
    fn = glob.glob(f'{SOURCE_BASE}\\{date}*')
    if len(fn) < 1:
      self.win.quit()
    for f in fn:
      self.tc += 1
      t = Thread(target=self.zip_thread, args=(os.path.basename(f),))
      t.start()

  def zip_thread(self, fn):
    if not os.path.exists(f'{ARCHIVE_BASE}\\{fn}.7z'):
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
        # f"E:\\church\\audio\\{fn}.7z",
        # f"{SOURCE_BASE}\\{fn}"
        f"{ARCHIVE_BASE}\\{fn}.7z",
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

    self.upload(f'{fn}.7z')

  def upload(self, fn):
    print('Upload')
    self.header.config(text='Uploading to backup server')
    sub = tk.Label(text="")
    prog = ttk.Progressbar(length=300)
    prog.pack(expand=True)
    sub.pack()
    t1 = Thread(target=self.uploader, args=(fn, sub, prog))
    t1.start()

  def uploader(self, fn, sub, prog):
    config = {
      'sftp_host': SFTP_HOST,
      'sftp_port': SFTP_PORT,
      'sftp_user': SFTP_USER,
      'sftp_key': SFTP_KEY,
      'upload_dir': UPLOAD_DIR,
      'archive_base': ARCHIVE_BASE,
    }
    up = Uploader(fn, config, sub, prog, self.done)
    up.upload()

  def done(self):
    self.tc -= 1
    if self.tc < 1:
      print('All is done - do the shutdown here')
      self.win.quit()

app = Automation()
app.win.mainloop()