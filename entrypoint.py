import sys, getopt, subprocess
from os import path, walk, remove
import re
import autosub

offset = None
skip_voldetect = False
# Uncomment this to skip calculating offset:
# offset = 473.291

# Set to true to not detect volume (therefore including almost all audio tracks)
# skip_voldetect = True



def print_help():
  print('Usage: -v <video file> [-d (--dry_run)] [-i (--include_audio)] [-a <audio dir>] [-c <chapters>] [-s <subtitles>] [-p <pdfs_dir] (-o <output> -2 <h.264 output>)')
  print('An output path is required either for HEVC [-o] or H.264 [-2]')
  print('--dry_run (-d) will generate the ffmpeg command but not execute it')
  print('--include_audio (-i) will include all audio files and not detect volume to determine if the audio file is empty or not')
  print('The audio dir is required, but will be guessed if not provided.')
  print('The chapters, subtitles, and pdfs_dir will be guessed unless provided')

def filter_file(f):
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

  sys.stdout.write(f'Getting volume of {title}: ')
  sys.stdout.flush()

  if skip_voldetect:
    print('skip_voldetect=True (including)')
    return True

  try:
    cmd = ['ffmpeg', '-hide_banner', '-i', path.join(audio, f), '-af', 'volumedetect', '-f', 'null', path.join(audio, f'{f}.voldetect')]
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

def find_sync_file():
  global sync_file, rate
  sync_file = None
  for root, dirs, files in walk(audio):
    for f in files:
      if "stream" in f.lower():
        sync_file = path.join(audio, f)
        cmd = ['ffprobe', '-v', 'error', '-of', 'default=noprint_wrappers=1:nokey=1', '-show_entries', 'stream=sample_rate', path.join(audio, f)]
        print('Sample rate: ', end='')
        try:
          rate, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
          rate = int(rate)
          print(rate)
          if rate != 48000:
            if not path.exists(path.join(audio, f'{f}.sync.aac')):
              cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-channel_layout', 'mono', '-i', path.join(audio, f), '-af', 'aresample=resampler=soxr', '-ar', '48000', path.join(audio, f'{f}.sync.aac')]
              print('Converting rate: ', end='')
              print(subprocess.list2cmdline(cmd))
              process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
              for c in iter(lambda: process.stdout.read(1), b""):
                sys.stdout.write(c)
            sync_file = path.join(audio, f'{f}.sync.aac')
            break
        except:
          print('ERROR: Unable to determine sample rate')
          break
  return sync_file

def get_opts():
  global video, audio, chapters, srt, pdfdir, output
  try:
    opts, args = getopt.getopt(sys.argv[1:],"hv:c:a:s:p:o:",["video=","chapters=", "audio_dir=", "subtitles=", "pdf_dir=", "output="])
  except getopt.GetoptError:
    print_help()
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      print_help()
      sys.exit()
    elif opt in ("-v", "--video"):
      video = arg
    elif opt in ("-c", "--chapters"):
      chapters = arg
    elif opt in ("-a", "--audio_dir"):
      audio = arg
    elif opt in ("-s", "--subtitles"):
      srt = arg
    elif opt in ("-p", "--pdfs"):
      pdfdir = arg
    elif opt in ("-o", "--output"): 
      output = arg

  if not path.exists(video):
    print(f'ERROR: {video} does not exist')
    sys.exit(2)
  if not path.exists(audio):
    print(f'ERROR: {audio} does not exist')
    sys.exit(2)

  find_additions()
  
  return video, audio, chapters, srt, pdfdir, output

def find_additions():
  global srt, pdfdir, chapters
  if srt == '':
    base = re.sub(r"\..{3}$", '', video)
    srt = f'{base}.srt'
    if not path.exists(srt):
      srt = f'{video}.srt'
      if not path.exists(srt):
        print('Generating subtitles:')
        autosub.generate_subtitles(source_path=video, output=f"{video}.srt")
  if pdfdir == '':
    pdfdir = path.abspath(path.join(path.dirname(video), '..', 'pdf'))
    if not path.exists(pdfdir):
      pdfdir = None
  if chapters == '':
    base = re.sub(r"\..{3}$", '', video)
    chapters = f'{base}.chapters'
    if not path.exists(chapters):
      chapters = None
  return srt, pdfdir, chapters

def find_offset():
  global offset, sync_file
  if offset == None:
    offset, err = subprocess.Popen(['/src/compute-sound-offset.sh', video, sync_file, '900'], stdout=subprocess.PIPE).communicate()
    if offset == b'':
      print("Unable to determine offset, trying skip: ")
      if path.exists(path.join(audio, f'{f}.sync.aac')):
        cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-ss', str(30*60), '-i', path.join(audio, f'{f}.sync.aac'), '-c', 'copy', path.join(audio, f'{f}.sync30.aac')]
      else:
        cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-ss', str(30*60), '-i', path.join(audio, f), path.join(audio, f'{f}.sync30.aac')]
      print('Jumping 30min: ', end='')
      print(subprocess.list2cmdline(cmd))
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
      for c in iter(lambda: process.stdout.read(1), b""):
        sys.stdout.write(c)
      sync_file = path.join(audio, f'{f}.sync30.aac')
      offset, err = subprocess.Popen(['/src/compute-sound-offset.sh', video, sync_file, '900'], stdout=subprocess.PIPE).communicate()
    if offset == b'':
      print("Unable to determine offset, please manually enter (in seconds): ", end="")
      sys.exit(2)
  offset = float(offset)

  for root, dirs, files in walk(audio):
    for f in files:
      if re.match(r".*stream.*aac$", f.lower()) != None:
        print(f'REMOVE {f}')
        remove(path.join(audio, f))
  return offset

video = chapters = audio = srt = pdfdir = output = ''
rate = 0
get_opts()

print(f'Input video: {video}')
print(f'Input audio dir: {audio}')
print(f'Input chapters: {chapters}')
print(f'Input subtitles: {srt}')
print(f'Input pdfs dir: {pdfdir}')
print(f'Output: {output}')

if chapters != None and not path.exists(chapters):
  print(f'ERROR: {chapters} does not exist')
  sys.exit(2)

find_sync_file()
print(f'Sync file: {sync_file}')

find_offset()
print(f'Offset: {offset}')

if path.exists(output):
  print(f'ERROR: {output} exists, not overwriting')

cmd=['ffmpeg', '-hide_banner', '-n']
audio_count = 0
for root, dirs, files in walk(audio):
  audio_files = list(filter(filter_file, files))

for f in audio_files:
  audio_count += 1
  layout = 'mono'
  if 'talkback_take' in f.lower() or 'pc_take' in f.lower():
    layout = 'stereo'
  
  # aux used to be stereo, but became mono
  if 'aux_take' not in f.lower():
    cmd += ['-channel_layout', layout]

  cmd += ['-i', path.join(audio, f)]
  if rate != 48000:
    cmd += ['-af', 'aresample=resampler=soxr', '-ar', '48000']

  # make talkback mono
  if 'talkback_take' in f.lower():
    cmd += ['-ac', '1']

cmd += ["-itsoffset", str(offset)]
cmd += ['-channel_layout', 'stereo', '-i', video]
if srt != None:
  cmd += ["-itsoffset", str(offset)]
  cmd += ["-i", srt]
if chapters != None:
  cmd += ["-itsoffset", str(offset)]
  cmd += ["-i", chapters]
cmd += ["-b:a", "192k"]
cmd += ["-map_metadata", "1"]

cmd += ["-map", f'{audio_count}:v']
cmd += ["-map", f'{audio_count}:a']
if str != None:
  cmd += ["-map", f"{audio_count + 1}:0"]
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

try:
  date = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})", video).group(1)
  pdf = path.join(pdfdir, f"{date}.pdf")
  print(f'PDF: {pdf}: ', end='')
  if path.exists(pdf):
    print('exists')
    cmd += ["-attach", pdf, "-metadata:s:t", "mimetype=application/pdf"]
  else:
    print('does not exist')
except:
  print(f'Filed to get PDF from {video}')
  next

cmd += ["-af", "aresample=resampler=soxr", "-ar", "48000"]

codec_cmd = ['ffprobe', '-v', 'error', '-of', 'default=noprint_wrappers=1:nokey=1', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', video]
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
  next

cmd += ["-c:a", "aac"]
if srt != None:
  cmd += ["-c:s", "ass"]
cmd += [output]

print(subprocess.list2cmdline(cmd))
if output != '':
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  for c in iter(lambda: process.stdout.read(1), b""):
    sys.stdout.write(c)