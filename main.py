import time
import curses
import asyncio
import random
import os
import itertools

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
TIC_TIMEOUT = 0.1
ROCKET_FRAMES = []

for animation_num in [1, 2]:
    with open(os.path.join('animations', f'rocket_frame_{animation_num}.txt')) as f:
        ROCKET_FRAMES.append(f.read())


def get_frame_size(text):
    """Calculate size of multiline text fragment, return pair — number of rows and columns."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def read_controls(canvas):
    """Read keys pressed and returns tuple with controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


async def animate_spaceship(canvas, row, column, frames, spaceship_speed=1):
    max_x, max_y = canvas.getmaxyx()
    for frame_num, frame in enumerate(itertools.cycle(frames)):
        for onetime_frame in range(len(frames)):
            draw_frame(canvas, row, column, frames[onetime_frame], True)
        draw_frame(canvas, row, column, frame, False)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        rows_direction *= spaceship_speed
        columns_direction *= spaceship_speed
        for onetime_frame in range(len(frames)):
            draw_frame(canvas, row, column, frames[onetime_frame], True)

        frame_rows, frame_columns = get_frame_size(frame)
        while not (frame_rows < row + rows_direction + frame_rows < max_x):
            rows_direction = rows_direction + 1 if rows_direction < 0 else rows_direction - 1
        while not (frame_columns < column + columns_direction + frame_columns < max_y):
            columns_direction = columns_direction + 1 if columns_direction < 0 else columns_direction - 1
        row = row + rows_direction
        column = column + columns_direction


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for i in range(random.randint(1, 50)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(random.randint(1, 50)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for i in range(random.randint(1, 50)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(random.randint(1, 50)):
            await asyncio.sleep(0)


def draw(canvas):
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    max_x, max_y = canvas.getmaxyx()
    start_symbols = '+*.:'
    animation_frames = 4

    coroutines = [
        fire(canvas, max_x // 2, max_y // 2),
        animate_spaceship(canvas, max_x // 2, max_y // 2, ROCKET_FRAMES)
    ]
    for star_num in range(250):
        x = random.randint(1, max_x - 2)
        y = random.randint(1, max_y - 2)
        star = blink(canvas, x, y, random.choice(list(start_symbols)))
        coroutines.append(star)

    while True:
        for _ in range(animation_frames):
            for coroutine in coroutines.copy():
                try:
                    coroutine.send(None)
                except StopIteration:
                    coroutines.remove(coroutine)
                    canvas.border()
            refresh_and_sleep(canvas, TIC_TIMEOUT)


def refresh_and_sleep(canvas, sleep):
    canvas.refresh()
    time.sleep(sleep)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
