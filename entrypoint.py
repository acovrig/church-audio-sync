import autosub, glob, re, shutil, os, sys, getopt, subprocess, signal

from automation import Automation
from bulletin_db import BulletinDB
from config import Config
from sync_audio import SyncAudio

class ChurchVideo():
  def __init__(self):
    self.config = Config()
    self.get_opts()

  def print_help(self):
    print('Usage: [-d (--date)] [-s (--dry_run)] [-o (--offset) offset] [-f (--force_30)] [-i (--include_audio)] [-4 (--h264)] [-5 (--hevc)]')
    print('-d --date => date to process (in YYYY-MM-DD)')
    print('-4 --h264 => Only process H.264 (mp4 video)')
    print('-5 --hevc => Only process HEVC (mkv package)')
    print('-s --dry_run => generate the ffmpeg command but not execute it')
    print('-f --force_30 => Offset audio sync test by 30min')
    print('-i --include_audio => include all audio files and not detect volume to determine if the audio file is empty or not')
    print('-o --offset => Offset (seconds) between audio and video')

  def get_opts(self):
    try:
      opts, _ = getopt.getopt(sys.argv[1:],"ifo:p:45sd:v:a:",["date=", "offset=", "video=", "audio=", "force_30", "pdf_dir", "dry_run", "include_audio", "h264", "h265"])
    except getopt.GetoptError:
      self.print_help()
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
        self.print_help()
        sys.exit()
      elif opt in ("-d", "--date"):
        self.config.date = arg
        self.config.set_date(arg)
      elif opt in ("-v", "--video"):
        self.config.video = arg
      elif opt in ("-a", "--audio"):
        self.config.audio = arg
      elif opt in ("-4", "--h264"):
        self.config.h264 = True
      elif opt in ("-5", "--hevc"):
        self.config.hevc = True
      elif opt in ("-o", "--offset"):
        try:
          self.config.offset = float(arg)
        except:
          print(f'WARNING: Unable to parse {arg} as a float, ignoring offset')
          pass
      elif opt in ("-p", "--pdfs"):
        self.config.pdf_dir = arg
      elif opt in ("-s", "--dry_run"): # s for skip
        self.config.dry_run = True
      elif opt in ("-f", "--force_30"): 
        self.config.force_30 = True
      elif opt in ("-i", "--include_audio"): 
        self.config.skip_voldetect = True

    # If neither H264 or HEVC are specified, run both
    # to run neither, pass `-d` for a dry_run.
    if self.config.h264 == False and self.config.hevc == False:
      self.config.h264 = self.config.hevc = True
    if not self.config.h264:
      self.config.output_264 = None
    if not self.config.hevc:
      self.config.output = None

    if self.config.video == None:
      for _root, _dirs, files in os.walk(self.config.vid_base):
        for f in files:
          if re.match(f"^{self.config.date}.*(?:mp4|mkv)", f.lower()) != None:
            self.config.video = os.path.abspath(os.path.join(self.config.vid_base, f))
            # break # Removed the break to find the last file that matches (most recent)

    if self.config.audio == None:
      for _root, dirs, _files in os.walk(self.config.source_base):
        for f in dirs:
          if f.lower().startswith(self.config.date):
            self.config.audio = os.path.abspath(os.path.join(self.config.source_base, f, 'Recorded'))
            # break # Removed the break to find the last file that matches (most recent)

    if self.config.video == None:
      print(f'ERROR: Unable to locate video file (for {self.config.date})\n')
      self.print_help()
      sys.exit(2)

    if self.config.audio == None:
      print(f'ERROR: Unable to locate audio files (for {self.config.date})')
    
    self.config.video_base = re.sub(r"\..{3}$", '', self.config.video)

    srt = f'{self.config.video_base}.srt'
    if not os.path.exists(srt):
      srt = f'{self.config.video}.srt'
    if not os.path.exists(srt):
      srt = f'{os.path.join(self.config.vid_base, self.config.date)}.srt'
    if os.path.exists(srt):
      self.config.srt_file = srt

    chapters = f'{self.config.video_base}.chapters'
    if not os.path.exists(chapters):
      chapters = f'{self.config.video}.chapters'
    if not os.path.exists(chapters):
      chapters = f'{os.path.join(self.config.vid_base, self.config.date)}.chapters'
    if os.path.exists(chapters):
      self.config.chapters_file = chapters

    pdf = f'{self.config.video_base}.pdf'
    if not os.path.exists(pdf):
      pdf = f'{os.path.join(self.config.vid_base, self.config.date)}.pdf'
    if not os.path.exists(pdf):
      pdf = f'{os.path.join(self.config.source_base, self.config.date)}.pdf'
    if os.path.exists(pdf):
      self.config.pdf_file = pdf

    self.find_additions()

  def find_additions(self):
    if self.config.srt_file == None:
      print('Generating subtitles:')
      autosub.generate_subtitles(source_path=self.config.video, output=f"{self.config.video_base}.srt")
      self.config.srt_file = f'{self.config.video_base}.srt'
      print('')

    if self.config.pdf_file == None:
      self.fetch_pdf()

    if self.config.chapters_file == None:
      try:
        bulletin = BulletinDB()
        bulletin = bulletin.get_date(self.config.date)
        Automation().write_chapters(self.config.date, self.config.chapters_file, bulletin)
      except:
        self.config.chapters_file = None
        pass

  def fetch_pdf(self):
    print(f'Fetch PDF for {self.config.date}')

if __name__ == '__main__':
  vid = ChurchVideo()

  print(f'Input video: {vid.config.video}')
  print(f'Input audio dir: {vid.config.audio}')
  print(f'Input chapters: {vid.config.chapters_file}')
  print(f'Input subtitles: {vid.config.srt_file}')
  print(f'Input pdf: {vid.config.pdf_file}')
  print(f'Output HEVC: {vid.config.output}')
  print(f'Output H.264: {vid.config.output_264}')
  if vid.config.dry_run:
    print('DRY RUN, not running ffmpeg, only generate command')

  # print(vid.config)

  sync = SyncAudio(vid.config)
  sync.perform_sync()

  # auto = Automation()
  # auto.close_apps()
  # auto.zip()
  # auto.transcode()
