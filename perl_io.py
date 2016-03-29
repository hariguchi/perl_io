r''' perl_io - Opens a file or pipe in the Perl style

Copyright (c) 2016 Yoichi Hariguchi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Usage:
  from perl_io import PerlIO

  Example 1:
    pio = PerlIO('/proc/meminfo')   # open `/proc/meminfo' for input

  Example 2:
    pio = PerlIO('> /tmp/foo.txt')  # open '/tmp/foo.txt' for output

  Example 3:
    pio = PerlIO('>> /tmp/foo.txt') # open '/tmp/foo.txt' for appending

  Example 4:
    pio = PerlIO('| cmd arg1 ...')  # we pipe output to the command `cmd'

  Example 5:
    pio = PerlIO('cmd arg1 ... |')  # execute `cmd' that pipes output to us

  You can access the Python file object as `pio.fo' after
  PerlIO object `pio' was successfully created. `pio.fo' is
  set to `None' if PelIO failed to open a file or pipe.

  Example6 : Read the output of `strings /usr/bin/python' from a pipe
    with PerlIO('strings /usr/bin/python |') as pio:
        for line in pio.fo.xreadlines():
            #
            # do something...
            #

  Example7 : Write to a file
    with PerlIO('>/tmp/.tmpfile-%d' % (os.getpid())) as pio:
        print >> pio.fo, 'This is an example'
        pio.fo.write('This is another example')
        pio.fo.write('\n')

  Note: PerlIO parses the parameter as follows in the case it
  indicates to input from or output to a pipe.
    1. Strips the first or last `|' (which indicates to open a pipe)
    2. If the remaining string includes shell special characters
       like `|', `>', `;', etc.,  PerlIO calls Popen() with
       "sh -c 'remaining_string'", which means it can be a security
       hazard when the remaining string includes the unsanitized input
       from an untrusted source.
    3. If the remaining string includes no shell special characters,
       PerlIO does not invoke shell when it calls Popen().

 How to test:
  python -m unittest -v perl_io

'''

import os
import platform
import re
import sys
import syslog
import time
import subprocess
import shlex
import unittest


class PerlIO:
    def __init__(self, open_str):
        self._fo = None
        self._proc = None
        open_str = open_str.strip()
        if open_str[-1] == '|':
            self._rd_open_pipe(open_str[:-1])
        elif open_str[0] == '|':
            self._wr_open_pipe(open_str[1:])
        elif open_str[0] == '>':
            if open_str[1] == '>':
                self._open_file(open_str[2:], 'a')
            else:
                self._open_file(open_str[1:], 'w')
        elif open_str[0] == '<':
            self._open_file(open_str[1:], 'r')
        elif open_str[0:2] == '+>' or open_str[0:2] == '+<':
            self._open_file(open_str[2:], 'r+')
        elif open_str == '-':
            self._fo = sys.stdin
        elif open_str == '>-':
            self._fo = sys.stdout
        else:
            self._open_file(open_str, 'r')

    def __enter__(self):
        return self

    def __exit__(self, type, val, traceback):
        self.close()

    def _parse_command(self, cmd):
        m = re.search(r'(\||<|>|`|;)', cmd)
        if m:
            return "sh -c '" + cmd + "'"
        return cmd

    def _rd_open_pipe(self, cmd):
        try:
            cmd = self._parse_command(cmd)
            self._proc = subprocess.Popen(shlex.split(cmd),
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            self._fo = self._proc.stdout
        except IOError:
            print >> sys.stderr, 'failed to open pipe from %s' % (cmd)

    def _wr_open_pipe(self, cmd):
        try:
            cmd = self._parse_command(cmd)
            self._proc = subprocess.Popen(shlex.split(cmd),
                                          stdin=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            self._fo = self._proc.stdin
        except IOError:
            print >> sys.stderr, 'failed to open pipe to %s' % (cmd)

    def _open_file(self, file, mode):
        file = file.strip()
        try:
            self._fo = open(file, mode)
        except IOError:
            print >> sys.stderr, 'failed to open %s' % (file)

    @property
    def fo(self):
        return self._fo

    @property
    def err_fo(self):
        return self._proc.stderr

    def close(self):
        if self._proc == None:
            self._fo.close()
        else:
            self._proc.communicate()


class TestPerlIO(unittest.TestCase):
    def runTest(self):
        file = self.file_test(False)
        self.rd_pipe_test(file)
        self.rd_pipe_shell_test()
        self.wr_pipe_test()
        os.remove(file)

    #
    # 1. Open a file to write using PerlIO
    # 2. Open a pipe outputting to us with a complex command line
    #    PerlIO('strings `which ls` | sort | uniq | ')
    #    so that shell is invoked with Popen().
    # 3. Write all the input to the file created in No. 1
    # 4. Check the contents
    #
    def rd_pipe_shell_test(self):
        file = '/tmp/.pio_pipe_rd_test-%d' % (os.getpid())
        pio_wr = PerlIO('> %s' % (file))
        self.assertNotEqual(pio_wr.fo, None)
        ll = []
        cmd = 'strings `which ls` | sort | uniq | '
        print >> sys.stderr, \
            'Read from pipe (multiple commands): %s' % (cmd)
        with PerlIO(cmd) as pio:
            for line in pio.fo.xreadlines():
                line = line.strip()
                ll.append(line)
                print >> pio_wr.fo, line
        pio_wr.close()
        pio_rd = PerlIO(file)
        self.assertNotEqual(pio_rd.fo, None)
        for line in pio_rd.fo.xreadlines():
            line = line.strip()
            expected = ll.pop(0)
            self.assertEqual(line, expected)
        os.remove(file)

    #
    # 1. Open a pipe to write with a complex command line
    #    PerlIO('| cat > /tmp/.pio_pipe_rt_test-XXXX')
    #    so that shell is invoked with Popen().
    #    The output to the pipe is redirected to a file
    # 2. Open the file to read using PerlIO
    # 3. Check the contents
    #
    def wr_pipe_test(self):
        m = re.search(r'CYGWIN', platform.system())
        if m:
            #
            # test fails on cygwin
            #
            return
        file = '/tmp/.pio_pipe_wr_test-%d' % (os.getpid())
        cmd = '| cat > %s' % (file)
        print >> sys.stderr, 'Write to pipe: %s' % (cmd)
        pio = PerlIO(cmd)
        self.assertNotEqual(pio.fo, None)
        ll = []
        for i in range (0, 100):
            line = "%4d %4d %4d %4d %4d" % (i, i, i, i, i)
            ll.append(line)
            print >> pio.fo, line
        pio.close()
        pio_rd = PerlIO(file)
        self.assertNotEqual(pio_rd.fo, None)
        for line in pio_rd.fo.xreadlines():
            line = line.rstrip()
            expected = ll.pop(0)
            self.assertEqual(line, expected)
        os.remove(file)

    def file_test(self, remove):
        #
        # pio = PerlIO('>/tmp/.fileTest-pid')
        #
        file = '/tmp/.fileTest-%d' % os.getpid()
        ofile = '> ' + file
        print >> sys.stderr, '\n\nWrite to file: %s' % (ofile)
        pio = PerlIO(ofile)
        if pio.fo == None:
            print >> sys.stderr, ' Error: failed to open %s' % file
            sys.exit(1)
        else:
            for i in range (0, 500):
                print >> pio.fo, '%4d %4d %4d %4d %4d' % (i, i, i, i, i)
            pio.close()
            #
            # Append test ('>>/tmp/.fileTest-pid')
            #
            ofile = ' >> ' + file
            print >> sys.stderr, 'Append to file: %s' % (ofile)
            pio = PerlIO(ofile)
            if pio.fo == None:
                print >> sys.stderr, ' Error: failed to open %s' % file
                sys.exit(1)
            else:
                for i in range (500, 1000):
                    print >> pio.fo, '%4d %4d %4d %4d %4d' % (i, i, i, i, i)
            pio.close()
            #
            # Read the file just created and check the contents
            #
            print >> sys.stderr, 'Read from file: %s' % (file)
            pio = PerlIO(file)
            i = 0
            for line in pio.fo.xreadlines():
                line = line.rstrip()
                expected = '%4d %4d %4d %4d %4d' % (i, i, i, i, i)
                i += 1
                self.assertEqual(line, expected)
            pio.close()
            if remove == True:
                os.remove(file)

        return file
            
    #
    # Read from a pipe with a simple command line
    # so that shell is not invoked with Popen().
    # Confirm the contents of the file is correct.
    # Must be called after file_test().
    #
    def rd_pipe_test(self, file):
        cmd = ' cat %s | ' % (file)
        print >> sys.stderr, 'Read from pipe: %s' % (cmd)
        i = 0
        with PerlIO(cmd) as pio:
            for line in pio.fo.xreadlines():
                line = line.rstrip()
                expected = '%4d %4d %4d %4d %4d' % (i, i, i, i, i)
                i += 1
                self.assertEqual(line, expected)

