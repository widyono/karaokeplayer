#!/usr/bin/env python3

# karaokeplayer.py
#
# basic file explorer widget with preset starting folders
# based on pre-organized karaoke filters

from tkinter import *
from tkinter import filedialog, N, E, S, W, X, Y
from tkinter import font
from functools import partial
import sys
import subprocess
import os
import random
from datetime import datetime

KARAOKE_DIR="/path/to/videos"

# TODO:
# * index all by-decade, by-genre, and by-mood subdirectories and allow
#   "SURPRISE ME BY GENRE" selection
# * add text search bar to search filenames in flat/
# * index lyrics to all songs and map to filenames
# * add text search bar to search lyrics

choices = ['by-artist-first', 'by-artist-last', 'by-decade', 'by-genre', 'by-mood', 'by-title', 'flat']
indexes = {'by-decade':[], 'by-genre':[], 'by-mood':[]}

for filter in indexes:
    indexes[filter].extend(os.listdir(KARAOKE_DIR+'/'+filter))

def play_file(filepath, prefix="", filter=""):
    errortxt=""
    try:
        label_currently_playing.configure(text = "Currently playing:\n" + os.path.basename(filepath))
        window.update()
        # OSX: open: -W = wait until app exits, -n = force new instance, -a iina = use IINA application
        subprocess.check_call(["open", "-W", "-n", "-a", "iina", prefix + filepath])
    except ChildProcessError as err:
        label_currently_playing.configure(text = f"ERROR PLAYING:\n{os.path.basename(filepath)}\n{err}")
        errortxt=",\"ERROR:"+err+"\""
    else:
        label_currently_playing.configure(text = "Last played:\n" + os.path.basename(filepath))
    finally:
        with open("playlist.txt", "a") as myfile:
            logpath=prefix+filepath
            logpath=logpath[len(KARAOKE_DIR)+1:]
            myfile.write(f"\"{datetime.today().strftime('%Y%m%dT%H%M%S')}\",\"{filter}\",\"{logpath}\"{errortxt}\n")

def browseFiles(subfolder):
    filepath = filedialog.askopenfilename(initialdir = KARAOKE_DIR + "/" + subfolder,
                                        title = "Select a File",
                                        filetypes = (("all files", "*.*"),))
    if filepath:
        play_file(filepath, filter=subfolder)

def pick_random():
    filepath = random.choice(os.listdir(KARAOKE_DIR + "/flat"))
    play_file(filepath, filter="random",prefix=KARAOKE_DIR+"/flat/")

window = Tk()
myfont = font.nametofont("TkDefaultFont")
myfont.configure(size=32, weight=font.BOLD)
window.title('File Explorer')
window.geometry("{0}x{1}+10+10".format(
                        window.winfo_screenwidth()-30, window.winfo_screenheight()-100))

label_file_explorer = Label(window, 
                            text = "KARAOKE PLAYER built with Tkinter",
                            height = 4,
                            fg = "light blue")

label_currently_playing = Label(window, 
                                text = "",
                                height = 4,
                                fg = "light blue")

buttons={}
for choice in choices:
    buttons[choice] = Button(window,
                             text = f"Browse {choice}",
                             command = partial(browseFiles, choice)) 

button_exit = Button(window,
                     text = "Exit",
                     command = sys.exit) 

buttons['SURPRISE ME'] = Button(window,
                                text = f"SURPRISE ME",
                                command = pick_random)

label_instructions = Label(window,
                           text = "When video plays, press F for Full Screen, and Q to quit",
                           height = 4,
                           fg = "yellow")

#
# GUI layout
#
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=1)
label_file_explorer.grid(columnspan = 2, row = 0, sticky = "nesw")
label_currently_playing.grid(columnspan = 2, row = 1, sticky = "nesw")
buttons['by-artist-first'].grid(column = 0, row = 2, padx = 3, pady = 3)
buttons['by-artist-last'].grid(column = 1, row = 2, padx = 3, pady = 3)
buttons['by-genre'].grid(column = 0, row = 3, padx = 3, pady = 3)
buttons['by-mood'].grid(column = 1, row = 3, padx = 3, pady = 3)
buttons['by-title'].grid(column = 0, row = 4, padx = 3, pady = 3)
buttons['flat'].grid(column = 1, row = 4, padx = 3, pady = 3)
buttons['SURPRISE ME'].grid(columnspan = 2, row = 5, padx = 3, pady = 3)
button_exit.grid(columnspan = 2, row = 6, padx = 3, pady = 3)
label_instructions.grid(columnspan = 2, row = 7, sticky = "nesw")

#
# MAIN LOOP
#
window.mainloop()
