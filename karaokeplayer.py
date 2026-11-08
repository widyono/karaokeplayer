#! /bin/sh -
''':'
find_best_python ()
{
    # regardless of algorithm, we are purposely ignoring Python 3.7 and 3.10; YMMV
    #
    # prioritize "most used" Python distribution on system with
    #   multiple versions installed side by side (determined by
    #   whichever has the most site packages installed)
    most_packages="$(ls -d /usr/lib/python3.{14,13,12,11,9,8,6}/site-packages/* /usr/lib/python2.7/site-packages/* /opt/local/Library/Frameworks/Python.framework/Versions/3.{14,13,12,11,9,8,6} /opt/local/Library/Frameworks/Python.framework/Versions/2.7/site-packages/* 2>/dev/null|awk -F/ '{print $4}'|uniq -c|sort -nr|head -1|awk '{print $2}')"
    if "$most_packages" -c '' 2>/dev/null; then
        echo "$most_packages"
        return
    fi
    # if for some reason we cannot identify "most used" version,
    #   simply pick the most modern binary actually installed
    for highest_installed in python3.14 python3.13 python3.12 python3.11 python3.9 python3.8 python3.6 python2.7 ; do
        if "$highest_installed" -c '' 2>/dev/null; then
            echo "$highest_installed"
            return
        fi
    done
    echo >&2 "Can't find appropriate Python interpreter"
    false
}
interpreter="$(find_best_python)" || exit
exec "$interpreter" "$0" "$@"
'''



# karaokeplayer.py
#
# https://github.com/widyono/karaokeplayer
#
# basic file explorer widget with preset starting folders
# based on pre-organized karaoke filters
#
# environment variables:
# KARAOKE_DIR   path to directory structure with karaoke video files
#
# structure:
# KARAOKE_DIR/
#   all/[:first_character:]/original_video_file         (original filename from download)
#   by-artist-first/[:first_initial:]/symlinks_into_all (symlink named First Last - Title)
#   by-artist-last/[:last_initial:]/symlinks_into_all   (symlink named Last,First - Title)
#   by-decade/[:4_digit_decade:]/symlinks_into_all      (symlink named Title - First Last)
#   by-genre/[:genre_label:]/symlinks_into_all          (symlink named Title - First Last)
#   by-mood/[:mood_label:]/symlinks_into_all            (symlink named Title - First Last)
#   by-title/[:title_initial:]/symlinks_into_all        (symlink named Title - First Last)
#   lyrics/[:first_character:]/original_filename_text_lyrics

from tkinter import Tk, filedialog, font, VERTICAL, END, StringVar, Scrollbar, Listbox, Frame, Label, Entry, Button
from functools import partial
import sys
import subprocess
import os
import fnmatch
import re
import random
from datetime import datetime
import argparse
import shutil

parser = argparse.ArgumentParser(description="KARAOKE PLAYER")
parser.add_argument("-d","--directory", help="Directory containing Karaoke video structure")
parser.add_argument("-u","--unique", action="store_true", help="Enforce playing anything only once during a single session")
parser.add_argument('searchterm', type=str, nargs='?', help='Search term to filter Karaoke video listing')
args = parser.parse_args()

KARAOKE_DIR=os.path.dirname(sys.argv[0])
KARAOKE_DEFAULT_FONT="TkDefaultFont"
KARAOKE_FIXED_FONT="TkFixedFont"
KARAOKE_DEFAULT_TEXT_SIZE=32
KARAOKE_KEY_FULLSCREEN="F"
if shutil.which("cvlc"):
    # -f = fullscreen
    KARAOKE_BIN_ARGS=["cvlc", "-f"]
    KARAOKE_KEY_QUIT="Ctrl-Q"
else:
    # -W = wait until app exits, -n = force new instance, -a iina = use IINA application
    KARAOKE_BIN_ARGS=["open", "-W", "-n", "-a", "iina"]
    KARAOKE_KEY_QUIT="Q"
for varname in [
        "KARAOKE_DIR",
        "KARAOKE_DEFAULT_FONT",
        "KARAOKE_DEFAULT_TEXT_SIZE",
        "KARAOKE_BIN_ARGS",
        "KARAOKE_KEY_QUIT",
        "KARAOKE_KEY_FULLSCREEN"
        ]:
    if os.environ.get(varname):
        if varname == "KARAOKE_BIN_ARGS":
            globals()[varname] = os.environ.get(varname).split()
        else:
            globals()[varname] = os.environ.get(varname)
if args.directory:
    KARAOKE_DIR=args.directory
KARAOKE_DIR=KARAOKE_DIR.split(',')[0]
TITLE_DIR=KARAOKE_DIR+"/by-title/"
PLAYLIST_FILE="{}/karaoke_playlist.txt".format(os.path.expanduser('~'))

# TODO:
# * index by-decade, by-genre, and by-mood top level directories
#   enabling "SURPRISE ME BY GENRE / DECADE / MOOD" feature
# * index lyrics to all songs and map to filenames
#   enabling text search bar for searching by lyrics

choices = ['by-artist-first', 'by-artist-last', 'by-decade', 'by-genre', 'by-mood', 'by-title']
filtered_filenames = []
session_history = {}
picker_filter = ""
picker_width = 0
filetrees = {}
maxwidth = {}

#def on_picker_resize(event):
#    global fixedfontwidth
#    picker.update()
#    picker_width = picker.winfo_width() // fixedfontwidth

for choice in choices:
    filetrees[choice] = []
    for root, dirs, files in os.walk("{}/{}".format(KARAOKE_DIR,choice)):
        dirs.sort()
        if not any(n in choice for n in ["by-title", "by-artist-first", "by-artist-last"]):
            if not choice in maxwidth:
                if dirs:
                    maxwidth[choice] = len(max(dirs, key=len))
                else:
                    maxwidth[choice] = 0
        for file in sorted(files):
            if file[0] == '.':
                continue
            filetrees[choice].append((root,file))

def get_timestamp():
    return datetime.today().strftime('%Y%m%dT%H%M%S')

def play_picked_file(*args):
    indexes = picker.curselection()
    if len(indexes) == 1:
        index = int(indexes[0])
        file_tuple = filtered_filenames[index]
        filename = file_tuple[0] + os.sep + file_tuple[1]
        play_file(filename, prefix="", picker_filter=picker_filter)

def play_file(filepath, prefix="", picker_filter=""):
    errortxt=""
    basepath=os.path.basename(filepath)
    basepath_repr=basepath.removesuffix(".mp4")
    if args.unique and basepath in session_history:
        label_currently_playing.configure(text = "ENFORCING UNIQUE PLAYS, ALREADY PLAYED THIS SESSION:\n{}".format(basepath_repr))
        with open(PLAYLIST_FILE, "a") as myfile:
            myfile.write("\"{}\",\"{}\",\"{}\",\"ERROR:NOT UNIQUE\"\n".format(get_timestamp(),picker_filter,basepath_repr))
        return
    try:
        label_currently_playing.configure(text = "Currently playing:\n" + basepath_repr)
        window.update()
        subprocess.check_call(KARAOKE_BIN_ARGS + [prefix + filepath])
    except ChildProcessError as err:
        label_currently_playing.configure(text = "ERROR PLAYING:\n{}\n{}".format(basepath_repr,err))
        errortxt=",\"ERROR:"+err+"\""
    else:
        label_currently_playing.configure(text = "Last played:\n" + basepath_repr)
    finally:
        session_history[basepath]=True
        with open(PLAYLIST_FILE, "a") as myfile:
            #logpath=prefix+filepath
            #logpath=logpath[len(KARAOKE_DIR)+1:]
            myfile.write("\"{}\",\"{}\",\"{}\"{}\n".format(get_timestamp(),picker_filter,basepath_repr,errortxt))

def pick_random():
    file = random.choice(filetrees['by-title'])
    play_file(file[1], picker_filter="random", prefix=file[0] + os.sep)

def fully_justify_picker_entries(entries):
    global filtered_filenames_list, picker_width
    fully_justified_entries = []
    for entry in entries:
        (lhs, rhs) = re.split(' - ', entry, maxsplit=1)
        lhs_width = len(lhs)
        rhs_width = len(rhs)
        space_width = picker_width - lhs_width - rhs_width
        if space_width < 2:
            if lhs_width > picker_width // 2 - 1:
                lhs_width = picker_width // 2 - 1
            if rhs_width > picker_width // 2 - 1:
                rhs_width = picker_width // 2 - 1
            space_width = picker_width - lhs_width - rhs_width
        spaces = " " * space_width
        fully_justified_entries.append("  {}{}{}".format(lhs[0:lhs_width],spaces,rhs[0:rhs_width]))
    filtered_filenames_list.set(fully_justified_entries)
    picker.selection_clear(0, END)
    picker.see(0)

def run_browse_trigger(filter):
    global filtered_filenames, picker_filter
    picker_filter = "browse:{}".format(filter)
    filtered_filenames = filetrees[filter]
    entries=[]
    if not any(n in filter for n in ["by-title", "by-artist-first", "by-artist-last"]):
        for file_tuple in filtered_filenames:
            entries.append(os.path.basename(file_tuple[0]).ljust(maxwidth[filter]) + ": " + file_tuple[1].removesuffix('.mp4'))
    else:
        for file_tuple in filtered_filenames:
            entries.append(file_tuple[1].removesuffix('.mp4'))
    fully_justify_picker_entries(entries)

def run_search_event(event):
    run_search_trigger()

def run_search_trigger():
    global filtered_filenames, picker_filter
    # TODO: sanitize search_term
    search_term_entry = search_term_string.get()
    picker_filter = "searched_for:{}".format(search_term_entry)
    search_term = "*{}*.*".format(search_term_entry)
    rematch = fnmatch.translate(search_term)
    filtered_filenames = []
    for file_tuple in filetrees['by-title']:
        if re.match(rematch, file_tuple[1], re.IGNORECASE):
            filtered_filenames.append(file_tuple)
    if filtered_filenames:
        fully_justify_picker_entries([file_tuple[1].removesuffix('.mp4') for file_tuple in filtered_filenames])
    else:
        label_currently_playing.configure(text = "ERROR, COULD NOT FIND:\n" + search_term)
        fully_justify_picker_entries([])

window = Tk()
filtered_filenames_list=StringVar(value=[])
search_term_string=StringVar(value="")
defaultfont = font.nametofont(KARAOKE_DEFAULT_FONT)
defaultfont.configure(size=KARAOKE_DEFAULT_TEXT_SIZE, weight=font.BOLD)
fixedfont = font.nametofont(KARAOKE_FIXED_FONT)
fixedfont.configure(size=KARAOKE_DEFAULT_TEXT_SIZE)
fixedfontwidth = fixedfont.measure("m")
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
                             text = "Browse {}".format(choice),
                             command = partial(run_browse_trigger, choice)) 

button_exit = Button(window,
                     text = "Exit",
                     command = sys.exit) 

buttons['SURPRISE ME'] = Button(window,
                                text = "SURPRISE ME",
                                command = pick_random)

label_search = Label(window,
                     text = "SEARCH:")
entry_search = Entry(window, textvariable=search_term_string, font=fixedfont)
entry_search.bind("<Return>", run_search_event)

label_instructions = Label(window,
                           text = "When video plays, press {} for Full Screen, and {} to quit".format(
                               KARAOKE_KEY_FULLSCREEN, KARAOKE_KEY_QUIT))

picker_label = Label(window,
                     text = "File picker:")
picker_frame = Frame(window)
picker = Listbox(picker_frame,
                 listvariable = filtered_filenames_list,
                 font=fixedfont)
picker.bind("<Double-1>", play_picked_file)
#picker.bind("<Configure>", on_picker_resize)
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
buttons['by-decade'].grid(column = 1, row = 4, padx = 3, pady = 3)
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
picker.update()
picker_width = picker.winfo_width() // fixedfontwidth

if args.searchterm:
    search_term_string.set(args.searchterm)
    run_search_trigger()

with open(PLAYLIST_FILE, "a") as myfile:
    myfile.write("===================================NEW=SESSION=\"{}\"\n".format(get_timestamp()))

#
# MAIN LOOP
#
window.mainloop()
