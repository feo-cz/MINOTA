Import('env')
import os
import shutil
import gzip
from zopfli.gzip import compress
import datetime

OUTPUT_DIR = "build_output{}".format(os.path.sep)

def get_env_name(target):
    parts = str(target[0]).split(os.sep)
    return parts[-2] if len(parts) > 1 else "unknown_env"

def bin_gzip(source, target, env):
    date_str = datetime.datetime.now().strftime("MINOTA_%Y%m%d_")
    env_name = get_env_name(target)
    variant = date_str + env_name

    # create string with location and file names based on variant
    bin_file = "{}firmware{}{}.bin".format(OUTPUT_DIR, os.path.sep, variant)
    gzip_file = "{}firmware{}{}.bin.gz".format(OUTPUT_DIR, os.path.sep, variant)

    # check if new target files exist and remove if necessary
    if os.path.isfile(gzip_file): os.remove(gzip_file)

    # write gzip firmware file
    with open(bin_file, "rb") as fp:
        with open(gzip_file, "wb") as f:
            zopfli_gz = compress(fp.read())
            f.write(zopfli_gz)
            shutil.copyfileobj(fp, f)

env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", [bin_gzip])
