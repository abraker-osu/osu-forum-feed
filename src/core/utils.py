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


    @staticmethod
    def wrap(lst: list, idx: int, num: int | type[None] = None) -> list:
        """
        Produces a shifted list slice view. If the view has
        more elements than the list or reaches the end of
        the list, the view wraps around

        lst : list
            List to produce the view on

        idx : int
            The index in `lst` to have the view start on (become the new 0 idx)

        num : int | None
            Number of elements the view has.
        """
        lst_len = len(lst)
        if isinstance(num, type(None)):
            num = lst_len
        return [ lst[(i + idx) % lst_len] for i in range(num) ]


    @staticmethod
    def wrap_idx(lst_len: int, idx: int, num: int | type[None] = None) -> list:
        """
        Produces a shifted list slice view by index. If the view has
        more elements than the list or reaches the end of
        the list, the index wraps around

        lst_len : int
            Size of the entire list

        idx : int
            The index in `lst` to have the view start on (become the new 0 idx)

        num : int | None
            Number of elements the view has.
        """
        if isinstance(num, type(None)):
            num = lst_len

        return [ (i + idx) % lst_len for i in range(num) ]
