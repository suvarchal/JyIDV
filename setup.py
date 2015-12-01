from distutils.command.install import install
from distutils import log
import sys
import os
import json

from distutils.spawn import find_executable
import subprocess

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


kernel_json = {
    "argv": [sys.executable,
	     "-m", "jyidv_kernel",
	     "-f", "{connection_file}"],
    "display_name": "IDV",
    "language": "python",
    "name": "jyidv_kernel",
}


class install_with_kernelspec(install):

    def run(self):
        install.run(self)
        user = '--user' in sys.argv
        try:
            from jupyter_client.kernelspec import install_kernel_spec
        except ImportError:
            from IPython.kernel.kernelspec import install_kernel_spec
        from IPython.utils.tempdir import TemporaryDirectory
        with TemporaryDirectory() as td:
            os.chmod(td, 0o755)  # Starts off as 700, not user readable
            with open(os.path.join(td, 'kernel.json'), 'w') as f:
                json.dump(kernel_json, f, sort_keys=True)
            log.info('Installing kernel spec')
            kernel_name = kernel_json['name']
            try:
                install_kernel_spec(td, kernel_name, user=user,
                                    replace=True)
            except:
                install_kernel_spec(td, kernel_name, user=not user,
                                    replace=True)

svem_flag = '--single-version-externally-managed'
if svem_flag in sys.argv:
    sys.argv.remove(svem_flag)

#check for jython version
try:
    if "IDV_HOME" in os.environ:
               #self._executable=os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"
        if find_executable(os.environ['IDV_HOME']+"/jre/bin/java"):
            executable=os.environ['IDV_HOME']+"/jre/bin/java"
        elif find_executable(os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"):
            executable=os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"
        else:
            raise Exception("Set environment variable IDV_HOME to IDV installation directory before you continue installation") 
        jythonver=subprocess.check_output([executable,"-jar",os.environ['IDV_HOME']+"/jython.jar","--version"],stderr=subprocess.STDOUT)
        jythonver=int(jythonver.strip().split()[-1][1:-1][1])
        if jythonver < 7:
            raise Exception("Current IDV version not compatable.\nThis tool requires IDV version 5.2 or above.")
        try:
            import filecmp
            import shutil
            JySRCfile=os.path.join(os.getcwd(),"jythonrc.py")
            JyDSTfile=os.path.join(os.environ['IDV_HOME'],".jythonrc.py")
            shutil.copy(JySRCfile,JyDSTfile)
        except IOError:
            if os.path.isfile(jyDSTfile) and filecmp.cmp(JySRCfile,JyDSTfile):
                pass
            elif os.path.isfile(jyINSfile) and not filecmp.cmp(JySRCfile,JyDSTfile):
                print("Cannot copy Jython utilities file to IDV_HOME, using existing older version, notebook can behave unpredictable!!")
            else:
                raise Exception("Permission denied to copy Jython utilities for IDV_HOME")
except Exception as e:
    print(e) 
    sys.exit()   
with open('jyidv_kernel.py') as fid:
    for line in fid:
        if line.startswith('__version__'):
            version = line.strip().split()[-1][1:-1]
            break
setup(name='jyidv_kernel',
      description='A IDV notebook kernel for Jupyter/IPython',
      version=version,
      url="https://github.com/suvarchal/JyIDV",
      author='Suvarchal Kumar Cheedela',
      author_email='suvarchal.kumar@gmail.com',
      py_modules=['jyidv_kernel'],
      license="MIT",
      cmdclass={'install': install_with_kernelspec},
      install_requires=["IPython >= 3.0","Jupyter","pexpect"],
      classifiers=[
          'Framework :: IPython',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Jython :: 2',
          'Programming Language :: Python :: 2',
          'Topic :: System :: Shells',
      ]
)
