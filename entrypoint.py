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

  sys.stdout.write(f"\tGetting volume of {title}: ")
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

def find_sync_file(fn = 'stream'):
  global sync_file, rate
  sync_file = None
  for root, dirs, files in walk(audio):
    for f in files:
      if fn.lower() in f.lower():
        sync_file = path.join(audio, f)
        if fn.lower() != 'stream':
          try:
            sys.stdout.write(f'Getting volume for sync {fn}: ')
            sys.stdout.flush()
            cmd = ['ffmpeg', '-hide_banner', '-i', sync_file, '-af', 'volumedetect', '-f', 'null', path.join(audio, f'{f}.voldetect')]
            _, volume = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            volume = re.search(r"max_volume: (.*?) dB", str(volume)).group(1)
            volume = float(volume)
            print(volume)
            if volume < -50:
              sync_file = None
          except:
            print(' (include)')
            return True

        if sync_file != None:
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
  if sync_file == None:
    if fn == 'stream':
      print('WARNING: Failed to get sync_file from stream, trying monitors')
      find_sync_file('monitors')
    elif fn == 'monitors':
      print('WARNING: Failed to get sync_file from monitors, trying piano')
      find_sync_file('piano')
    elif fn == 'piano':
      print('WARNING: Failed to get sync_file from piano, trying lapel')
      find_sync_file('lapel')
    elif fn == 'lapel':
      print('WARNING: Failed to get sync_file from lapel, trying prayer')
      find_sync_file('prayer')
  return sync_file

def get_opts():
  global video, audio, chapters, srt, pdfdir, dry_run, skip_voldetect, output, output_264
  try:
    opts, args = getopt.getopt(sys.argv[1:],"caspdhiv:o:2:",["video=","chapters", "audio_dir", "subtitles", "pdf_dir", "dry_run", "include_audio", "output", "output_264"])
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
    elif opt in ("-d", "--dry_run"): 
      dry_run = True
    elif opt in ("-i", "--include_audio"): 
      skip_voldetect = True
    elif opt in ("-o", "--output"): 
      output = arg
    elif opt in ("-2", "--output_264"): 
      output_264 = arg

  if audio == '':
    try:
      date = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})", video).group(1)
      audio = path.abspath(path.join(path.dirname(video), '..', 'audio', date, 'Recorded'))
    except AttributeError:
      print('ERROR: Unable to determine audio path')
      sys.exit(2)

  if not path.exists(video):
    print(f'ERROR: {video} does not exist')
    sys.exit(2)
  if not path.exists(audio):
    print(f'ERROR: {audio} does not exist')
    sys.exit(2)
  if output == '' and output_264 == '':
    print('ERROR: output path is required')
    print('Please specify an HEVC output [-o] or H.264 output [-2]')
    sys.exit(2)
  if not output.lower().endswith('mkv'):
    output = f'{output}.mkv'
    print(f'WARNING: output must end in mkv - appended mkv to output name: {output}')

  find_additions()
  
  return video, audio, chapters, srt, pdfdir, dry_run, skip_voldetect, output, output_264

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
        print('')
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

  print("\nGetting audio offset:\nFinding sync file")

  find_sync_file()
  print(f'Sync file: {sync_file}')

  if sync_file == None:
    print('ERROR, no sync_file specified, skipping offset calculation')
    offset = 0
    return offset

  if offset == None:
    sys.stdout.write('Calculating offset: ')
    sys.stdout.flush()
    offset, err = subprocess.Popen(['/src/compute-sound-offset.sh', video, sync_file, '900'], stdout=subprocess.PIPE).communicate()
    if offset == b'':
      print("Unable to determine offset, trying skip: ")
      if path.exists(path.join(audio, f'{f}.sync.aac')):
        cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-ss', str(30*60), '-i', path.join(audio, f'{f}.sync.aac'), '-c', 'copy', path.join(audio, f'{f}.sync30.aac')]
      else:
        cmd = ['ffmpeg', '-v', 'warning', '-stats', '-n', '-ss', str(30*60), '-i', path.join(audio, f), path.join(audio, f'{f}.sync30.aac')]
      # print(subprocess.list2cmdline(cmd))
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
      for c in iter(lambda: process.stdout.read(1), b""):
        sys.stdout.write(c)
      sync_file = path.join(audio, f'{f}.sync30.aac')
      offset, err = subprocess.Popen(['/src/compute-sound-offset.sh', video, sync_file, '900'], stdout=subprocess.PIPE).communicate()

    if offset == b'':
      if 'stream' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying monitors')
        find_sync_file('monitors')
        find_offset()
      elif 'monitors' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying piano')
        find_sync_file('piano')
        find_offset()
      elif 'piano' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying lapel')
        find_sync_file('lapel')
        find_offset()
      elif 'lapel' in sync_file.lower():
        print(f'WARNING: unable to find offset in {sync_file}, trying prayer')
        find_sync_file('prayer')
        find_offset()
      else:
        print("ERROR: Unable to determine offset")
      sys.exit(2)
  offset = float(offset)
  print(offset)

  for root, dirs, files in walk(audio):
    for f in files:
      if re.match(r".*stream.*aac$", f.lower()) != None:
        print(f'REMOVE {f}')
        remove(path.join(audio, f))
  return offset

def fix_chapters():
  global chapters
  print(f"\nFix chapters with offset {offset} - {chapters}")
  main_title = None
  chapters_arr = []
  with open(chapters, 'r') as f:
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

  chapters = f'{chapters.replace(".chapters", "")}.offset.chapters'

  new_chapters = f';FFMETADATA1\ntitle={main_title}\n\n'
  for chapt in chapters_arr:
    new_chapters += "[CHAPTER]\n"
    new_chapters += "TIMEBASE=1/1000\n"
    new_chapters += f"START={int(chapt['start'] + offset) * 1000}\n"
    new_chapters += f"END={int(chapt['end'] + offset) * 1000}\n"
    new_chapters += f"title={chapt['title']}\n\n"

  print(f'Writing {chapters}:\n\n{new_chapters}')
  with open(chapters, 'w') as f:
    f.write(new_chapters)

dry_run = False
video = chapters = audio = srt = pdfdir = output = output_264 = ''
rate = 0
get_opts()

print(f'Input video: {video}')
print(f'Input audio dir: {audio}')
print(f'Input chapters: {chapters}')
print(f'Input subtitles: {srt}')
print(f'Input pdfs dir: {pdfdir}')
print(f'Output HEVC: {output}')
print(f'Output H.264: {output_264}')
if dry_run:
  print('DRY RUN, not running ffmpeg, only generate command')

if chapters != None and not path.exists(chapters):
  print(f'ERROR: {chapters} does not exist')
  sys.exit(2)

if path.exists(output):
  print(f'ERROR: {output} exists, not overwriting')

cmd=['ffmpeg', '-hide_banner', '-n']
if output != '':
  find_offset()

  audio_count = 0
  print("\nGetting audio files (by volume):")
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
  if chapters != None:
    audio_count += 1 # So the srt map # below works (and the map_metadata)
    if offset > 0:
      fix_chapters()
    cmd += ["-i", chapters]
    cmd += ["-map_metadata", str(audio_count)]
  if srt != None:
    cmd += ["-itsoffset", str(offset)]
    cmd += ["-i", srt]
  cmd += ["-b:a", "192k"]

  cmd += ["-map", f'{audio_count}:v']
  cmd += ["-map", f'{audio_count}:a']
  if srt != None:
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
    print(f"\nPDF: {pdf}: ", end='')
    if path.exists(pdf):
      print("exists\n")
      cmd += ["-attach", pdf, "-metadata:s:t", "mimetype=application/pdf"]
    else:
      print("does not exist\n")
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
    pass

  cmd += ["-c:a", "aac"]
  if srt != None:
    cmd += ["-c:s", "ass"]
  cmd += [output]

if output_264 != '':
  if output == '':
    cmd += ['-i', video]
    if chapters != None:
      cmd += ['-i', chapters]
      cmd += ['-map_metadata', '1']
  else:
    cmd += ["-map", f'{audio_count}:v']
    cmd += ["-map", f'{audio_count}:a']
    if chapters != None:
      cmd += ["-map_metadata", str(audio_count)]
  cmd += ['-c:v', 'libx264']
  cmd += ['-c:a', 'aac']
  cmd += ['-movflags', '+faststart']
  cmd += [output_264]

print(subprocess.list2cmdline(cmd))
if not dry_run:
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  for c in iter(lambda: process.stdout.read(1), b""):
    sys.stdout.write(c)