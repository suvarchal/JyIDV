from ipykernel.kernelbase import Kernel
from IPython.utils.path import locate_profile
from pexpect import replwrap,EOF,spawn
import signal
import re
import os
from distutils.spawn import find_executable
import sys

from IPython.display import Image
from glob import glob
import tempfile
import random
from shutil import rmtree
from base64 import b64encode

from itertools import cycle
__version__ = '0.9.1'

class JythonKernel(Kernel):
    implementation = 'IDV Kernel'
    implementation_version = __version__
    language = 'jython'
    language_version = '2.7.0'
    language_info = {'mimetype': 'text/x-python','name':'jython','file_extension':'.py','codemirror_mode':{'version':2,'name':'text/x-python'},'pygments_lexer':'python','help_links':[{'text':'Jython', 'url': 'www.jython.org'},{'text':'Jython Kernel Help','url':'https://github.com/suvarchal/IJython'}]}
    banner = "IDV Kernel"

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_jython()

        try:
            self.hist_file = os.path.join(locate_profile(),'jython_kernel.hist')
        except:
            self.hist_file = None
            self.log.warn('No default profile found, history unavailable')

        self.max_hist_cache = 500
        self.hist_cache = []

    def _start_jython(self):
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        #for some reason kernel needs two excepts with jython executable so using only jython.jar
        try:
            if "IDV_HOME" in os.environ:
               #self._executable=os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"
               if find_executable(os.environ['IDV_HOME']+"/jre/bin/java"):
                   self._executable=os.environ['IDV_HOME']+"/jre/bin/java"
               elif find_executable(os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"):
                   self._executable=os.environ['IDV_HOME']+"/jre.bundle/Contents/Home/jre/bin/java"
               else:
                   self._executable="java"

               liblist=["idv.jar","ncIdv.jar","external.jar","visad.jar","jython.jar"]
               libs=libs=":".join([os.environ['IDV_HOME']+"/"+lib for lib in liblist])
               opts=" -Xmx2048m -XX:+DisableExplicitGC -Didv.enableStereo=false -cp "+libs+" org.python.util.jython -i "+os.environ['IDV_HOME']+"/.jythonrc.py"
               self._executable=self._executable+opts
            else:
               raise Exception("IDV_HOME not found")

            self._child  = spawn(self._executable,timeout = None)
#            self.jywrapper = replwrap.REPLWrapper(self._child,u">>> ",prompt_change=None,new_prompt=u">>> ",continuation_prompt=u'... ')
            #rows, cols = map(int, os.popen('stty size', 'r').read().split())
 #           self._child.setwinsize(300,400)
            self._child.waitnoecho(True)
            self._child.expect(u">>> ")
            self._child.setwinsize(600,400)
        finally:
            signal.signal(signal.SIGINT, sig)


    def do_execute(self, code, silent, store_history=False, user_expressions=None,
                   allow_stdin=False):
        code   =  code.strip()
        abort_msg = {'status': 'abort',
                     'execution_count': self.execution_count}
        interrupt = False
        doDisplay = False
        try:
            if code.strip().startswith("#show"):
                plot_opts=""
                if len(code.strip().lstrip("#").strip('()').split('(')[1][1:-1])>1:
                   plot_opts=code.strip().lstrip("#").strip('()').split('(')[1][1:-1]
                plot_dir = tempfile.mkdtemp(dir=os.path.expanduser("~"))
                plot_file=","+plot_dir+"/"+"plot_"+str(random.randint(1000, 9999))+".png"
                output = self.jyrepl("getImage();writeImage('"+plot_file+"','"+plot_opts+"')", timeout=None)
                if not len(glob("%s/*.png" % plot_dir))==0:
                   images = [open(imgfile, 'rb').read() for imgfile in glob("%s/*.png" % plot_dir)]
                   display_data = []

                   for image in images:
                       display_data.append({'image/png': b64encode(image).decode('ascii')})
                   doDisplay=True
            elif code.strip().startswith("showMovie"):
                plot_dir = tempfile.mkdtemp(dir=os.path.expanduser("~"))
                plot_file="plot_"+str(random.randint(1000, 9999))+".gif"
                plot_file=os.path.join(plot_dir,plot_file)
                cmd='idv.waitUntilDisplaysAreDone();writeMovie('+repr(plot_file)+')'
                self.jyrepl(cmd)
                if not len(glob("%s/*.gif" % plot_dir))==0:
                    gifimages = [open(imgfile, 'rb').read() for imgfile in glob("%s/*.gif" % plot_dir)]
                display_data = []
                for image in gifimages:
                       display_data.append({'image/png': b64encode(image).decode('ascii')})
                rmtree(plot_dir)
                #### below works when showMovie imagefile
                #plot_file=code.strip("showMovie").strip()
                #display_data = []
                #if os.path.isfile(plot_file):
                #   gifimage = open(plot_file, 'rb').read()
                #   display_data.append({'image/png': b64encode(gifimage).decode('ascii')})
                doDisplay=True
            else:
                output = self.jyrepl(code, timeout=None)
                if output.lstrip().startswith("{"):
                    out=eval(output.strip())
                    display_data=[]
                    display_data.append({'image/png': out['data']})
                    doDisplay=True
                else:
                    output = '\n'.join([line for line in output.splitlines()])+'\n'
        except KeyboardInterrupt:
            self._child.sendintr()
            output = self._child.before+'\n Got interrupt: Current Jython doenst support Interrupting ...so Restarting.....'
            interrupt = True
            #self.jyrepl("exit()")
            #self._start_jython()
        except EOF:
            output = self._child.before + 'Reached EOF Restarting Jython'
            self._start_jython()
        if not silent and not doDisplay:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        if not silent and  doDisplay:
            for data in display_data:
                self.send_response(self.iopub_socket, 'display_data',{'data':data,'metadata':{}})
        #doDisplay=True
        #if doDisplay:
          # print("i am in Display")
          # plot_dir = "/home/suvarchal" #tempfile.mkdtemp(dir=os.path.expanduser("~"))
          # plot_file=plot_dir+"/"+"plot_"+str(random.randint(1000, 9999))+".png"
           #plot_opts=display_code.strip('()')
           #output = self.jywrapper.run_command("getImage();writeImage('"+plot_file+"')", timeout=None)
           #if not len(glob("%s/plot_jumbo.png" % plot_dir))==0:
              #print("found plot")
              #images = [open(imgfile, 'rb').read() for imgfile in glob("%s/plot_jumbo.png" % plot_dir)]
              #display_data = []

              #for image in images:
              #    print(image)
              #    display_data.append({'image/png': b64encode(image).decode('ascii')})

              #for data in display_data:
              #    self.send_response(self.iopub_socket, 'display_data',{'data':data,'metadata':{}})
        if code.strip() and store_history:
            self.hist_cache.append(code.strip())
            #rmtree(plot_dir)
        if interrupt:
            return {'status': 'abort', 'execution_count': self.execution_count}

        return {'status': 'ok','execution_count': self.execution_count,'payload': [],'user_expressions': {}}
    def do_complete(self, code, cursor_pos):
        code = code[:cursor_pos]
        default = {'matches': [], 'cursor_start': 0,
                   'cursor_end': cursor_pos, 'metadata': dict(),
                   'status': 'ok'}

        if not code or code[-1] == ' ':
            return default

        tokens = code.split()
        if not tokens:
            return default
        token = tokens[-1]
        start = cursor_pos - len(token)

#        if len(re.split(r"[^\w]",token)) > 1:
#            cmd="dir("+re.split(r"[^\w]",token)[-2]+")"
#            output=self.jyrepl(cmd,timeout=None)
#            matches.extend([e for e in re.split(r"[^\w]",output)[:] if not e.strip()=="" and not e.strip().startswith("__")])
 #           token=re.split(r"[^\w]",token)[-1]
 #           start = cursor_pos - len(token)
 #       else:
 #           cmd=("import sys;sys.builtins.keys()")
 #           output=self.jyrepl(cmd,timeout=None)
 #           matches.extend([e for e in re.split(r"[^\w]",output)[:] if not e.strip()=="" and not e.strip().startswith("__")])
        #self._child.send(code.strip()+'\t')
        #self._child.expect(u">>> ",timeout=None)
        #self._child.expect(u">>> ",timeout=None)
        #output=self._child.before
        matches=[]
        code='do_complete('+repr(code)+')'
        output=self.jyrepl(code)
        if len(output)>1:    matches.extend(eval(output))
    #matches.extend([e for e in re.split(r"[^\w]",output)[:] if not e.strip()=="" and not e.strip().startswith("__")])
        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}


    def do_history(self,hist_access_type,output,raw,session=None,start=None,stoop=None,n=None,pattern=None,unique=None):
        if not self.hist_file:
            return {'history':[]}
        if not os.path.exists(self.hist_file):
            with open(self.hist_file, 'wb') as f:
                f.write('')

        with open(self.hist_file, 'rb') as f:
            history = f.readlines()

        history = history[:self.max_hist_cache]
        self.hist_cache = history
        self.log.debug('**HISTORY:')
        self.log.debug(history)
        history = [(None, None, h) for h in history]

        return {'history': history}

    def do_inspect(self,code,cursor_pos,detail_level=1):
        found=False
        default={'status':'ok', 'found': False,
                'data': dict(), 'metadata': dict()}

        if not code or code[-1] == ' ':
            return default


        #if len(re.split(r"[^\w]",token)) > 1:
        #    cmd="dir("+re.split(r"[^\w]",token)[-2]+")"
        #    output=self.jyrepl(cmd,timeout=None)
        #    matches.extend([e for e in re.split(r"[^\w]",output)[:] if not e.strip()=="" and not e.strip().startswith("__")])
        #    token=re.split(r"[^\w]",token)[-1]
        #    start = cursor_pos - len(token)
        #else:
        #    cmd=("import sys;sys.builtins.keys()")
        #    output=self.jyrepl(cmd,timeout=None)
        #    matches.extend([e for e in re.split(r"[^\w]",output)[:] if not e.strip()=="" and not e.strip().startswith("__")])

        code='do_inspect('+repr(code)+')'
        data=self.jyrepl(code)
        try:
            data=eval(data)
            found=True
        except:
            found=False

        return {'status':'ok', 'found': found,
                'data': {'text/plain':data}, 'metadata': dict()}
    def do_shutdown(self,restart):
        #self.send("exit()")
        self._child.kill(signal.SIGKILL)
        return {'status':'ok', 'restart':restart}
    def jyrepl(self,code,timeout=None):
        out=""
        indents=cycle(map(lambda x: len(x)-len(x.lstrip()),code.splitlines()))
        indents.next()
        for line in code.splitlines():
            #print str(ln+1)+" code is "+line
            self._child.sendline(line)
            now_prompt=self._child.expect_exact([u">>> ",u"... "])
            now_prompt=self._child.expect_exact([u">>> ",u"... "])
            if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'#for clean outputs
            curr_indent=len(line)-len(line.lstrip())
            if not curr_indent==indents.next() and now_prompt==1: #should take care of last line and loops but not loops
                self._child.send(u'\n')
                now_prompt=self._child.expect_exact([u">>> ",u"... "])
                now_prompt=self._child.expect_exact([u">>> ",u"... "])
                if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
#        if now_prompt==1:
#            self._child.send(u'\n')
#            now_prompt=self._child.expect_exact([u">>> ",u"... "])
#            now_prompt=self._child.expect_exact([u">>> ",u"... "])
#            if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'

# Below is way to go in future gives line numbers for errors, simple but eval doesnt evaluate one line x=1
#but exec doesnt return objects, problematic for functions like getImage or anything that returns data or just typing
#object doesnt produce the object
#        if len(code.splitlines())==1:
#            out=""
#            code='eval('+repr(code.strip())+')'
#            self._child.sendline(code)
#            now_prompt=self._child.expect_exact([u">>> ",u"... "])
#            now_prompt=self._child.expect_exact([u">>> ",u"... "])
#            if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
#        else:
#            out=""
#            code='exec('+repr(code)+')'
#            for line in code.splitlines():
#                self._child.sendline(line)
#                now_prompt=self._child.expect_exact([u">>> ",u"... "])
#                now_prompt=self._child.expect_exact([u">>> ",u"... "])
#                if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
        return out
if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JythonKernel)
