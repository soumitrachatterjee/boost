
import TestCmd
from tree import build_tree, trees_difference
import copy
import fnmatch
import os
import shutil
import string
import types

#
# FIXME: this is copy-pasted from TestSCons.py
# Should be moved to TestCmd.py?
#
if os.name == 'posix':
    def _failed(self, status = 0):
        if self.status is None:
            return None
        if os.WIFSIGNALED(status):
            return None
        return _status(self) != status
    def _status(self):
        if os.WIFEXITED(self.status):
            return os.WEXITSTATUS(self.status)
        else:
            return None
elif os.name == 'nt':
    def _failed(self, status = 0):
        return not self.status is None and self.status != status
    def _status(self):
        return self.status

class Tester(TestCmd.TestCmd):

    def __init__(self):

        self.original_workdir = os.getcwd()

        jam_build_dir = ""
        if os.name == 'nt':
            jam_build_dir = "bin.ntx86"
        elif os.name == 'posix':
            jam_build_dir = "bin.linuxx86"
        else:
            raise "Don't know directory where jam is build for this system"

        TestCmd.TestCmd.__init__(self,
                                 program=os.path.join('..', 'jam_src', jam_build_dir, 'bjam') + ' -d0',
                                 match=TestCmd.match_exact,
                                 workdir='')

        os.chdir(self.workdir)

    #
    # Methods that change working directory's content
    #
    def set_tree(self, tree_location):
        # Seem like it's not possible to remove a directory which is
        # current.
        d = os.getcwd()
        os.chdir(os.path.dirname(self.workdir))
        shutil.rmtree(self.workdir, ignore_errors=0)

        if not os.path.isabs(tree_location):
                tree_location = os.path.join(self.original_workdir, tree_location)
        shutil.copytree(tree_location, self.workdir)

        os.chdir(d)

    def write(self, file, content):
        try:
            os.makedirs(os.path.dirname(file))
        except:
            pass
        open(self.native_file_name(file), "wb").write(content)

    def touch(self, names):
        if not type(names) == types.ListType:
                names = [names]
        for name in names:
                os.utime(self.native_file_name(name), None)


    #
    #   FIXME: Large portion copied from TestSCons.py, should be moved?
    #
    def run_build_system(self, extra_args='', stdout = None, stderr = '', status = 0, **kw):
        self.previous_tree = build_tree(self.workdir)

        try:
            kw['program'] = self.program + ' ' + extra_args
            apply(TestCmd.TestCmd.run, [self], kw)
        except:
            print "STDOUT ============"
            print self.stdout()
            print "STDERR ============"
            print self.stderr()
            raise
        if _failed(self, status):
            expect = ''
            if status != 0:
                expect = " (expected %d)" % status
            print "%s returned %d%s" % (self.program, _status(self), expect)
            print "STDOUT ============"
            print self.stdout()
            print "STDERR ============"
            print self.stderr()
            self.fail_test(1)
        if not stdout is None and not self.match(self.stdout(), stdout):
            print "Expected STDOUT =========="
            print stdout
            print "Actual STDOUT ============"
            print self.stdout()
            stderr = self.stderr()
            if stderr:
                print "STDERR ==================="
                print stderr
            self.fail_test(1)
        if not stderr is None and not self.match(self.stderr(), stderr):
            print "STDOUT ==================="
            print self.stdout()
            print "Expected STDERR =========="
            print stderr
            print "Actual STDERR ============"
            print self.stderr()
            self.fail_test(1)

        self.tree = build_tree(self.workdir)
        self.tree_difference = trees_difference(self.previous_tree, self.tree)
        self.unexpected_difference = copy.deepcopy(self.tree_difference)

    def read(self, name):
        return open(self.native_file_name(name), "wb").read()

    # A number of methods below check expectations with actual difference
    # between directory trees before and after build.
    # All the 'expect*' methods require exact names to be passed.
    # All the 'ignore*' methods allow wildcards.

    # All names can be lists, which are taken to be directory components
    def expect_addition(self, names):
        if type(names) == types.StringType:
                names = [names]
        for name in names:
                try:
                        self.unexpected_difference.added_files.remove(name)
                except:
                        print "File %s not added as expected" % (name,)
                        self.fail_test(1)

    def ignore_addition(self, wildcard):
        ignore_elements(self.unexpected_difference.added_files, wildcard)

    def expect_removal(self, names):
        if type(names) == types.StringType:
                names = [names]
        for name in names:
                try:
                        self.unexpected_difference.removed_files.remove(name)
                except:
                        print "File %s not removed as expected" % (name,)
                        self.fail_test(1)

    def ignore_removal(self, wildcard):
        ignore_elements(self.unexpected_difference.removed_files, wildcard)

    def expect_modification(self, names):
        if type(names) == types.StringType:
                names = [names]
        for name in names:
                try:
                        self.unexpected_difference.modified_files.remove(name)
                except:
                        print "File %s not modified as expected" % (name,)
                        self.fail_test(1)

    def ignore_modification(self, wildcard):
        ignore_elements(self.unexpected_difference.modified_files, wildcard)

    def expect_touch(self, names):
        if type(names) == types.StringType:
                names = [names]
        for name in names:
                try:
                        self.unexpected_difference.touched_files.remove(name)
                except:
                        print "File %s not touched as expected" % (name,)
                        self.fail_test(1)


    def ignore_touch(self, wildcard):
        ignore_elements(self.unexpected_difference.touched_files, wildcard)

    def ignore(self, wildcard):
        ignore_elements(self.unexpected_difference.added_files, wildcard)
        ignore_elements(self.unexpected_difference.removed_files, wildcard)
        ignore_elements(self.unexpected_difference.modified_files, wildcard)
        ignore_elements(self.unexpected_difference.touched_files, wildcard)

    def expect_nothing_more(self):
        if not self.unexpected_difference.empty():
                self.fail_test(1)


    # Helpers
    def mul(self, *arguments):
        if len(arguments) == 0:
                return None
        else:
                here = arguments[0]
                if type(here) == type(''):
                        here = [here]

                if len(arguments) > 1:
                        there = apply(self.mul, arguments[1:])
                        result = []
                        for i in here:
                                for j in there:
                                        result.append(i + j)
                        return result
                else:
                        return here



    # Internal methods
    def ignore_elements(list, wildcard):
        """Removes in-place, element of 'list' that match the given wildcard."""
        w = fnmatch.translate(wildcard)
        list[:] = filter(lambda x, w=w: not w(x), list)

    def native_file_name(self, name):
        elements = string.split(name, "/")
        return apply(os.path.join, [self.workdir]+elements)

class List:

    def __init__(self, s=""):
        # Have to handle espaced spaces correctly
        s = string.replace(s, "\ ", '\001')
        self.l = []
        for e in string.split(s):
            self.l.append(string.replace(e, '\001', ' '))

    def __len__(self):
        return len(l)

    def __getitem__(self, key):
        return self.l[key]

    def __setitem__(self, key, value):
        self.l[key] = value

    def __delitem__(self, key):
        del self.l[key]

    def __coerce__(self, other):
        if isinstance(other, type("")):
            return (self,List(other))
        else:
            return None

    def __str__(self):
        return str(self.l)

    def __repr__(self):
        return ( self.__module__ + '.List('
                 + repr(string.join(self.l, ' '))
                 + ')')
                        
    def __mul__(self, other):
        result = List()
        for f in self:
            for s in other:
                result.l.append(f + s)
        return result

# quickie tests. Should use doctest instead.    
if __name__ == '__main__':
    assert str(List("foo bar") * "/baz") == "['foo/baz', 'bar/baz']"
    assert repr("foo/" * List("bar baz")) == "__main__.List('foo/bar foo/baz')"
    print 'tests passed'




