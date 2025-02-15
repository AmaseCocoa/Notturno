import logging

import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.WHITE + Style.BRIGHT + Fore.RED,
    }

    def format(self, record: logging.LogRecord):
        levelname = record.levelname
        color = self.COLORS.get(levelname, Fore.WHITE)
        level_length = len(levelname)
        padding = 8 - level_length
        pad = f"{' ' * padding}"
        record.levelname = f"[{color}{record.levelname}{Style.RESET_ALL}]{pad}"
        return super().format(record)


logger = logging.getLogger("notturno")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = ColoredFormatter("%(levelname)s %(message)s")
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
