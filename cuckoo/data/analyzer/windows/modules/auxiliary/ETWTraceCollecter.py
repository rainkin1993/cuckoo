# Copyright (C) 2017 rainkin1993
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from zipfile import ZipFile, ZIP_DEFLATED
from subprocess import call
from lib.common.abstracts import Auxiliary
from lib.common.exceptions import CuckooPackageError, CuckooDisableModule, CuckooError
from lib.common.results import upload_to_host
import logging
from shutil import copy, rmtree
import win32gui
import win32con
import win32api
from psutil import pids
from time import sleep

log = logging.getLogger(__name__)


class ETWTraceCollecter(Auxiliary):
    """Allow ETWTraceCollecter to be run on the side."""

    def __init__(self, options={}, analyzer=None):
        super(ETWTraceCollecter, self).__init__(options, analyzer)

        self.etw_path = self.options.get("etw_path")
        self.etw_exe_name = "ETW_write_logfile.exe"
        self.backup_files = ["drivemapfile_backup", ]
        self.output_files = ["addressmap", "test.bin", "sample_pid.txt"]
        self.output_dirs = ["process2Module", "rva2FuncName"]
        self.dump_path = "dumpfile"
        self.collecter_pidfile = "collecter_pid.txt"
        self.addressmap_exe = "obtain_syscall_address.exe"
        self.archive_name = "output.zip"
        self.pids_file_name = "sample_pids.txt"

    def start(self):
        """Do preparation work for etw"""

        '''if not self.options.get("etw"):
            raise CuckooDisableModule

        if not self.etw_path:
            raise CuckooError(
                "In order to use the etw collecter, it is"
                "required to set the dir path of etw collecter"
                "by the option etw_path"
            )'''

        etw_exe_path = os.path.join(self.etw_path, self.etw_exe_name)
        log.debug(etw_exe_path)
        if not os.path.exists(etw_exe_path):
            raise CuckooPackageError(
                                     "etw collecter doesn't exist"
                                     )

        curdir = os.getcwd()
        os.chdir(self.etw_path)

        # Do clear work for dirs
        self._clear_dir("dumpfile")
        for i in range(len(self.output_dirs)):
            self._clear_dir(self.output_dirs[i])

        # generate address map
        os.system(self.addressmap_exe)

        os.chdir(curdir)


    def _clear_dir(self, path):
        """clear content of the directory"""

        if os.path.exists(path):
            rmtree(path)
        os.mkdir(path)

    def _rename_backup(self, name):
        """rename file with suffix '_backup'"""

        index = name.find("_backup")
        if index != -1:
            return name[0: index] + name[index + 7: len(name)]
        else:
            return name

    def _wait_till_stop(self):
        """wait until etw is stopped successfully"""

        with open(self.collecter_pidfile, "r") as f:
            collecter_pid = int(f.readline())
        while True:
            pid_list = pids()
            if collecter_pid not in pid_list:
                break
            log.debug("Waiting...")
            sleep(3)

    def _stop_collecter(self):
        """simulate the keyboard input to stop etw"""

        def callback(hwnd, extra):
            if win32gui.IsWindowEnabled(hwnd):
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    win32api.keybd_event(13, 0, 0, 0)
                    win32api.keybd_event(13, 0, win32con.KEYEVENTF_KEYUP, 0)
                except:
                    pass
            return True

        win32gui.EnumWindows(callback, None)
        self._wait_till_stop()
        log.debug("Successfully stop the etw collecter")

    '''def _parse_by_pid(self, pid_list):
        """Parse the output.bin and filter by pid"""

        for pid in pid_list:
            pid_output_dir_path = os.path.join(self.output_dir_name, str(pid))
            os.mkdir(pid_output_dir_path)
            call([
                self.parser_name,
                str(pid),
                self.output_bin_name,
                self.addressmap_name,
                pid_output_dir_path
            ])
            log.debug("Successfully parse the output for pid {pid}".format(pid=pid))'''

    def _compress_dir(self, final_result_dir_path):
        """Compress the results as a zip file"""

        archive = ZipFile(self.archive_name, 'w', ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(final_result_dir_path):
            for filename in filenames:
                archive.write(os.path.join(dirpath, filename))
        archive.close()
        log.debug("Successfully compress the final output")

    '''def stop(self):
        """Stop the etw collecter, preprocess the output,
        compress the result and upload the archive"""

        # CD into the path of etw collecter
        curdir = os.getcwd()
        os.chdir(self.etw_path)

        # Stop etw collecter
        call([self.etw_exe_name, "-stop"])
        log.debug("Successfully stop the etw collecter")

        # Keep the type of pids consistent to iterable structure
        pid_list = []
        if not isinstance(self.pids, (tuple, list)):
            pid_list.append(self.pids)
        else:
            pid_list = self.pids

        # Store the main pids generated directly by the submit file
        main_pids_file_path = self.pids_file_name
        with open(main_pids_file_path, "w") as pids_file:
            for pid in pid_list:
                pids_file.write(str(pid))

        # Check which model user want to run,
        # Default set is original
        process_mode = "original"
        if "process_mode" in self.options:
            process_mode = self.options["process_mode"]

        # original : don't parse the output generated by ETW.exe
        # syscall_only : parse the output but only capture the syscall data
        # syscall_plus_events : parse the output and get all the syscall and events data
        process_mode_2_functions = {
            "original": self._keep_original_data,
            "syscall_only": self._keep_syscall_only_data,
            "syscall_plus_events": self._keep_syscall_plus_events_data
        }

        # Process output according to process mode
        process_mode_2_functions[process_mode](pid_list)

        # Return back to the original working path
        os.chdir(curdir)

        # Upload the results to the host
        archive_path = os.path.join(self.etw_path, self.archive_name)
        upload_to_host(archive_path, os.path.join("files", self.archive_name))
        log.debug("Successfully upload to the result server")'''

    def stop(self):
        """Stop the etw collecter, preprocess the output,
        compress the result and upload the archive"""

        curdir = os.getcwd()
        os.chdir(self.etw_path)

        # Stop etw collecter
        self._stop_collecter()

        # Copy output into dumpfile
        for i in range(len(self.backup_files)):
            copy(self.backup_files[i],
                 os.path.join(self.dump_path, self._rename_backup(self.backup_files[i])))
        for i in range(len(self.output_files)):
            os.rename(self.output_files[i], os.path.join(self.dump_path, self.output_files[i]))
        for i in range(len(self.output_dirs)):
            os.rename(self.output_dirs[i], os.path.join(self.dump_path, self.output_dirs[i]))
        sleep(5)

        # Keep the type of pids consistent to iterable structure
        '''pid_list = []
        if not isinstance(self.pids, (tuple, list)):
            pid_list.append(self.pids)
        else:
            pid_list = self.pids

        # Store the main pids generated directly by the submit file
        main_pids_file_path = self.pids_file_name
        with open(main_pids_file_path, "w") as pids_file:
            pids_file.write(str(pid_list))
        os.rename(main_pids_file_path, os.path.join(self.dump_path, main_pids_file_path))'''

        self._compress_dir(self.dump_path)
        os.chdir(curdir)

        # Upload the results to the host
        archive_path = os.path.join(self.etw_path, self.archive_name)
        upload_to_host(archive_path, os.path.join("files", self.archive_name))
        log.debug("Successfully upload to the result server")

