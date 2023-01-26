from dataclasses import dataclass
from dotenv import load_dotenv
import re, os
from datetime import datetime

@dataclass
class Config():
  date: str = datetime.now().strftime(r'%Y-%m-%d')
  video: str = None
  output: str = None
  output_264: str = None
  h264: bool = False
  hevc: bool = False
  video_base: str = None
  audio: str = None
  srt_file: str = None
  pdf_file: str = None
  chapters_file: str = None
  dry_run: bool = False
  skip_voldetect: bool = False
  offset: float = None
  force_30: bool = False

  def __post_init__(self):
    if os.path.exists('.env'):
      load_dotenv()
    else:
      print('WARNGIN: .evn file not found, using bare env')

    self.source_base = os.getenv('SOURCE_BASE')
    self.vid_base = os.getenv('VID_BASE')
    self.pdf_base = os.getenv('PDF_BASE')
    self.archive_audio_base = os.getenv('ARCHIVE_AUDIO_BASE')
    self.archive_video_base = os.getenv('ARCHIVE_VIDEO_BASE')
    self.sikuli_path = os.getenv('SIKULI_PATH')
    self.sikuli_script_path = os.getenv('SIKULI_SCRIPT_PATH')
    self.zip_path = os.getenv('ZIP_PATH')

    self.sftp_backup = {
      'host': os.getenv('SFTP_BACKUP_HOST'),
      'port': os.getenv('SFTP_BACKUP_PORT'),
      'user': os.getenv('SFTP_BACKUP_USER'),
      'key': os.getenv('SFTP_BACKUP_KEY'),
      'dir': os.getenv('SFTP_BACKUP_DIR'),
    }
    self.sftp_dvd = {
      'host': os.getenv('SFTP_DVD_HOST'),
      'port': os.getenv('SFTP_DVD_PORT'),
      'user': os.getenv('SFTP_DVD_USER'),
      'key': os.getenv('SFTP_DVD_KEY'),
      'dir': os.getenv('SFTP_DVD_DIR'),
    }

    self.set_date(self.date)

  def set_date(self, date):
    if date == None:
      date = self.date

    base264 = os.path.join(self.archive_video_base, 'h264', date)
    self.output = os.path.join(self.archive_video_base, 'hevc', f'{date}.mkv')
    self.output_264 = os.path.join(base264, f'{date}.mp4')
    if not os.path.exists(base264):
      os.makedirs(base264)

    pdf = os.path.abspath(os.path.join(self.pdf_base, f'{date}.pdf'))
    if os.path.exists(pdf):
      self.pdf_file = pdf

