import colorama
from colorama import Fore

colorama.init(autoreset=True)

status_colors = {
    range(100, 200): Fore.CYAN,
    range(200, 300): Fore.GREEN,
    range(300, 400): Fore.YELLOW,
    range(400, 500): Fore.RED,
    range(500, 600): Fore.MAGENTA,
}


def stat_color(status_code):
    color = Fore.WHITE
    for code_range, code_color in status_colors.items():
        if status_code in code_range:
            color = code_color
    return color
