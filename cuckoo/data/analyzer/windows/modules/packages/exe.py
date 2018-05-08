# Copyright (C) 2010-2013 Claudio Guarnieri.
# Copyright (C) 2014-2016 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import shlex

from lib.common.abstracts import Package
from multiprocessing import Process


def _run(pid, path, etw_exe_name):
    """run ETW_write_logfile.exe"""
    curdir = os.curdir
    os.chdir(path)
    os.system(etw_exe_name + " " + str(pid))
    os.chdir(curdir)


class Exe(Package):
    """EXE analysis package."""

    def __init__(self, options={}, analyzer=None):
        super(Exe, self).__init__(options, analyzer)

        self.etw_path = self.options.get("etw_path")
        self.etw_exe_name = "ETW_write_logfile.exe"
        self.collecter_pidfile = "collecter_pid.txt"
        self.exe_pidfile = "sample_pid.txt"

    def _start_collecter(self, pid):
        """Create a new process to start etw
        Save pid of sample exe and etw"""
        if self.options.get("etw") and self.etw_path:
            etw_exe_path = os.path.join(self.etw_path, self.etw_exe_name)
            if os.path.exists(etw_exe_path):
                p = Process(target=_run, args=(pid, self.etw_path, self.etw_exe_name))
                p.start()
                with open(os.path.join(self.etw_path, self.collecter_pidfile), "w") as f:
                    f.write(str(p.pid))
                with open(os.path.join(self.etw_path, self.exe_pidfile), "w") as f:
                    f.write(str(pid))

    def start(self, path):
        args = self.options.get("arguments", "")

        name, ext = os.path.splitext(path)
        if not ext:
            new_path = name + ".exe"
            os.rename(path, new_path)
            path = new_path

        pid = self.execute(path, args=shlex.split(args))

        self._start_collecter(pid)

        return pid
