# Functions to display progress on stdout


class Status:
    show_progress = False
    level = 0
    column = 0


status = Status()


def enable(value):
    status.show_progress = value


def print_flush(msg, end="\n"):
    try:
        print(msg, end=end, flush=True)
    except TypeError:
        # micropython doesn't support the flush argument
        print(msg, end=end)


def step(message, level=0):
    if status.show_progress:
        print(("|   " * level) + "+-- " + message)


def log(message, level=0):
    if status.show_progress:
        print_flush(("|   " * level) + message)


def start_dots(level=0):
    if status.show_progress:
        print("|   " * level, end="")
        status.level = level
        status.column = level * 4


def add_dot():
    if status.show_progress:
        if status.column >= 80:
            end_dots()
            start_dots(status.level)
        status.column += 1
        print_flush(".", end="")


def end_dots():
    if status.show_progress:
        print()
