# Clipper

Finds the most "eventful" moments in a folder of videos and cuts a short highlight clip around each one.

```bash
python clipper.py videos/ clips/ --clip-length 15 --workers 4
python clipper.py videos/ clips/ --reencode   # frame-accurate cuts, slower
```

Needs `ffmpeg` and `ffprobe` on your PATH.
