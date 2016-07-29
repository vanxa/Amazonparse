from distutils.core import setup
import py2exe, sys, os, PIL, bs4, urllib, urllib3

sys.argv.append('py2exe')
bs4_file = bs4.__file__
bs4_loc = bs4_file.rsplit("\\",1)[0]
if bs4_loc not in sys.path:
    sys.path.append(bs4_loc)
    
print(sys.path)
setup(
    options = {
                    'py2exe': {
 #                           'bundle_files': 3,
                            'optimize': 0,
                            'packages' : ['PIL','urllib3','bs4'],
                            'excludes': ['pkg_resources','doctest', 'pdb','jsonschema', 'tornado', 'setuptools', 'distutils', 'matplotlib']
                    }
               },
    console = [{'script': 'azparser/productparser.py'}],
)