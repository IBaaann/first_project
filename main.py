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
