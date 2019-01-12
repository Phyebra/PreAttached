from sys import argv
from PIL import Image
import configparser
import subprocess
import tempfile
import pathlib
import time
import sys
import os

crf = False

# Grab output and input folder
try:
    name_folder, name_file = os.path.split(argv[1])
    name_file, name_extension = os.path.splitext(name_file)
    print("Compressing:", str(argv[1]))
except IndexError:
    print("Argument parsing error!\nAre you running this program on its own?")
    os.system('echo An IndexError occurred while getting input files. Press any key to exit...')
    os.system('pause >nul')
    exit()

# Image format support
enabled_formats = {
    'video' : ['.gif', '.webm', '.mp4', '.avi'], 
    'image' : ['.jpg', '.png', '.jpeg']
}

# New ini config system
config = configparser.ConfigParser()
config_location = os.path.join('config.ini')
print("Searching for config file at:", config_location)
config.read(config_location)

# Retrieve relevant options
try:
    print("fm ", end='')
    file_max = int(config['SETUP']['target'])
    print("sf ", end='')
    suffix = config['SETUP']['suffix']
    print("vs ", end='')
    video_suffix = config['SETUP']['video_suffix']
    print("st ", end='')
    step = int(config['SETUP']['step'])
    print("fl ", end='')
    ffmpeg_location = config['DEFAULT']['ffmpeg_location']
    print("pl ", end='')
    ffprobe_location = config['DEFAULT']['ffprobe_location']
    print("tf ", end='')
    # temp_file = config['DEFAULT']['temp_file']
    temp_file = tempfile.TemporaryFile()
    print("kb ", end='')
    kilobyte = int(config['DEFAULT']['kilobyte'])
    print("cr ", end='')
    crash_pause = config['REPORTING'].getboolean('pause_on_crash')
    print("ha ", end='')
    hwaccel = config['HARDWARE'].getboolean('hwaccel')
    print("hc ", end='')
    hwcodec = config['HARDWARE']['hwcodec']
    print("ic ", end='')
    imgcont = config['SETUP'].getboolean('continue_under_target_image')
    print("vc ", end='')
    vidcont = config['SETUP'].getboolean('continue_under_target_video')
    print("gp ", end='')
    gif_pass = config['VIDEO'].getboolean('bypass_target_for_gif')
    print("ff ")
    ffmpeg_support = config['LIBRARY'].getboolean('ffmpeg')
    
    print("Video Codec:", hwcodec)

    if config['SETUP'].getboolean('reformat_images') == True:
        fmat = str(config['SETUP']['image_output_format'])
    else:
        fmat = name_extension[1:]
    
    if config['SETUP'].getboolean('reformat_videos') == True:
        video_fmat = None
    else:
        video_fmat = config['SETUP']['video_output_format']
    
    debug = config['REPORTING'].getboolean('debug')

except KeyError:
    print("Error while parsing config file!\nPlease check config.ini.")
    os.system('echo A KeyError occurred while parsing configs. Press any key to exit...')
    os.system('pause >nul')
    sys.exit()
except ValueError:
    print("Your config file values are set incorrectly!\n Please check config.ini.")
    os.system('echo A KeyError occurred while parsing configs. Press any key to exit...')
    os.system('pause >nul')
    sys.exit()

if debug == True:
    print("=============== Debug Output ===============")
    print("operating system:", sys.platform)
    print("python implementation:", sys.version_info)
    print("argv:", argv)
    print("config:", config)
    print("available formats:", enabled_formats)
    try:
        print("pillow version:")
        print("PIL ", Image.VERSION)
    except Exception as e:
        print("ERROR >" + e + "< while importing Pillow")
    try:
        print("path:", argv[0])
        print("target:", argv[1])
        print("output format:", fmat)
    except:
        print("COULD NOT PRINT argv[1]")
    print("to attempt loading ffmpeg, press a key")
    os.system('pause')
    try:
        os.system(ffmpeg_location + ' -version')
        os.system(ffprobe_location + ' -version')
    except Exception as e:
        print(e)
    os.system('pause')

current = 100                               # current image quality
passes = 0                                  # total repetitions
done = False                                # done flag
size = file_max + 1                         # initial size

# Decide whether to pause or crash without report
def terminate(pause=False, message=''):
    if pause == True:
        error_msg = 'echo Exception occurred. Details: ' + str(message) + '... Press any key to exit'
        os.system(error_msg)
        os.system('pause >nul')
    sys.exit()

def invoke_ffmpeg(source, save, vid_bw, aud_bw='128k', binary='ffmpeg.exe', crf=True, hw_accel=False):
    
    print("hw", hw_accel)
    
    additional_options = ""

    if hw_accel == False:
        start_options = ""
    elif hw_accel == True:
        start_options = " -hwaccel " + hwcodec
    
    if crf == True:
        if aud_bw == None:
            command = binary + start_options + " -i \"" + str(source) + "\" -c:v libvpx-vp9 -crf 10 -b:v " + str(vid_bw) + " -maxrate " + str(vid_bw) + " -bufsize 4M -an -f webm " + additional_options + "\"" + str(save) + "\""
        else:
            command = binary + start_options + " -i \"" + str(source) + "\" -c:v libvpx-vp9 -crf 10 -b:v " + str(vid_bw) + " -maxrate " + str(vid_bw) + " -bufsize 4M -c:a libopus -b:a " + str(aud_bw) + " -f webm " + additional_options + "\"" + str(save) + "\""
    elif crf == False:
        if aud_bw == None:
            command = binary + start_options + " -i \"" + str(source) + "\" -c:v libvpx-vp9 -b:v " + str(vid_bw) + " -minrate " + str(vid_bw) + " -maxrate " + str(vid_bw) + " -bufsize 4M -an -f webm " + additional_options + "\"" + str(save) + "\""
        else:
            command = binary + start_options + " -i \"" + str(source) + "\" -c:v libvpx-vp9 -b:v " + str(vid_bw) + " -minrate " + str(vid_bw) + " -maxrate " + str(vid_bw) + " -bufsize 4M -c:a libopus -b:a " + str(aud_bw) + " -f webm " + additional_options + "\"" + str(save) + "\""
    else:
        raise 'EncodingError'

    print("passing command:", command)
    os.system(command)

def is_animated(img):
    gif = Image.open(img)
    try:
        gif.seek(1)
    except EOFError:
        return False
    else:
        return True

# Get size of input image
x = os.path.getsize(argv[1]) / kilobyte

print("Image ext:", name_extension)
# time.sleep(50)

# Decide whether to send to PIL or ffmpeg
if name_extension == '.gif' and name_extension in enabled_formats['video'] or name_extension in enabled_formats['image']:
    if is_animated(argv[1]):
        mode = 'video'
    else:
        mode = 'image'
elif name_extension in enabled_formats['video']:
    mode = 'video'
elif name_extension in enabled_formats['image']:
    mode = 'image'
else:
    print("File extension does not exist")
    os.system('pause')
    exit()

# Decide whether to terminate if the image is already the right size
if x < size:
    print("Image already fits within criteria, checking options...")
    if mode == 'video' and name_extension == '.gif' and gif_pass == True:
        print("bypassing")
    elif mode == 'video' and vidcont == False:
        terminate()
    elif mode == 'image' and imgcont == False:
        terminate()

if mode == 'video':
    
    if ffmpeg_support == False:
        print("Video support has been disalbed in config files.")
        os.system('PAUSE')
        sys.exit()
    
    # Video compression mode
    print("Video file detected. Encoding...")
    src = pathlib.Path(argv[1])
    run_time_cmd = str(ffprobe_location) + ' -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"' + str(src) + "\""
    run_time = float(os.popen(run_time_cmd).read())
    print("runtime:", run_time)
    
    # Encode without audio if formatted as .gif
    if name_extension == '.gif':
        save = pathlib.Path(os.path.join(name_folder, (str(name_file) + str(suffix) + '.webm')))
        available_kbps = str(int((file_max / run_time) * 0.85)) + 'k'
        print("available bandwidth:", available_kbps)
        invoke_ffmpeg(src, save, available_kbps, None, ffmpeg_location, crf, hwaccel)
    
    else:
        
        save = pathlib.Path(os.path.join(name_folder, (str(name_file) + str(suffix) + str(name_extension))))
        available_kbps = int((file_max * 8) / run_time)
        print("total bandwidth:", available_kbps)
        
        if 150 < available_kbps < 200:
            available_kbps -= int((100 - (300 - available_kbps)) * 0.91)
            audio_quality = int((100 - (300 - available_kbps)) * 0.91)
        
        elif available_kbps <= 150:
            audio_quality = None

        else:
            audio_quality = '118k'
            available_kbps -= 128
        
        available_kbps = str(int(available_kbps * 0.85)) + 'k'
        
        print("available bandwidth:", available_kbps)
        
        invoke_ffmpeg(src, save, available_kbps, audio_quality, ffmpeg_location, crf, hwaccel)
    
    subprocess.Popen(r'explorer /select, "' + str(save))

elif mode == 'image': 
    # Image compression mode
    while True:
        # Recompress every time target missed
        if done == False:
            img = Image.open(argv[1])
            done = True
            rgb = img.convert('RGB')
            

            try:
                rgb.save(temp_file, format=fmat, quality=current)
            except Exception as e:
                print(temp_file, temp_file, fmat, current)
                print(e)
                terminate(True)
        # Get size of the saved file
        size = os.stat(temp_file.name).st_size / kilobyte
        print("Pass -->", passes, round(size), "kb. Originally:", file_max)
        passes += 1  
        
        # Stop if done
        if size < file_max or passes > 10:    
            print("done --> " + str(round(size,2)) + " kb")
            name_file, name_ext = os.path.splitext(name_file)
            name_file = name_file + str(suffix) 

            # Reformat image?
            if fmat == None: 
                out = os.path.join(name_folder, (str(name_file) + name_ext))
            else: 
                out = os.path.join(name_folder, (str(name_file) + '.' + str(fmat)))
            
            # Save image and report to user
            rgb.save(out)
            print(out)
            subprocess.Popen(r'explorer /select, "' + out)
            
            os.system('cls')
            os.system('color 0a')
            print("Your file was successfully saved:", out)
            time.sleep(2)
            break
            
        else:
            current -= step
            print(current)
            continue
else:
    print("Unsupported extension!")
    terminate(crash_pause)
