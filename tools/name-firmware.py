Import('env')
import os
import shutil
import datetime

OUTPUT_DIR = "build_output{}".format(os.path.sep)

def get_env_name(target):
    parts = str(target[0]).split(os.sep)
    return parts[-2] if len(parts) > 1 else "unknown_env"

def bin_rename_copy(source, target, env):
    date_str = datetime.datetime.now().strftime("MINOTA_%Y%m%d_")
    env_name = get_env_name(target)
    variant = date_str + env_name
    
    # check if output directories exist and create if necessary
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    for d in ['firmware', 'map']:
        if not os.path.isdir("{}{}".format(OUTPUT_DIR, d)):
            os.mkdir("{}{}".format(OUTPUT_DIR, d))

    # create string with location and file names based on variant
    map_file = "{}map{}{}.map".format(OUTPUT_DIR, os.path.sep, variant)
    bin_file = "{}firmware{}{}.bin".format(OUTPUT_DIR, os.path.sep, variant)

    # check if new target files exist and remove if necessary
    for f in [map_file, bin_file]:
        if os.path.isfile(f):
            os.remove(f)

    # copy firmware.bin to firmware/<variant>.bin
    shutil.copy(str(target[0]), bin_file)

    # copy firmware.map to map/<variant>.map
    if os.path.isfile("firmware.map"):
        shutil.move("firmware.map", map_file)

env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", [bin_rename_copy])
