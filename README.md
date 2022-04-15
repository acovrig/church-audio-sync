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