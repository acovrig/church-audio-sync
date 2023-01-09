import glob, re, shutil, os, sys, getopt, subprocess
from dotenv import load_dotenv
from time import sleep

from uploader import Uploader
from transcoder import Transcoder
from datetime import datetime
from bulletin_db import BulletinDB

DATE_OVERRIDE=None
# DATE_OVERRIDE='2022-04-16'

class Automation():
  def is_running(self, name):
    return (name in os.popen(f"tasklist /fo csv /fi \"IMAGENAME eq {name}\"").read())

  def close_apps(self):
    print('Closing Things')
    cnt = 6
    i = 0
    sikuli = subprocess.Popen([
      "java",
      "-jar",
      SIKULI_PATH,
      "-r",
      SIKULI_SCRIPT_PATH
    ])
    i += 1
    print('VoiceMeeter')
    while self.is_running('voicemeeterpro.exe'):
      os.system(f"taskkill /im \"voicemeeterpro.exe\"")
      sleep(2)
        
    i += 1
    print('OBS')
    while self.is_running('obs64.exe'):
      os.system(f"taskkill /im \"obs64.exe\"")
      sleep(2)
        
    i += 1
    print('Chrome')
    while self.is_running('chrome.exe'):
      os.system(f"taskkill /im \"chrome.exe\"")
      sleep(2)
        
    i += 1
    print('X32')
    while self.is_running('X32-Edit.exe'):
      os.system(f"taskkill /im \"X32-Edit.exe\"")
      sleep(2)
        
    i += 1
    print('Waveform')
    while self.is_running('Waveform 11 (64-bit).exe'):
      # Closing waveform via sikuli
      os.system(f"java.exe -jar C:\src\sikulixide-2.0.5.jar -r C:\src\sikulix\CloseWaveform.sikuli\CloseWaveform.py")
      sleep(2)

  def zip(self):
    date = DATE_OVERRIDE if DATE_OVERRIDE != None else datetime.now().strftime(r'%Y-%m-%d')
    fn = glob.glob(f'{SOURCE_BASE}\\{date}*')
    for f in fn:
      if not os.path.exists(f'{ARCHIVE_AUDIO_BASE}\\{f}.7z'):
        print(f'Starting zip {f}')
        cmd = subprocess.Popen([
          ZIP_PATH,
          "a",
          "-t7z",
          # "-sdel",
          "-bsp1",
          "-mx9",
          f"{ARCHIVE_AUDIO_BASE}\\{f}.7z",
          f"{SOURCE_BASE}\\{f}"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        while cmd.poll() == None:
          m = re.search(r"^ *([0-9]+)% [0-9]+ \+ (.*$)", cmd.stdout.readline())
          if m != None:
            print(m.group(0))
        print('Done')

      Uploader(SFTP_BACKUP, f'{ARCHIVE_AUDIO_BASE}\\{f}.7z', 'audio')

  def write_chapters(self, date, chapt_fn, db):
    h, m, s = db[0]['ss'].split(':')
    dur = int(h) * 3600 + int(m) * 60 + int(s)
    chapters = f';FFMETADATA1\ntitle=Church {date}\n\n'
    chapters += "[CHAPTER]\n"
    chapters += "TIMEBASE=1/1000\n"
    chapters += f"START=0\n"
    chapters += f"END={dur * 1000}\n"
    chapters += f"title=Welcome\n\n"
    for i, e in enumerate(db):
      print(e)
      try:
        end = db[i + 1]
      except:
        break

      h, m, s = e['ss'].split(':')
      ss = int(h) * 3600 + int(m) * 60 + int(s)
      h, m, s = end['ss'].split(':')
      dur = int(h) * 3600 + int(m) * 60 + int(s)
      chapters += "[CHAPTER]\n"
      chapters += "TIMEBASE=1/1000\n"
      chapters += f"START={ss * 1000}\n"
      chapters += f"END={dur * 1000}\n"
      chapters += f"title={e['name']}\n\n"

    print(f'Writing {chapt_fn}:\n\n{chapters}')
    with open(chapt_fn, 'w') as f:
      f.write(chapters)

  def transcode(self):
    date = DATE_OVERRIDE if DATE_OVERRIDE != None else datetime.now().strftime(r'%Y-%m-%d')
    fn = glob.glob(f'{VID_BASE}\\{date}*')
    if len(fn) < 1:
      print('ERROR: no files found to transcode')
    for f in fn:
      chapt_fn = os.path.join(os.path.dirname(f), f'{date}.chapters')
      db = BulletinDB()
      db = db.get_date()
      self.write_chapters(date, chapt_fn, db)

      f = os.path.basename(f)
      date = f[0:10]
      if not os.path.exists(f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw'):
        os.makedirs(f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw')
      trans = Transcoder(flavors=[
        {'codec': 'libx264', 'dst': f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4'},
        {'codec': 'libx265', 'dst': f'{ARCHIVE_VIDEO_BASE}\\hevc\\{date}.mp4'}
      ])
      trans.transcode(src=f'{VID_BASE}\\{f}', chapters=chapt_fn)
      print('Archive source video')
      shutil.move(f'{VID_BASE}\\{f}', f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\raw\\{f}')
      print('Archive source video: done')
      
      Uploader(SFTP_BACKUP, f'{ARCHIVE_VIDEO_BASE}\\hevc\\{date}.mp4', 'hevc')
      Uploader(SFTP_BACKUP, f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4', f'h264/{date}')
      Uploader(SFTP_DVD, f'{ARCHIVE_VIDEO_BASE}\\h264\\{date}\\{date}.mp4')

if __name__ == '__main__':
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

  if not os.path.exists('.env'):
    print('ENV file missing, please copy .env.sample to .env and modify as needed.')
    quit()

  app = Automation()
  app.mainloop()