
import os

class Utils:

    # Thanks https://gist.github.com/amitsaha/5990310
    @staticmethod
    def tail(lines, fname):
        bufsize = 8192
        fsize   = os.stat(fname).st_size
        iter    = 0

        if fsize < 1: return ''

        with open(fname) as f:
            if bufsize > fsize: bufsize = fsize - 1

            data = []
            while True:
                iter +=1
                f.seek(fsize-bufsize*iter)
                data.extend(f.readlines())

                print(len(data))
                if len(data) >= lines or f.tell() == 0:
                    return ''.join(data[-lines:])
