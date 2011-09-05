import hashlib
import os
import os.path
import shutil
import subprocess
import sys
import unicodedata
    
#---- external processes ----#
def call(args):
    '''
    Blocking process call.
    Takes an list of strings like ['ls', '-l'] and returns the 3-tuple
    (stdout, stderr, returncode).
    '''
    p = subprocess.Popen(args, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE, close_fds=True, shell=False)
    o, e = p.communicate()
    return o.decode('utf-8'), e.decode('utf-8'), p.returncode


def carefulcall(args):
    '''
    Like call but throws ReturnCodeException on non-zero return.
    '''
    (o, e, r) = call(args)
    if not r == 0:
        sys.stderr.write('#' * 80 + '\n')
        sys.stderr.write(e + '\n')
        sys.stderr.write('#' * 80 + '\n')
        raise ReturnCodeException(r)
    return (o, e)


class ReturnCodeException(Exception):
    def __init__(self, retcode):
        self.retcode = retcode
    def __str__(self):
        return repr('return code: ' + self.retcode + '\n')


class MySQL:

    def __init__(self, domain, database, uname, passwd):
        self.domain = domain
        self.database = database
        self.uname = uname
        self.passwd = passwd


    def dbcall(sql):
        args = ['mysql', '-u', self.uname, '-h' + self.url,
                "--password=" + self.passwd, '-D' + self.database,
                '--skip-column-names', '-e']
        (o, e) = carefulcall(args + [sql])
        rows = list(o.splitlines())
        rows = [row.split('\t') for row in rows]
        return (rows, e)


#---- hashing ----#
def md5file(path):
    '''
    Return md5 sum of provided file.
    '''
    with open(path, 'rb') as f:
        md5 = hashlib.md5()
        block_size = 128*md5.block_size
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


#---- file system ----#
LF = '\n'
CR = '\r'
CRLF = '\r\n'

def makepath(*paths):
    '''
    Convenience function for creating a path
    from fragments that never begin or end
    with os.sep.
    '''
    return os.sep.join(paths)


def abswalk(path):
    '''
    Generator returning the absolute path of every file (directory or other)
    under path.
    '''
    path = os.path.abspath(path)
    for (dirpath, dirnames, filenames) in os.walk(path):
        for dirname in dirnames:
            yield os.path.join(path, dirpath, dirname)
        for filename in filenames:
            yield os.path.join(path, dirpath, filename)


#TODO: handle filenames with slashes in them
#TODO: handle cases where normalized file name already exists
def normpath(root, dest):
    '''
    Recursively copies all the files and directories under root to a directory
    of the same name under dest, with normalized paths of lowercase
    alphanumeric names.
    '''
    dest = os.path.abspath(dest)
    assert os.path.exists(dest), dest + ' does not exist'
    paths = [f for f in abswalk(root)]
    paths.sort(key=lambda el: - len(el))
    for path in paths:
        assert os.path.exists(path), path + " doesn't exist"
        assert os.path.isfile(path) or os.path.isdir(path), (
            "can't handle special file: " + path)
        assert path.startswith(root)
        rest = path[len(root):]
        newpath = dest + _normalize(rest)
        print(path + ' --> ' + newpath)
        dirname = os.path.dirname(newpath)
        # if not os.path.exists(dirname):
        #     os.makedirs(dirname)
        # assert os.path.exists(dirname), ('needed directory ' + dirname +
        #                                  ' does not exist')
        # if os.path.isfile(path):
        #     assert not os.path.exists(newpath), newpath + ' already exists'
        # shutil.move(path, newpath)
        # assert os.path.exists(newpath), newpath + ' not created'
        # if os.path.exists(path):
        #     if os.path.isdir(path):
        #         os.rmdir(path)
        #     else:
        #         os.remove(path)
        # assert not os.path.exists(path), path + ' still exists'


def _normalize(fname):
    fname = fname.lower()
    fname = fname.replace(' ', '_')
    specials = ['/', '_', '-', '.']
    goodchars = set(specials + [chr(i) for i in range(97, 123)] +
                    [chr(i) for i in range(48, 58)])
    newname = []
    for char in fname:
        if char not in goodchars:
            nchar = '_' + _normalize(unicodedata.name(char)) + '_'
            newname.append(nchar)
        else:
            newname.append(char)
    newname = ''.join(newname)

    def validate(str):
        for char in str:
            assert char in goodchars, 'bad char ' + char

    validate(newname)
    return newname


def unixperm(path):
    '''
    Return unix permissions as a 3-tuple of ints.
    For example, (7, 5, 5).
    '''
    permstr = oct(os.stat(path).st_mode)[-3:]
    return (int(permstr[0]), int(permstr[1]), int(permstr[2]))
