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
    max_x, max_y = get_real_maxyx(canvas)
    for frame in itertools.cycle(frames):
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        rows_direction *= spaceship_speed
        columns_direction *= spaceship_speed

        # update coordinates
        frame_rows, frame_columns = get_frame_size(frame)

        planned_rows = row + rows_direction
        row = max(1, planned_rows) if rows_direction < 0 else min(max_x - frame_rows, planned_rows)

        planned_columns = column + columns_direction
        column = max(1, planned_columns) if columns_direction < 0 else min(max_y - frame_columns, planned_columns)

        draw_frame(canvas, row, column, frame, False)

        await asyncio.sleep(0)

        for onetime_frame in frames:
            draw_frame(canvas, row, column, onetime_frame, True)


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


def get_real_maxyx(canvas):
    """Return fixed by 1 max_x and max_y cause canvas.getmaxyx truthfully return width and height of screen."""
    width, height = canvas.getmaxyx()
    max_x = width - 1
    max_y = height - 1
    return max_x, max_y


def draw(canvas):
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    max_x, max_y = get_real_maxyx(canvas)
    start_symbols = '+*.:'

    rocket_frames = []
    for animation_num in [1, 2]:
        with open(os.path.join('animations', f'rocket_frame_{animation_num}.txt')) as f:
            rocket_frames.append(f.read())

    coroutines = [
        fire(canvas, max_x // 2, max_y // 2),
        animate_spaceship(canvas, max_x // 2, max_y // 2, rocket_frames)
    ]
    for star_num in range(250):
        border_width = 1
        x = random.randint(border_width, max_x - border_width)
        y = random.randint(border_width, max_y - border_width)
        star = blink(canvas, x, y, random.choice(start_symbols))
        coroutines.append(star)

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
            canvas.border()
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
