# Copyright (C) 2017 rainkin1993
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from zipfile import ZipFile
from subprocess import call
from lib.common.abstracts import Auxiliary
from lib.common.exceptions import CuckooPackageError, CuckooDisableModule, CuckooError
from lib.common.results import upload_to_host


class ETWTraceCollecter(Auxiliary):
    """Allow ETWTraceCollecter to be run on the side."""

    def __init__(self, options={}, analyzer=None):
        super(ETWTraceCollecter, self).__init__(options, analyzer)

        self.etw_path = self.options.get("etw_path")

        self.output_dir_name = "output"
        self.corrected_output_dir_name = "corrected_output"
        self.etw_exe_name = "ETW.exe"
        self.output_bin_name = "output.bin"
        self.addressmap_name = "addressmap"
        self.archive_name = "output.zip"
        self.preprocess_script_name = "new_preTreat.py"
        self.parser_name = "parse_cdm_runqing.exe"

    def start(self):
        """Start the etw collecter"""
        if not self.options.get("etw"):
            raise CuckooDisableModule
        
        if not self.etw_path:
            raise CuckooError(
                "In order to use the ETWTraceCollecter, it is"
                "required to set the dir path of ETWTraceCollecter"
                "by the option etw_path"
            )

        etw_exe_path = os.path.join(self.etw_path, self.etw_exe_name)

        if not os.path.exists(etw_exe_path):
            raise CuckooPackageError(
                                     "ETW.exe doesn't exist"
                                     )

        '''
        # Register the msdia120.dll         
        tempdir = os.path.join(bin_path, "res")
        os.chdir(tempdir)
        res = os.system("regsvr32 msdia120.dll")
        res = subprocess.Popen("regsvr32 msdia120.dll", shell = True)
        time.sleep(0.1)
        res.kill()
        os.chdir(curdir)
        '''

        # Start etw collecter in the background.
        curdir = os.getcwd()
        os.chdir(self.etw_path)
        call([self.etw_exe_name, "-start"])
        os.chdir(curdir)

    def stop(self):
        """Stop the etw collecter, preprocess the output,
        compress the result and upload the archive"""

        # CD into the path of etw collecter
        curdir = os.getcwd()
        os.chdir(self.etw_path)

        # Stop etw collecter
        call([self.etw_exe_name, "-stop"])

        # Keep the type of pids consistent to iterable structure
        pid_list = []
        if not isinstance(self.pids, (tuple, list)):
            pid_list.append(self.pids)
        # Parse the output.bin and filter by pid
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

        # Correct the wrong format data
        call([
            "python",
            self.preprocess_script_name,
            self.output_dir_name,
            self.corrected_output_dir_name
        ])

        # Compress the results as a zip file
        archive_path = os.path.join(self.etw_path, self.archive_name)
        archive = ZipFile(archive_path, 'w')
        for dirpath, dirnames, filenames in os.walk(self.corrected_output_dir_name):
            for filename in filenames:
                archive.write(os.path.join(dirpath, filename))
        archive.close()

        # Return back to the original working path
        os.chdir(curdir)

        # Upload the results to the host
        upload_to_host(archive_path, os.path.join("files", self.archive_name))


