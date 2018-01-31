from cuckoo.common.abstracts import Processing
from os.path import join
from cuckoo.common.exceptions import CuckooProcessingError
from json import dump, load


class Window(object):
    def __init__(self):
        self.hwnd = None
        self.classname = None
        self.text = None
        self.pid = None
        self.tid = None
        self.owner = None
        self.isvisible = None
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None
        self.staticicon = None
        self.childwins = None


class WindowInfo(Processing):
    """Analysis debug information."""

    def parse_json(self, jdict):
        win = Window()
        win.hwnd = jdict['hwnd']
        win.text = jdict['text']
        win.classname = jdict['classname']
        win.pid = jdict['pid']
        win.tid = jdict['tid']
        win.owner = jdict['owner']
        win.isvisible = jdict['isvisible']
        win.left = jdict['left']
        win.right = jdict['right']
        win.top = jdict['top']
        win.bottom = jdict['bottom']
        win.staticicon = jdict['staticicon']
        if jdict['childwins'] is not None:
            win.childwins = []
            for childwin in jdict['childwins']:
                win.childwins.append(self.parse_json(childwin))
        return win

    def find_owner(self, win):
        # find owner window
        if self.rootwin.childwins is not None and win.owner > 0:
            for child in self.rootwin.childwins:
                if child.hwnd == win.owner:
                    win.owner = child
        if win.childwins is not None:
            for child in win.childwins:
                self.find_owner(child)

    def check_win_info(self, win):
        '''if win.isvisible:
            self.process_res['hasGUI'] = True'''
        if win.staticicon == 65581:
            self.isError = 'True '+str(win.pid)+"_"+str(win.tid)
        if win.text is not None and "error" in win.text.lower():
            self.isError = 'True '+str(win.pid)+"_"+str(win.tid)
        if win.staticicon > 0 and self.isError == 'False':
            self.isError = 'NotSure '+str(win.pid)+"_"+str(win.tid)
        if win.isvisible:
            self.hasvisible = True
            self.visible_process.add(str(win.pid)+"_"+str(win.tid))
        if win.childwins is not None:
            if win.isvisible:
                self.hasGUI = True
                self.GUI_process.add(str(win.pid))
            for child in win.childwins:
                self.check_win_info(child)

    def run(self):
        """Run debug analysis.
        @return: debug information dict.
        """
        self.key = "windowinfo"
        self.GUI_process = set()
        self.visible_process = set()
        self.isError = 'False'
        self.hasGUI = False
        self.hasvisible = False
        try:
            with open(join(self.analysis_path, "files", "window_info.txt"), "r") as fp:
                if len(fp.readline().strip(' \n')) == 0:
                    return
                self.rootwin = self.parse_json(load(fp))
                self.find_owner(self.rootwin)
                self.check_win_info(self.rootwin)
        except IOError:
            raise CuckooProcessingError("window_info.txt not found!")

        try:
            with open(join(self.analysis_path, "files", "process_result.txt"), "w") as fp:
                #dump(self.process_res, fp)
                fp.writelines(self.isError+"\n")
                fp.writelines(str(self.hasGUI)+" "+",".join(self.GUI_process)+"\n")
                fp.writelines(str(self.hasvisible) + " " + ",".join(self.visible_process))
        except IOError:
            raise CuckooProcessingError("Cannot open process_result.txt")