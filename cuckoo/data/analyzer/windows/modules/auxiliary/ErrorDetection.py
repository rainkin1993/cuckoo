import os
from subprocess import Popen
from lib.common.abstracts import Auxiliary
from lib.common.results import upload_to_host
import logging

import json
import win32gui, win32con, win32api, win32process
import time
from multiprocessing import Process

log = logging.getLogger(__name__)


class Window(object):
    def __init__(self):
        self.hwnd = None  #handle of the window
        self.classname = None  #class name of the window
        self.text = None  #title/text of the window
        self.pid = None  #process id of the window
        self.tid = None  #thread id of the window
        self.owner = None #hwnd of the owner window
        self.isvisible = None  #visibility of the window
        self.left = None  #left bound of the window
        self.right = None  #right bound of the window
        self.top = None  #top bound of the window
        self.bottom = None  #bottom bound of the window
        self.staticicon = None  #static icon id of the window(if not exist, equal to 0)
        self.childwins = None  #child windows of the window


class WindowEncoder(json.JSONEncoder):
    def default(self, win):
        tmp = {}
        tmp['hwnd'] = win.hwnd
        tmp['classname'] = win.classname
        tmp['text'] = win.text
        tmp['pid'] = win.pid
        tmp['tid'] = win.tid
        tmp['owner'] = win.owner
        tmp['isvisible'] = win.isvisible
        tmp['left'] = win.left
        tmp['right'] = win.right
        tmp['top'] = win.top
        tmp['bottom'] = win.bottom
        tmp['staticicon'] = win.staticicon
        if win.childwins is not None:
            tmp['childwins'] = []
            for childwin in win.childwins:
                tmp['childwins'].append(self.default(childwin))
        else:
            tmp['childwins'] = None
        return tmp


def _WindowEnum(hwnd, extra):
    windows = extra[0]
    init_check = extra[1]
    parent = extra[2]
    if windows.has_key(hwnd):
        return True
    windows[hwnd] = 1
    if not init_check:
        win = Window()
        win.hwnd = hwnd
        win.classname = win32gui.GetClassName(hwnd)
        win.text = win32gui.GetWindowText(hwnd)
        try:
            win.text.encode('utf-8')
        except BaseException:
            win.text = "There are some characters cannot be encoded!"
        win.staticicon = win32gui.SendMessage(hwnd, win32con.STM_GETICON)
        win.tid, win.pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            win.owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        except:
            win.owner = None
        win.owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        if win32gui.IsWindowVisible(hwnd):
            win.isvisible = True
            rect = win32gui.GetWindowRect(hwnd)
            win.left = rect[0]
            win.right = rect[2]
            win.top = rect[1]
            win.bottom = rect[3]
            try:
                win32gui.EnumChildWindows(hwnd, _WindowEnum, (windows, init_check, win))
            except:
                pass
        else:
            win.isvisible = False
        if parent.childwins is None:
            parent.childwins = []
        parent.childwins.append(win)

def EnumMsgOnlyWin():
    hwnd = win32gui.FindWindowEx(win32con.HWND_MESSAGE, None, None, None)
    msg_only_wins ={}
    while hwnd is not None:
        if msg_only_wins.has_key(hwnd):
            break
        elif(hwnd != 0):
            msg_only_wins[hwnd] = win32gui.GetClassName(hwnd)
        else:
            msg_only_wins[hwnd] = ""
        hwnd = win32gui.FindWindowEx(win32con.HWND_MESSAGE, hwnd, None, None)
    return msg_only_wins

def run(path, msgwin, rootwin):
    init_check = True
    windows = {}
    try:
        while True:
            win32gui.EnumWindows(_WindowEnum, (windows, init_check, rootwin))
            msg_only_wins = EnumMsgOnlyWin()
            init_check = False
            window_info = open(path, 'w')
            window_info.write(WindowEncoder().encode(rootwin))
            window_info.close()
            msg_only_window = open(msgwin, 'w')
            msg_only_window.write(str(msg_only_wins))
            msg_only_window.close()
            time.sleep(1)
    except UnicodeError:
        window_info.write("Unicode error!\n")


class ErrorDetection(Auxiliary):
    """Allow ETWTraceCollecter to be run on the side."""

    # print "All tests done!"

    def start(self):
        """Start the etw collecter"""
        curdir = os.getcwd()
        self.path = os.path.join(curdir, "bin", "window_info.txt")
        self.msgwin = os.path.join(curdir, "bin", "msg_only_window.txt")
        self.rootwin = Window()
        self.p = Process(target=run, args=(self.path, self.msgwin, self.rootwin))
        self.p.start()
        log.debug("After start ErrorDetection")

    def stop(self):
        """Stop the etw collecter, preprocess the output,
        compress the result and upload the archive"""

        # CD into the path of etw collecter

        Popen("taskkill /F /T /PID %i" % self.p.pid, shell=True)
        upload_to_host(self.path, os.path.join("files", "window_info.txt"))
        upload_to_host(self.msgwin, os.path.join("files", "msg_only_window.txt"))
        log.debug("Successfully upload to the result server")


