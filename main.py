import sys
import math
import random
import array
from collections import deque
import pygame


# Константы
SW, SH = 1280, 720
FPS = 60
TILE = 64
GAME_TITLE = "MY TYPICAL SCHOOL DAY"
GAME_SUBTITLE = "Мой обычный день в школе"
CLOCK_START = 23 * 60 + 40      # 23:40
CLOCK_SPEED = 7.5               # игровых секунд за 1 реальную
NOTES_NEEDED = 3

BG_COLOR = (12, 14, 22)
GOLD = (255, 205, 100)
WHITE = (240, 240, 245)
SOLID_CHARS = "#BCX"            # стены, парты, колонны, выход
FONT_NAMES = "segoeui,arial,helvetica,dejavusans,liberationsans,notosans,freesans"


# Утилиты
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def shade(c, f):
    return (clamp(int(c[0] * f), 0, 255), clamp(int(c[1] * f), 0, 255), clamp(int(c[2] * f), 0, 255))


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def ipts(points):
    return [(int(round(x)), int(round(y))) for x, y in points]


def tile_of(v):
    return int(v // TILE)
