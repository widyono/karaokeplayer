#!/usr/bin/env python3

# karaokeplayer.py
#
# basic file explorer widget with preset starting folders
# based on pre-organized karaoke filters

from tkinter import *
from tkinter import filedialog
from tkinter import font
from tkinter import VERTICAL
from functools import partial
import sys
import subprocess
import os
import fnmatch
import re
import random
from datetime import datetime
import argparse

parser = argparse.ArgumentParser(description="KARAOKE PLAYER")
parser.add_argument("-d","--directory", help="Directory containing Karaoke video structure")
parser.add_argument('searchterm', type=str, nargs='?', help='Search term to filter Karaoke video listing')
args = parser.parse_args()

KARAOKE_DIR="/path/to/videos"
if os.environ.get("KARAOKE_DIR"):
    KARAOKE_DIR=os.environ.get("KARAOKE_DIR")
if args.directory:
    KARAOKE_DIR=args.directory
FLAT_DIR=KARAOKE_DIR+"/flat/"

# TODO:
# * index all by-decade, by-genre, and by-mood subdirectories and allow
#   "SURPRISE ME BY GENRE" selection
# * add text search bar to search filenames in flat/
# * index lyrics to all songs and map to filenames
# * add text search bar to search lyrics

choices = ['by-artist-first', 'by-artist-last', 'by-decade', 'by-genre', 'by-mood', 'by-title', 'flat']
indexes = {'by-decade':[], 'by-genre':[], 'by-mood':[]}
filtered_filenames = []
already_played = []
picker_filter = ""

for filter in indexes:
    indexes[filter].extend(os.listdir(KARAOKE_DIR+'/'+filter))

def play_picked_file(*args):
    indexes = picker.curselection()
    if len(indexes) == 1:
        index = int(indexes[0])
        filename = filtered_filenames[index]
        play_file(filename, prefix=FLAT_DIR, filter=picker_filter)

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
    filepath = random.choice(os.listdir(FLAT_DIR))
    play_file(filepath, filter="random",prefix=FLAT_DIR)

def run_search_event(event):
    run_search_trigger()

def run_search_trigger():
    global filtered_filenames, filtered_filenames_list, picker_filter
    # TODO: sanitize search_term
    search_term_entry = search_term_string.get()
    picker_filter = f"searched_for:{search_term_entry}"
    search_term = f"*{search_term_entry}*.*"
    rematch = fnmatch.translate(search_term)
    filtered_filenames = [n for n in os.listdir(FLAT_DIR) if re.match(rematch, n, re.IGNORECASE)]
    if filtered_filenames:
        filtered_filenames_list.set(filtered_filenames)
    else:
        print(f"Could not find any matching files for {search_term}")
        filtered_filenames_list=StringVar(value=[])

window = Tk()
filtered_filenames_list=StringVar(value=[])
search_term_string=StringVar(value="")
myfont = font.nametofont("TkDefaultFont")
myfont.configure(size=32, weight=font.BOLD)
window.title('File Explorer')
window.geometry("{0}x{1}+10+10".format(
                        window.winfo_screenwidth()-30, window.winfo_screenheight()-100))

label_file_explorer = Label(window, 
                            text = "KARAOKE PLAYER built with Tkinter")

label_currently_playing = Label(window, 
                                text = "")

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

label_search = Label(window,
                     text = "SEARCH:")
entry_search = Entry(window, textvariable=search_term_string)
entry_search.bind("<Return>", run_search_event)

label_instructions = Label(window,
                           text = "When video plays, press F for Full Screen, and Q to quit")

picker_label = Label(window,
                     text = "File picker:")
picker_frame = Frame(window)
picker = Listbox(picker_frame,
                 listvariable = filtered_filenames_list)
picker.bind("<Double-1>", play_picked_file)
picker_scrollbar = Scrollbar(picker_frame,
                             orient=VERTICAL,
                             command=picker.yview)
picker['yscrollcommand'] = picker_scrollbar.set

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
label_search.grid(column = 0, row = 6, padx = 3, pady = 3)
entry_search.grid(column = 1, row = 6, padx = 3, pady = 3)
picker_label.grid(columnspan = 2, row = 7, padx = 3, pady = 3)
picker_frame.columnconfigure(0, weight=100)
picker_frame.columnconfigure(1, weight=1)
picker_frame.grid(columnspan = 2, row = 8, padx = 3, pady = 3, sticky = "nesw")
picker.grid(column = 0, row = 0, padx = 3, pady = 3, sticky = "nesw")
picker_scrollbar.grid(column = 1, row = 0, padx = 3, pady = 3, sticky = "ns")
button_exit.grid(columnspan = 2, row = 9, padx = 3, pady = 3)
label_instructions.grid(columnspan = 2, row = 10, sticky = "nesw")

if args.searchterm:
    search_term_string.set(args.searchterm)
    run_search_trigger()

#
# MAIN LOOP
#
window.mainloop()
