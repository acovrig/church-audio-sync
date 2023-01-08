This is a simple python app that handles shutdown of the Streaming-PC.

This app should:
* Close things
  * VoiceMeeter
  * OBS
  * Chrome
  * Waveform
  * Livestream
* Compress the waveform audio to a ultra level 7z
* Transcode the H.264 mkv to a H.264 and HEVC mp4
* Upload the 7z and mp4 files to the school's server (for an off-site backup)
* Upload the transcoded H.264 mp4 to Beckett


# Sync Audio Tracks
This code is forked and expanded from [Alexander Lopatin's repository](https://github.com/alopatindev/sync-audio-tracks).
It calculates a delay between the audio from OBS and Waveform.
It then merges all audio from Waveform into an `mkv` with video from OBS.
If subtitles, bulletin PDF, and chapters are available, it will merge those in also.
If subtitles are not available, it will generate them via the Google Translate API.
If the sample rate between OBS and Waveform don't match, it will resample the Waveform audio to match.
If the video codec isn't hevc, it will convert it.

### Supported Formats
They depend on how SoX and FFmpeg were built for your OS ([more details](https://github.com/alopatindev/sync-audio-tracks/issues/2#issuecomment-421603812)). If it didn't work with some format for you — try WAV as experiment.

## Installation
Make sure these dependences are installed:
- bash (tested with 4.4.23)
- bc (tested with 1.06.95)
- ffmpeg (tested with 4.1.3)
- fftw (tested with 3.3.6_p2)
- libsndfile (tested with 1.0.28)
- python3 (tested with 3.6.10)
- sox (tested with 14.4.2)
- autosub3 (`pip3 install`) (tested with 0.1.0)

On Debian some packages may need to be installed together with `-dev` packages (for instance `fftw` with `fftw-dev`).

Now compile it with
```
make -j
```

## Usage
```
python3 entrypoint.py -v <video file> -a <audio dir> [-c <chapters>] [-s <subtitles>] [-p <pdfs_dir] [-o <output>]
```
OR
```
docker run -it --rm -v $(pwd):/media -w /media image_name -v obs_video.mp4 -a waveform_project/Recorded -o merged.mkv
```
## License
[Apache 2.0](LICENSE.txt)

Copyright (C) 2018—2020 Alexander Lopatin
