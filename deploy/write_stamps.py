# -*- coding: utf-8 -*-
import os

MEDIA = "/opt/katin-bot/media/prompts"
OUT = "/opt/katin-bot/data/prepared_video"
NAMES = ["IMG_8398", "IMG_8422", "IMG_8427", "IMG_8431", "IMG_8433"]

for name in NAMES:
    src = os.path.join(MEDIA, name + ".MOV")
    dest = os.path.join(OUT, name + ".mp4")
    stamp_path = dest + ".src"
    st = os.stat(src)
    stamp = "v3|{}|{}|{}".format(os.path.abspath(src), st.st_size, int(st.st_mtime))
    with open(stamp_path, "w") as fh:
        fh.write(stamp)
    print(stamp)
