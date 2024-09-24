"""
Overrides any and all loggers
"""

if 'global_loger' not in globals():
    globals()['global_logger'] = True

    import sys
    import logging

    class ColorFormatter(logging.Formatter):
        """
        Colorizes log messages
        """

        grey     = '\x1b[38;20m'
        white    = '\x1b[37;20m'
        yellow   = '\x1b[33;20m'
        green    = '\x1b[32;20m'
        red      = '\x1b[31;20m'
        bold_red = '\x1b[31;1m'
        reset    = '\x1b[0m'

        rgb = lambda r, g, b: f'\x1b[38;2;{r};{g};{b}m'

        FORMATS = {
            logging.DEBUG: f'   {rgb(100, 100, 100)}%(levelname)s  %(asctime)s  [ %(name)s ] %(message)s{reset}',
            logging.INFO: f'    {green}%(levelname)s{reset}  %(asctime)s  [ %(name)s ] {grey}%(message)s{reset}',
            logging.WARNING: f' {yellow}%(levelname)s{reset}  %(asctime)s  [ %(name)s ] {grey}%(message)s{reset}',
            logging.ERROR: f'   {rgb(200, 100, 100)}%(levelname)s  %(asctime)s  [ %(name)s ] %(message)s{reset}',
            logging.CRITICAL: f'{bold_red}%(levelname)s{reset}  {rgb(200, 50, 50)}%(asctime)s  [ %(name)s ] %(message)s{reset}'
        }

        def format(self, record: logging.LogRecord) -> str:
            """
            Formatter override
            """
            return logging.Formatter(self.FORMATS[record.levelno]).format(record)


    class Logger(logging.Logger):
        """
        A logger set to have a polled stream handler and colorized formatter (windows only)
        """
        def __init__(self, name: str = '', level: int = logging.DEBUG):
            logging.Logger.__init__(self, name, level=level)

            self.__sh = logging.StreamHandler()

            is_win = sys.platform == 'win32'
            if is_win:
                self.__sh.setFormatter(ColorFormatter())
            else:
                self.__sh.setFormatter(logging.Formatter('%(levelname)s  %(asctime)s   [ %(name)s ] %(message)s'))

            self.addHandler(self.__sh)


    logging.setLoggerClass(Logger)
    logging.getLogger = Logger
