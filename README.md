# perl_io
Open a file or pipe in the Perl style

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
