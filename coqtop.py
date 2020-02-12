import re, os, subprocess, threading

def find_coqtop():
    for path in [os.path.join(entry, 'coqtop') for entry in os.get_exec_path()]:
        if os.access(path, os.X_OK):
            return path

class Coqtop:
    def __init__(self, manager, path, args=[], debug=True):
        self.debug = debug

        if self.debug:
            print('coq: running ' + path)

        self.manager = manager
        self.proc = subprocess.Popen([path, "-emacs"] + args,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            stdin =subprocess.PIPE,
            bufsize=0)

        self.out_thread = threading.Thread(target=self.receive)
        self.out_thread.daemon = True
        self.out_thread.start()

    def kill(self):
        if self.debug:
            print('coq: killing')

        self.proc.kill()

    def receive(self):
        while True:
            buf = b''

            while not buf.endswith(b'</prompt>'):
                try:
                    chunk = self.proc.stdout.read(65536)
                    if len(chunk) == 0:
                        return
                    buf += chunk
                except IOError as e:
                    buf += str(e)

            buf = re.sub(rb'\A\n*<prompt>.*</prompt>|[\xfe\xff]', b'', buf, flags=re.S)
            buf = buf.decode('utf-8')
            if buf.find('\n') == -1:
                output = ''
                prompt = buf
            else:
                (output, prompt) = buf.rsplit('\n', 1)

            if self.debug:
                print('coq-> ' + output.strip())
                print('coq:> ' + prompt.strip())

            output = re.sub(r'<infomsg>\n?|\n?</infomsg>', '', output)
            output = re.sub(r'<warning>\n?|\n?</warning>', '', output)
            self.manager.receive(output, prompt)

    def send(self, statement):
        if self.debug:
            print('->coq ' + statement)
        self.proc.stdin.write((statement + '\n').encode('utf-8'))
        self.proc.stdin.flush()
