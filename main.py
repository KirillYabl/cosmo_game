import time
import curses
import asyncio
import random
import os
import itertools

from curses_tools import draw_frame, get_frame_size, read_controls
from explosion import explode
from obstacles import Obstacle, has_collision
from physics import update_speed

TIC_TIMEOUT = 0.1
COROUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISION = []
GAME_OVER_FRAME = r'''\
   ______                        ____                 
  / ____/___ _____ ___  ___     / __ \_   _____  _____
 / / __/ __ `/ __ `__ \/ _ \   / / / / | / / _ \/ ___/
/ /_/ / /_/ / / / / / /  __/  / /_/ /| |/ /  __/ /    
\____/\__,_/_/ /_/ /_/\___/   \____/ |___/\___/_/     
'''
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}
GAMSE_STARTED = time.time()
START_YEAR = 1957
GUN_YEAR = 2020
GAME_YEARS_TO_REAL_SECONDS_RATIO = 1.5


def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2


def get_current_year():
    seconds_past = time.time() - GAMSE_STARTED
    game_years_past = int(seconds_past / GAME_YEARS_TO_REAL_SECONDS_RATIO)
    return START_YEAR + game_years_past


async def sleep(tics=1):
    for i in range(tics):
        await asyncio.sleep(0)


async def animate_spaceship(canvas, row, column, frames, spaceship_speed=1):
    max_x, max_y = get_real_maxyx(canvas)
    animations_in_tic = 2
    row_speed = column_speed = 0
    for frame in itertools.cycle(frames):
        for _ in range(animations_in_tic):
            rows_direction, columns_direction, space_pressed = read_controls(canvas)
            rows_direction *= spaceship_speed
            columns_direction *= spaceship_speed
            row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)

            # update coordinates
            frame_rows, frame_columns = get_frame_size(frame)

            planned_rows = row + row_speed
            row = max(1, planned_rows) if rows_direction < 0 else min(max_x - frame_rows, planned_rows)

            planned_columns = column + column_speed
            column = max(1, planned_columns) if columns_direction < 0 else min(max_y - frame_columns, planned_columns)

            draw_frame(canvas, row, column, frame, False)

            current_year = get_current_year()
            if space_pressed and current_year >= GUN_YEAR:
                frame_center = frame_columns // 2
                COROUTINES.append(fire(canvas, row, column + frame_center))
            await asyncio.sleep(0)

            draw_frame(canvas, row, column, frame, True)

            for obstacle in OBSTACLES:
                if obstacle.has_collision(row, column, frame_rows, frame_columns):
                    COROUTINES.append(show_gameover(canvas))
                    return


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

    # curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed

        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                OBSTACLES_IN_LAST_COLLISION.append(obstacle)
                await explode(canvas, row, column)
                return


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    garbage_rows_size, garbage_columns_size = get_frame_size(garbage_frame)

    row = 0
    garbage_obstacle = Obstacle(row, column, garbage_rows_size, garbage_columns_size, uid=2 ** 32)
    OBSTACLES.append(garbage_obstacle)

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        garbage_obstacle.row = row

        if garbage_obstacle in OBSTACLES_IN_LAST_COLLISION:
            OBSTACLES_IN_LAST_COLLISION.remove(garbage_obstacle)
            OBSTACLES.remove(garbage_obstacle)
            return


async def fill_orbit_with_garbage(canvas, garbage_frames):
    """Run garbage coroutines with game logic"""
    rows_number, columns_number = canvas.getmaxyx()

    tics = 0

    while True:
        current_year = get_current_year()
        delay_tics = get_garbage_delay_tics(current_year)

        if not delay_tics:
            await asyncio.sleep(0)
        elif tics < delay_tics:
            tics += 1
            await asyncio.sleep(0)
        else:
            tics = 1
            garbage_frame = random.choice(garbage_frames)
            column = random.randint(0, columns_number)
            COROUTINES.append(fly_garbage(canvas, column=column, garbage_frame=garbage_frame))
            await asyncio.sleep(0)


async def show_obstacles(canvas):
    rows_number, columns_number = canvas.getmaxyx()
    while True:
        drawn_frames = []
        for obstacle in OBSTACLES:
            row, column, obstacle_frame = obstacle.dump_bounding_box()
            drawn_frames.append((row, column, obstacle_frame))
            draw_frame(canvas, row, column, obstacle_frame)

        await asyncio.sleep(0)

        for drawn_frame in drawn_frames:
            draw_frame(canvas, *drawn_frame, negative=True)

        to_delete = []
        for obstacle in OBSTACLES:
            if obstacle.row >= rows_number:
                to_delete.append(obstacle)

        for obstacle in to_delete:
            OBSTACLES.remove(obstacle)


async def show_gameover(canvas):
    max_x, max_y = canvas.getmaxyx()
    size_x, size_y = get_frame_size(GAME_OVER_FRAME)
    x = (max_x - size_x) // 2
    y = (max_y - size_y) // 2

    while True:
        draw_frame(canvas, x, y, GAME_OVER_FRAME)
        await asyncio.sleep(0)


async def show_current_year_and_phrases(canvas):
    max_x, max_y = get_real_maxyx(canvas)
    bottom_corner = max_x - 1
    left_corner = 1
    sub_canvas = canvas.derwin(bottom_corner, left_corner)
    while True:
        current_year = get_current_year()
        msg = f"current year: {current_year}. {PHRASES.get(current_year, '')}"
        draw_frame(sub_canvas, 0, 0, msg)
        await asyncio.sleep(0)
        draw_frame(sub_canvas, 0, 0, msg, negative=True)


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(random.randint(1, 50))

        canvas.addstr(row, column, symbol)
        await sleep(random.randint(1, 50))

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(random.randint(1, 50))

        canvas.addstr(row, column, symbol)
        await sleep(random.randint(1, 50))


def get_real_maxyx(canvas):
    """Return fixed by 1 max_x and max_y cause canvas.getmaxyx truthfully return width and height of screen."""
    width, height = canvas.getmaxyx()
    max_x = width - 1
    max_y = height - 1
    return max_x, max_y


def draw(canvas):
    global COROUTINES

    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    max_x, max_y = get_real_maxyx(canvas)
    start_symbols = '+*.:'

    rocket_frames = []
    for animation_num in [1, 2]:
        with open(os.path.join('animations', f'rocket_frame_{animation_num}.txt')) as f:
            rocket_frames.append(f.read())

    garbage_fnames = ['duck.txt', 'hubble.txt', 'lamp.txt', 'trash_large.txt', 'trash_small.txt', 'trash_xl.txt']
    garbage_frames = []
    for garbage_fname in garbage_fnames:
        with open(os.path.join('garbage', garbage_fname)) as f:
            garbage_frames.append(f.read())

    COROUTINES += [
        animate_spaceship(canvas, max_x // 2, max_y // 2, rocket_frames),
        fill_orbit_with_garbage(canvas, garbage_frames),
        # show_obstacles(canvas), # uncomment it if you need show obstacles
        show_current_year_and_phrases(canvas),
    ]
    for star_num in range(250):
        border_width = 1
        x = random.randint(border_width, max_x - border_width)
        y = random.randint(border_width, max_y - border_width)
        star = blink(canvas, x, y, random.choice(start_symbols))
        COROUTINES.append(star)

    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
        canvas.border()
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
