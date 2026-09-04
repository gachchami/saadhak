"""Rebuild the video against human narration dropped in docs/voice/."""
import glob, json, os, subprocess

VOICE_DIR = "private/voice"
PAD = 0.7
frames = sorted(glob.glob("/tmp/vid/frames/*.png"))
clips = sorted(f for f in glob.glob(f"{VOICE_DIR}/*") if os.path.splitext(f)[1].lower()
               in (".m4a", ".mp3", ".wav", ".aiff", ".caf", ".mp4"))

def dur(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                 "-of","csv=p=0",p], capture_output=True, text=True).stdout.strip())

if len(clips) == 1:
    # one continuous take: split the video evenly across the narration
    total = dur(clips[0]); per = total / len(frames)
    audio = clips[0]
    timings = [per] * len(frames)
    print(f"one take, {total:.0f}s across {len(frames)} frames ({per:.1f}s each)")
else:
    if len(clips) != len(frames):
        raise SystemExit(f"{len(clips)} clips for {len(frames)} frames; name them 01..{len(frames):02d}")
    padded = []
    for i, c in enumerate(clips):
        out = f"/tmp/vid/audio/h{i:02d}.m4a"
        subprocess.run(["ffmpeg","-y","-i",c,"-af",f"apad=pad_dur={PAD}",
                        "-c:a","aac","-b:a","192k",out], capture_output=True, check=True)
        padded.append(out)
    with open("/tmp/vid/hlist.txt","w") as f:
        for p in padded: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","/tmp/vid/hlist.txt",
                    "-c:a","aac","-b:a","192k","/tmp/vid/human.m4a"], capture_output=True, check=True)
    audio = "/tmp/vid/human.m4a"
    timings = [dur(p) for p in padded]
    print(f"{len(clips)} clips, {sum(timings):.0f}s total")

with open("/tmp/vid/hframes.txt","w") as f:
    for p, t in zip(frames, timings):
        f.write(f"file '{p}'\nduration {t:.2f}\n")
    f.write(f"file '{frames[-1]}'\n")

subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","/tmp/vid/hframes.txt",
                "-i",audio,"-vf","scale=1920:1080,format=yuv420p","-r","30",
                "-c:v","libx264","-preset","medium","-crf","20",
                "-c:a","aac","-b:a","192k","-shortest","docs/saadhak.mp4"],
               capture_output=True, check=True)
print("docs/saadhak.mp4 rebuilt with your voice")
