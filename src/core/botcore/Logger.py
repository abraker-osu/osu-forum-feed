import logging
import traceback
import config
import pathlib


class Logger(logging.getLoggerClass()):

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level=logging.DEBUG)

        formatter = logging.Formatter('%(levelname)s  %(asctime)s   [ %(name)s ] %(message)s')
        
        self.sh = logging.StreamHandler()
        self.sh.setFormatter(formatter)

        if 'db' in config.runtime_mode: self.sh.setLevel(logging.DEBUG)
        else:                           self.sh.setLevel(logging.INFO)
        
        self.addHandler(self.sh)

        # \TODO: Maybe break up the logging file if it goes over 1MB
        #   get file size
        #   if over 1MB, then rename current logging file to '{start_date}_{end_date}_{logger_name}.log'
        #   cut-paste into logging folder named '{logger_name}'

        self.fh = logging.FileHandler(str(config.log_path / (name + '.log')))
        self.fh.setFormatter(formatter)
        self.fh.setLevel(logging.INFO)
        self.addHandler(self.fh)


    def __del__(self):
        self.sh.close(); self.removeHandler(self.sh)
        self.fh.close(); self.removeHandler(self.fh)


    # \FIXME: https://osu.ppy.sh/forum/t/772528 <- this thread's title has characters which break logger encoding; Error report: https://i.imgur.com/pFmcQvB.png
    '''
    def error(self, msg):
        msg = msg.strip()
        if msg == 'None' or msg == 'N/A' or len(msg) == 0: 
            self.exception(msg)
        else:
            self.error(msg)

    
    def critical(self, msg):
        msg = msg.strip()
        if msg == 'None' or msg == 'N/A' or len(msg) == 0: 
            self.exception(msg)
        else:
            self.critical(msg)
    '''

    
    def exception(self, msg):
        msg = msg.strip()
        msg += '\n' + traceback.format_exc()
        self.critical(msg)