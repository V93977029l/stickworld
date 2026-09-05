"""从 SWL Unity 数据中提取全部 AudioClip（UnityPy）。

输出: audio_raw/<音效名>_<序号>.<ogg|wav>
"""
import sys, os, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import UnityPy
from UnityPy.export.AudioClipConverter import extract_audioclip_samples

SRC = r"F:\VSCode\game-2\temp\swl_audio\unpacked\assets\bin\Data"
OUT = r"F:\VSCode\game-2\temp\swl_audio\audio_raw"
os.makedirs(OUT, exist_ok=True)

env = UnityPy.load(SRC)
count, fail = 0, 0
names = []
for obj in env.objects:
    if obj.type.name != "AudioClip":
        continue
    try:
        clip = obj.read()
        name = (clip.m_Name or "unnamed").strip().replace(" ", "_")
        samples = extract_audioclip_samples(clip)
        if not samples:
            continue
        for sname, data in samples.items():
            ext = "ogg" if data[:4] == b"OggS" else "wav"
            sname = sname.strip().replace(" ", "_") or name
            path = os.path.join(OUT, f"{sname}.{ext}")
            if os.path.exists(path):
                base, e = os.path.splitext(path)
                path = f"{base}_{count}{e}"
            with open(path, "wb") as f:
                f.write(data)
            names.append(f"{os.path.basename(path)}\t{len(data)}")
            count += 1
    except Exception as e:
        fail += 1
        if fail <= 5:
            traceback.print_exc()

print(f"extracted={count} failed_clips={fail}")
with open(os.path.join(OUT, "..", "audio_index.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(names)))
