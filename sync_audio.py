import autosub, glob, re, shutil, os, sys, getopt, subprocess
from dotenv import load_dotenv
from datetime import datetime

from automation import Automation
from bulletin_db import BulletinDB

class SyncAudio():
  def __init__(self, config):
    self.config = config
    self.rate = 48000

  def build_main_cmd(self):
    cmd=['ffmpeg', '-hide_banner', '-n']
    if self.config.audio != None and self.config.offset == None:
      self.config.offset = self.find_offset()

    audio_count = 0
    print("\nGetting audio files (by volume):")
    if self.config.audio != None:
      for _root, _dirs, files in os.walk(self.config.audio):
        audio_files = list(filter(self.filter_file, files))
    else:
      print('WARNING: Skipping audio (None)')
      audio_files = []

    if self.config.hevc:
      for f in audio_files:
        audio_count += 1
        layout = 'mono'
        if 'talkback_take' in f.lower() or 'pc_take' in f.lower():
          layout = 'stereo'
        
        # aux used to be stereo, but became mono
        if 'aux_take' not in f.lower():
          cmd += ['-channel_layout', layout]

        cmd += ['-i', os.path.join(self.config.audio, f)]
        # TODO: Find this rate var def
        if self.rate != 48000:
          cmd += ['-af', 'aresample=resampler=soxr', '-ar', '48000']

        # make talkback mono
        if 'talkback_take' in f.lower():
          cmd += ['-ac', '1']

      if self.config.offset != None:
        cmd += ["-itsoffset", str(self.config.offset)]
      cmd += ['-channel_layout', 'stereo', '-i', self.config.video]

      if self.config.chapters_file != None:
        if self.config.offset > 0:
          self.fix_chapters(self.config.offset)

      if self.config.srt_file != None:
        cmd += ["-itsoffset", str(self.config.offset)]
        cmd += ["-i", self.config.srt_file]

      if self.config.chapters_file != None:
        audio_count += 1 # So the srt map # below works (and the map_metadata)
        cmd += ["-i", self.config.chapters_file]
        cmd += ["-map_metadata", str(audio_count + 1)]

      cmd += ["-map", f'{audio_count - 1}:v']
      cmd += ["-map", f'{audio_count - 1}:a']
      if self.config.srt_file != None:
        cmd += ["-map", f"{audio_count}:0"]
      for i, f in enumerate(audio_files):
        cmd += ["-map", str(i)]

      cmd += [f'-metadata:s:a:0', 'title=AV']
      cmd += [f'-disposition:a:0', 'default']
      for i, f in enumerate(audio_files):
        try:
          title=re.search(r"_([a-zA-Z0-9 ]*?)_Take", f).group(1)
        except:
          title = f
        cmd += [f'-metadata:s:a:{i+1}', f'title={title}']

        if self.config.pdf_file != None:
          cmd += ["-attach", self.config.pdf_file, "-metadata:s:t", "mimetype=application/pdf"]

      cmd += ["-b:a", "192k"]

      codec_cmd = ['ffprobe', '-v', 'error', '-of', 'default=noprint_wrappers=1:nokey=1', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', self.config.video]
      print('Video codec: ', end='')
      try:
        codec, err = subprocess.Popen(codec_cmd, stdout=subprocess.PIPE).communicate()
        codec = codec.decode('utf-8').replace("\n", "")
        print(codec)
        if codec == 'hevc':
          cmd += ["-c:v", "copy"]
        else:
          cmd += ["-c:v", "libx265"]
      except:
        cmd += ["-c:v", "libx265"]
        pass

      cmd += ["-c:a", "aac"]
      if self.config.srt_file != None:
        cmd += ["-c:s", "ass"]
      cmd += [self.config.output]

    if self.config.h264:
      if self.config.hevc:
        cmd += ["-map", f'{audio_count - 1}:v']
        cmd += ["-map", f'{audio_count - 1}:a']
        if self.config.chapters_file != None:
          cmd += ["-map_metadata", str(audio_count)]
      else:
        cmd += ['-i', self.config.video]
        if self.config.chapters_file != None:
          cmd += ['-i', self.config.chapters_file]
          cmd += ['-map_metadata', '1']
      cmd += ['-c:v', 'libx264']
      cmd += ['-c:a', 'aac']
      cmd += ['-movflags', '+faststart']
      cmd += [self.config.output_264]

    return cmd

  def filter_file(self, f):
    if re.match(r".*wav$", f.lower()) == None:
      return False
    if '_hearing_take' in f.lower():
      return False
    if '_idk_take' in f.lower():
      return False
    if '_monitors_take' in f.lower():
      return False
    if '_pulpit left_take' in f.lower():
      return False
    if '_pulpit right_take' in f.lower():
      return False
    if 'stream_take' in f.lower():
      return True
    if 'piano_take' in f.lower():
      return True
    if 'prayer_take' in f.lower():
      return True
    if 'talkback_take' in f.lower():
      return True

    try:
      title=re.search(r"_([a-zA-Z0-9 ]*?)_Take", f).group(1)
    except:
      title = f

    sys.stdout.write(f"\tGetting volume of {title}: ")
    sys.stdout.flush()

    if self.config.skip_voldetect:
      print('skip_voldetect=True (including)')
      return True

    try:
      cmd = ['ffmpeg', '-hide_banner', '-i', os.path.join(self.config.audio, f), '-af', 'volumedetect', '-f', 'null', os.path.join(self.config.audio, f'{f}.voldetect')]
      _, volume = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
      volume = re.search(r"max_volume: (.*?) dB", str(volume)).group(1)
      volume = float(volume)
      print(volume, end='')
      if volume < -50:
        print(' (ignore)')
        return False
    except:
      print(' (include)')
      return True
    print(' (include)')
    return True

  def find_sync_file(self, fn = 'stream'):
    sync_file = None
    for _root, _dirs, files in os.walk(self.config.audio):
      for f in files:
        if fn.lower() in f.lower():
          sync_file = os.path.join(self.config.audio, f)

          # Was this input actually recorded?
          if fn.lower() != 'stream':
            try:
              sys.stdout.write(f'Getting volume for sync {fn}: ')
              sys.stdout.flush()
              cmd = ['ffmpeg', '-hide_banner', '-i', sync_file, '-af', 'volumedetect', '-f', 'null', os.path.join(self.config.audio, f'{f}.voldetect')]
              _, volume = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
              volume = re.search(r"max_volume: (.*?) dB", str(volume)).group(1)
              volume = float(volume)
              print(volume)
              if volume < -50:
                sync_file = None
            except:
              pass
          if os.path.exists(os.path.join(self.config.audio, f'{f}.voldetect')):
            os.remove(os.path.join(self.config.audio, f'{f}.voldetect'))

          if sync_file != None:
            cmd = [
              'ffprobe',
              '-v', 'error',
              '-of', 'default=noprint_wrappers=1:nokey=1',
              '-show_entries', 'stream=sample_rate',
              os.path.join(self.config.audio, f)
            ]
            print('Sample rate: ', end='')
            try:
              rate, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
              self.rate = int(rate)
              print(self.rate)
              if self.rate != 48000:
                if not os.path.exists(os.path.join(self.config.audio, f'{f}.sync.aac')):
                  cmd = [
                    'ffmpeg',
                    '-n',
                    '-v', 'warning',
                    '-stats',
                    '-channel_layout', 'mono',
                    '-i', os.path.join(self.config.audio, f),
                    '-af', 'aresample=resampler=soxr',
                    '-ar', '48000',
                    os.path.join(self.config.audio, f'{f}.sync.aac')
                  ]
                  print('Converting rate: ', end='')
                  print(subprocess.list2cmdline(cmd))
                  process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                  for c in iter(lambda: process.stdout.read(1), b""):
                    sys.stdout.write(c)
                sync_file = os.path.join(self.config.audio, f'{f}.sync.aac')
                break
            except:
              print('ERROR: Unable to determine sample rate')
              break
    if sync_file == None:
      if fn == 'stream':
        print('WARNING: Failed to get sync_file from stream, trying monitors')
        sync_file = self.find_sync_file('monitors')
      elif fn == 'monitors':
        print('WARNING: Failed to get sync_file from monitors, trying piano')
        sync_file = self.find_sync_file('piano')
      elif fn == 'piano':
        print('WARNING: Failed to get sync_file from piano, trying lapel')
        sync_file = self.find_sync_file('lapel')
      elif fn == 'lapel':
        print('WARNING: Failed to get sync_file from lapel, trying prayer')
        sync_file = self.find_sync_file('prayer')
    return sync_file

  def find_offset(self, fn = 'stream'):
    print("\nGetting audio offset:\n\tFinding sync file")

    sync_file = self.find_sync_file(fn)
    print(f'\tSync file: {sync_file}')

    if sync_file == None:
      print('ERROR, no sync_file specified, skipping offset calculation')
      offset = 0
      return offset

    sys.stdout.write('Calculating offset: ')
    sys.stdout.flush()
    offset = b''
    if not self.config.force_30:
      offset, _ = subprocess.Popen(['./compute-sound-offset.sh', self.config.video, sync_file, '900'], stdout=subprocess.PIPE).communicate()
    if offset == b'':
      print("Unable to determine offset, trying skip: ")
      cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-ss', str(30*60), '-i', sync_file, '-t', '1000', f'{sync_file}.sync30.aac']
      subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
      sync_file = f'{sync_file}.sync30.aac'
      offset, _ = subprocess.Popen(['./compute-sound-offset.sh', self.config.video, sync_file, '900'], stdout=subprocess.PIPE).communicate()
      if offset != b'':
        offset = float(offset) + (30 * 60)

    for root, dirs, files in os.walk(self.config.audio):
      for f in files:
        if re.match(r".*aac$", f.lower()) != None:
          print(f'REMOVE {f}')
          os.remove(os.path.join(self.config.audio, f))

    if offset == b'':
      if 'stream' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying monitors')
        offset = self.find_offset('monitors')
      elif 'monitors' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying piano')
        offset = self.find_offset('piano')
      elif 'piano' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying lapel')
        offset = self.find_offset('lapel')
      elif 'lapel' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying prayer')
        offset = self.find_offset('prayer')
      else:
        print("ERROR: Unable to determine offset")
        offset = None

    if offset != None:
      offset = float(offset)

    print(offset)
    return offset

  def fix_chapters(self, offset):
    print(f"\nFix chapters with offset {offset} - {self.config.chapters_file}")

    with open(self.config.chapters_file, 'r') as f:
      try:
        f.readlines()
      except:
        print('Unable to read captions, converting:')
        try:
          with open(self.config.chapters_file, 'r', encoding='cp1252') as inf:
            with open(f'{self.config.chapters_file}.utf8', 'w', encoding='utf-8') as outf:
              for l in inf:
                outf.write(l)
          os.rename(f'{self.config.chapters_file}.utf8', self.config.chapters_file)
        except:
          print('Unable to convert captions locally, trying iconv:')
          cmd = ['iconv', '-f', 'windows-1252', self.config.chapters_file, '-t', 'utf-8', '-o', f'{self.config.chapters_file}.utf8']
          # print(subprocess.list2cmdline(cmd))
          try:
            subprocess.Popen(cmd).communicate()
          except:
            print(f'WARNING: Unable to decode captions ({self.config.chapters_file}).')
            self.config.chapters_file = None
            return False
          if os.path.exists(f'{self.config.chapters_file}.utf8'):
            os.rename(f'{self.config.chapters_file}.utf8', self.config.chapters_file)

    main_title = None
    chapters_arr = []
    with open(self.config.chapters_file, 'r') as f:
      chapt = None
      for l in f.readlines():
        l = l.replace("\n", "")
        if '[chapter]' in l.lower():
          if chapt != None:
            chapters_arr.append(chapt)
          chapt={}

        if l.lower().startswith('title='):
          if chapt == None:
            try:
              main_title=re.search(r"title=(.*)$", l, re.IGNORECASE).group(1)
            except:
              next
          else:
            try:
              title=re.search(r"title=(.*)$", l, re.IGNORECASE).group(1)
              chapt['title'] = title
            except:
              next

        elif chapt != None and l.lower().startswith('start='):
          try:
            start=re.search(r"start=(.*)$", l, re.IGNORECASE).group(1)
            chapt['start'] = int(start) / 1000
          except:
            next

        elif chapt != None and l.lower().startswith('end='):
          try:
            end=re.search(r"end=(.*)$", l, re.IGNORECASE).group(1)
            chapt['end'] = int(end) / 1000
          except:
            next

    self.config.chapters_file = f'{self.config.chapters_file.replace(".chapters", "")}.offset.chapters'

    new_chapters = f';FFMETADATA1\ntitle={main_title}\n\n'
    for chapt in chapters_arr:
      new_chapters += "[CHAPTER]\n"
      new_chapters += "TIMEBASE=1/1000\n"
      new_chapters += f"START={int(chapt['start'] + offset) * 1000}\n"
      new_chapters += f"END={int(chapt['end'] + offset) * 1000}\n"
      new_chapters += f"title={chapt['title']}\n\n"

    print(f'Writing {self.config.chapters_file}:')
    with open(self.config.chapters_file, 'w') as f:
      f.write(new_chapters)

  def perform_sync(self):
    cmd = self.build_main_cmd()
    print(subprocess.list2cmdline(cmd))

    if self.config.output != None and os.path.exists(self.config.output) and os.stat(self.config.output).st_size == 0:
      os.remove(self.config.output)
    if self.config.output_264 != None and os.path.exists(self.config.output_264) and os.stat(self.config.output_264).st_size == 0:
      os.remove(self.config.output_264)

    if not self.config.dry_run:
      print('run cmd')
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
      for c in iter(lambda: process.stdout.read(1), b""):
        sys.stdout.write(c)

if __name__ == '__main__':
  from config import Config

  config = Config()
  sync = SyncAudio(config)
  sync.perform_sync()
