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

class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((SW, SH), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("MY TYPICAL SCHOOL DAY: Мой обычный день в школе")
        self.clock = pygame.time.Clock()
        self.assets = Assets()
        self.F = self.assets.fonts
        self.sfx = Sfx()
        self.running = True
        self.t = 0.0
        self.scene = "menu"
        self.menu_index = 0
        self.menu_rects = []
        self.pause_index = 0
        self.fade = 1.0
        self.overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
        rng = random.Random(11)
        self.stars = [(rng.randint(0, SW), rng.randint(0, 330), rng.choice((1, 1, 2)), rng.random() * 6)
                      for _ in range(90)]
        self.snow = [[rng.uniform(0, SW), rng.uniform(0, SH), rng.uniform(30, 90),
                      rng.choice((1, 2, 2, 3)), rng.uniform(-18, 18)] for _ in range(110)]
        self.menu_sky = pygame.Surface((SW, SH))
        for y in range(SH):
            self.menu_sky.fill(mix((8, 10, 28), (40, 52, 96), y / float(SH)), (0, y, SW, 1))
        self.glow_title = None
        self._reset_run_state()

    #состояние забега
    def _reset_run_state(self):
        self.progress = Progress()
        self.levels = {}
        self.level = None
        self.player = None
        self.floor = 0
        self.checkpoint = None
        self.play_time = 0.0
        self.caught_count = 0
        self.stuns = 0
        self.toasts = []
        self.caught_by = None
        self.caught_t = 0.0
        self.note_text = None
        self.note_t = 0.0
        self.card_t = 0.0
        self.slide = 0
        self.slide_t = 0.0
        self.stair_cd = 0.0
        self.grace = 0.0
        self.cam = pygame.math.Vector2(0, 0)
        self.hint_t = 0.0

    @property
    def alarm(self):
        return self.progress.notes >= NOTES_NEEDED

    def start_new_game(self):
        self._reset_run_state()
        self.scene = "intro"
        self.slide = 0
        self.slide_t = 0.0
        self.fade = 1.0

    def begin_floor(self, idx, pos=None, card=True):
        self.floor = idx
        if idx not in self.levels:
            self.levels[idx] = Level(idx, self.progress, self.assets)
        self.level = self.levels[idx]
        if pos is None:
            pos = self.level.spawn
        self.player = Player(pos.x, pos.y)
        self.save_checkpoint(pos)
        self.snap_camera()
        self.stair_cd = 0.8
        self.grace = 1.5
        self.fade = 1.0
        if card:
            self.scene = "card"
            self.card_t = 0.0
        else:
            self.scene = "play"

    def save_checkpoint(self, pos=None):
        if pos is None:
            pos = self.checkpoint["pos"] if self.checkpoint else self.player.pos
        self.checkpoint = dict(floor=self.floor, pos=pygame.math.Vector2(pos), progress=self.progress.copy())

    def retry_floor(self):
        cp = self.checkpoint
        self.progress = cp["progress"].copy()
        self.floor = cp["floor"]
        self.levels[self.floor] = Level(self.floor, self.progress, self.assets)
        self.begin_floor(self.floor, pygame.math.Vector2(cp["pos"]), card=False)
        self.scene = "play"

    def go_stairs(self, stair):
        target = self.floor + (1 if stair.kind == "v" else -1)
        if target < 0 or target >= len(FLOORS):
            return
        if target not in self.levels:
            self.levels[target] = Level(target, self.progress, self.assets)
        lvl = self.levels[target]
        want = "^" if stair.kind == "v" else "v"
        pos = None
        for st in lvl.stairs:
            if st.kind == want:
                pos = pygame.math.Vector2(st.center)
                break
        if pos is None:
            pos = pygame.math.Vector2(lvl.spawn)
        self.sfx.play("stairs")
        self.begin_floor(target, pos, card=True)

    #события
    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F11:
                try:
                    pygame.display.toggle_fullscreen()
                except Exception:
                    pass
                return
            if ev.key == pygame.K_m:
                self.sfx.muted = not self.sfx.muted
                self.toast("Звук выключен" if self.sfx.muted else "Звук включён")
                return
        fn = getattr(self, "ev_" + self.scene, None)
        if fn:
            fn(ev)

    def toast(self, text, color=WHITE):
        self.toasts.append([text, 3.0, color])
        self.toasts = self.toasts[-4:]

    def is_confirm(self, ev):
        return ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)

    def ev_menu(self, ev):
        items = self.menu_items()
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(items)
                self.sfx.play("menu")
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(items)
                self.sfx.play("menu")
            elif self.is_confirm(ev):
                items[self.menu_index][1]()
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(ev.pos) and i != self.menu_index:
                    self.menu_index = i
                    self.sfx.play("menu")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(ev.pos):
                    self.menu_index = i
                    items[i][1]()

    def menu_items(self):
        return [("Начать игру", self.start_new_game),
                ("Как играть", lambda: setattr(self, "scene", "help")),
                ("Звук: выкл" if self.sfx.muted else "Звук: вкл", self.toggle_sound),
                ("Выход", lambda: setattr(self, "running", False))]

    def toggle_sound(self):
        self.sfx.muted = not self.sfx.muted

    def ev_help(self, ev):
        if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN):
            self.scene = "menu"

    def ev_intro(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.begin_floor(0)
            return
        if self.is_confirm(ev) or (ev.type == pygame.MOUSEBUTTONDOWN):
            text = INTRO_SLIDES[self.slide][1]
            if self.slide_t * 55 < len(text):
                self.slide_t = len(text) / 55.0 + 0.01
            else:
                self.slide += 1
                self.slide_t = 0.0
                if self.slide >= len(INTRO_SLIDES):
                    self.begin_floor(0)

    def ev_card(self, ev):
        if self.card_t > 0.6 and (ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN):
            self.scene = "play"

    def ev_play(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE or ev.key == pygame.K_p:
                self.scene = "pause"
                self.pause_index = 0
            elif ev.key in (pygame.K_e, pygame.K_SPACE):
                self.interact()

    def ev_note(self, ev):
        if self.note_t > 0.5 and ev.type == pygame.KEYDOWN and ev.key in (
                pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_ESCAPE, pygame.K_KP_ENTER):
            self.scene = "play"

    def ev_pause(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key in (pygame.K_ESCAPE, pygame.K_p):
            self.scene = "play"
        elif ev.key in (pygame.K_UP, pygame.K_w):
            self.pause_index = (self.pause_index - 1) % 3
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self.pause_index = (self.pause_index + 1) % 3
        elif self.is_confirm(ev):
            if self.pause_index == 0:
                self.scene = "play"
            elif self.pause_index == 1:
                self.retry_floor()
            else:
                self.scene = "menu"
                self.fade = 1.0

    def ev_caught(self, ev):
        if self.caught_t < 0.8 or ev.type != pygame.KEYDOWN:
            return
        if ev.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self.retry_floor()
        elif ev.key == pygame.K_ESCAPE:
            self.scene = "menu"
            self.fade = 1.0

    def ev_ending(self, ev):
        if self.is_confirm(ev) or ev.type == pygame.MOUSEBUTTONDOWN:
            if self.slide < len(ENDING_SLIDES):
                text = ENDING_SLIDES[self.slide][1]
                if self.slide_t * 55 < len(text):
                    self.slide_t = len(text) / 55.0 + 0.01
                else:
                    self.slide += 1
                    self.slide_t = 0.0
            else:
                self.scene = "menu"
                self.fade = 1.0
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.scene = "menu"
            self.fade = 1.0

    #взаимодействие
    def find_interact(self):
        p, lvl = self.player, self.level
        best = None

        def consider(dist, limit, kind, obj, label, bonus=0):
            nonlocal best
            if dist <= limit:
                score = dist - bonus
                if best is None or score < best[0]:
                    best = (score, kind, obj, label)

        for d in lvl.doors.values():
            dist = (d.center - p.pos).length()
            if d.locked:
                label = "Отпереть дверь (ключ)" if self.progress.keys > 0 else "Заперто — нужен ключ"
            else:
                label = "Закрыть дверь" if d.open_target else "Открыть дверь"
            consider(dist, 78, "door", d, label)
        for st in lvl.stairs:
            dist = (st.center - p.pos).length()
            nxt = self.floor + (1 if st.kind == "v" else -1)
            if 0 <= nxt < len(FLOORS):
                n_floor = 3 - nxt
                consider(dist, 84, "stairs", st,
                         ("Спуститься на %d этаж" if st.kind == "v" else "Подняться на %d этаж") % n_floor)
        for tch in lvl.teachers:
            if tch.can_trip():
                dist = (tch.pos - p.pos).length()
                consider(dist, 58, "teacher", tch, "Подставить ногу (%s)" % tch.cfg["name"], bonus=20)
        for r in lvl.exits:
            dist = (pygame.math.Vector2(r.center) - p.pos).length()
            label = "Выйти из школы" if self.progress.notes >= NOTES_NEEDED else \
                "Выход закрыт: нужны все 3 страницы (%d/3)" % self.progress.notes
            consider(dist, 90, "exit", r, label)
        return best

    def interact(self):
        cand = self.find_interact()
        if not cand:
            return
        _, kind, obj, _label = cand
        lvl, p = self.level, self.player
        if kind == "door":
            if obj.locked:
                if self.progress.keys > 0:
                    self.progress.keys -= 1
                    obj.locked = False
                    self.progress.unlocked.add((self.floor, obj.tx, obj.ty))
                    obj.set_open(True)
                    self.save_checkpoint()
                    self.sfx.play("unlock")
                    self.toast("Дверь отперта", (150, 255, 170))
                else:
                    self.sfx.play("locked")
                    self.toast("Заперто. Нужен ключ.", (255, 150, 120))
            else:
                if obj.open_target:
                    if lvl.door_occupied(obj, p):
                        self.toast("В проёме что-то мешает", (255, 150, 120))
                        return
                    obj.set_open(False)
                else:
                    obj.set_open(True)
                obj.auto = False
                self.sfx.play("door")
        elif kind == "stairs":
            if self.stair_cd <= 0:
                self.go_stairs(obj)
        elif kind == "teacher":
            obj.stun(6.0)
            self.stuns += 1
            self.sfx.play("stun")
            self.toast("Подножка! Он отключился на 6 секунд", (255, 230, 120))
        elif kind == "exit":
            if self.progress.notes >= NOTES_NEEDED:
                self.sfx.play("win")
                self.scene = "ending"
                self.slide = 0
                self.slide_t = 0.0
                self.fade = 1.0
            else:
                self.sfx.play("locked")
                self.toast("Без трёх страниц журнала уходить нельзя — тебе никто не поверит!", (255, 180, 120))

    #обновление
    def update(self, dt):
        self.t += dt
        if self.fade > 0:
            self.fade = max(0.0, self.fade - dt * 1.6)
        for ts in self.toasts:
            ts[1] -= dt
        self.toasts = [ts for ts in self.toasts if ts[1] > 0]
        for s in self.snow:
            s[1] += s[2] * dt
            s[0] += s[4] * dt
            if s[1] > SH + 5:
                s[1] = -5
                s[0] = random.uniform(0, SW)
        fn = getattr(self, "upd_" + self.scene, None)
        if fn:
            fn(dt)

    def upd_intro(self, dt):
        self.slide_t += dt

    def upd_ending(self, dt):
        self.slide_t += dt

    def upd_card(self, dt):
        self.card_t += dt
        self.update_camera(dt)
        if self.card_t > 2.6:
            self.scene = "play"

    def upd_note(self, dt):
        self.note_t += dt

    def upd_caught(self, dt):
        self.caught_t += dt

    def upd_play(self, dt):
        self.play_time += dt
        self.hint_t += dt
        if self.stair_cd > 0:
            self.stair_cd -= dt
        if self.grace > 0:
            self.grace -= dt
        keys = pygame.key.get_pressed()
        lvl, p = self.level, self.player
        p.update(dt, lvl, keys)
        lvl.update(dt, p, self)
        self.check_items()
        for tch in lvl.teachers:
            if self.grace <= 0 and tch.state != "STUNNED" and tch.hitbox.colliderect(p.hitbox):
                if (not p.hidden) or tch.state == "CHASE":
                    self.caught(tch)
                    return
        self.update_camera(dt)

    def check_items(self):
        p, lvl = self.player, self.level
        for it in list(lvl.items):
            if p.hitbox.colliderect(it.rect.inflate(14, 14)):
                lvl.items.remove(it)
                self.progress.collected.add((self.floor, it.tx, it.ty))
                if it.kind == "key":
                    self.progress.keys += 1
                    self.sfx.play("pick")
                    self.toast("Найден ключ! Он подойдёт к запертой двери.", GOLD)
                    self.save_checkpoint()
                else:
                    self.progress.notes += 1
                    self.save_checkpoint()
                    note = lvl.data["note"]
                    extra = ""
                    if self.progress.notes >= NOTES_NEEDED:
                        extra = "\n\nВО ВСЕЙ ШКОЛЕ ВКЛЮЧИЛАСЬ СИГНАЛИЗАЦИЯ! Учителя стали быстрее. Беги к выходу!"
                    self.note_text = (note["title"], note["text"] + extra)
                    self.note_t = 0.0
                    self.scene = "note"
                    self.sfx.play("note")
                    return

    def caught(self, tch):
        self.caught_by = tch
        self.caught_count += 1
        self.caught_t = 0.0
        self.scene = "caught"
        self.sfx.play("caught")

    #камера
    def cam_target(self):
        lvl, p = self.level, self.player
        tx = p.pos.x - SW / 2.0
        ty = p.pos.y - SH / 2.0
        tx = -(SW - lvl.px_w) / 2.0 if lvl.px_w <= SW else clamp(tx, 0, lvl.px_w - SW)
        ty = -(SH - lvl.px_h) / 2.0 if lvl.px_h <= SH else clamp(ty, 0, lvl.px_h - SH)
        return pygame.math.Vector2(tx, ty)

    def snap_camera(self):
        self.cam = self.cam_target()

    def update_camera(self, dt):
        tgt = self.cam_target()
        k = min(1.0, dt * 8.0)
        self.cam += (tgt - self.cam) * k

    #отрисовка
    def draw(self):
        s = self.screen
        fn = getattr(self, "draw_" + self.scene, None)
        if fn:
            fn(s)
        if self.fade > 0:
            self.assets.black.set_alpha(int(255 * self.fade))
            s.blit(self.assets.black, (0, 0))

    def draw_snow(self, s):
        for x, y, sp, r, dr in self.snow:
            c = 170 + r * 25
            pygame.draw.circle(s, (c, c, 255), (int(x), int(y)), r)

    def draw_menu_bg(self, s):
        t = self.t
        s.blit(self.menu_sky, (0, 0))
        for x, y, r, ph in self.stars:
            c = 150 + int(80 * math.sin(t * 1.5 + ph))
            pygame.draw.circle(s, (c, c, min(255, c + 20)), (x, y), r)
        pygame.draw.circle(s, (236, 236, 214), (1040, 120), 46)
        pygame.draw.circle(s, (206, 206, 186), (1024, 106), 10)
        pygame.draw.circle(s, (206, 206, 186), (1054, 134), 7)
        ink = (14, 18, 32)
        pygame.draw.rect(s, ink, (180, 360, 920, 300))
        pygame.draw.rect(s, ink, (560, 270, 160, 100))
        pygame.draw.polygon(s, ink, [(536, 272), (640, 196), (744, 272)])
        pygame.draw.rect(s, (24, 30, 52), (180, 356, 920, 6))
        lit = None
        for r in range(3):
            for c in range(11):
                x, y = 230 + c * 74, 400 + r * 70
                on = math.sin(t * 0.6 + c * 1.9 + r * 2.7) > 0.72
                if (c, r) == (3, 1):
                    on = True
                    lit = (x + 18, y + 22)
                col = (255, 214, 120) if on else (26, 34, 58)
                pygame.draw.rect(s, col, (x, y, 36, 44), border_radius=3)
        pygame.draw.rect(s, (30, 22, 18), (610, 590, 60, 100), border_radius=4)
        pygame.draw.rect(s, (255, 214, 120), (616, 596, 48, 8))
        pygame.draw.rect(s, (60, 72, 104), (0, 660, SW, 60))
        pygame.draw.rect(s, (90, 104, 140), (0, 660, SW, 4))
        if lit:
            self.overlay.fill((0, 0, 0, 0))
            base = 1.0 + math.sin(t * 0.9) * 0.45
            pts = [lit]
            for i in range(13):
                a = base - 0.24 + 0.48 * i / 12.0
                pts.append((lit[0] + math.cos(a) * 420, lit[1] + math.sin(a) * 420))
            pygame.draw.polygon(self.overlay, (255, 240, 150, 60), ipts(pts))
            s.blit(self.overlay, (0, 0))
        self.draw_snow(s)

    def title_glow(self):
        if self.glow_title is None:
            img = self.F["title"].render(GAME_TITLE, True, (255, 200, 90))
            w, h = img.get_size()
            small = pygame.transform.smoothscale(img, (max(1, w // 6), max(1, h // 6)))
            self.glow_title = pygame.transform.smoothscale(small, (w + 40, h + 40))
        return self.glow_title

    def draw_menu(self, s):
        self.draw_menu_bg(s)
        pulse = 0.6 + 0.4 * math.sin(self.t * 2)
        g = self.title_glow()
        g.set_alpha(int(150 * pulse))
        s.blit(g, g.get_rect(center=(SW // 2, 150)))
        blit_text(s, self.F["title"], GAME_TITLE, (255, 232, 170), (SW // 2, 150), "center", (90, 40, 10))
        blit_text(s, self.F["big"], GAME_SUBTITLE.upper(), (170, 200, 255), (SW // 2, 232), "center", (0, 0, 20))
        items = self.menu_items()
        self.menu_rects = []
        for i, (label, _fn) in enumerate(items):
            r = pygame.Rect(0, 0, 380, 56)
            r.center = (SW // 2, 330 + i * 70)
            self.menu_rects.append(r)
            sel = i == self.menu_index
            if sel:
                panel(s, r, (255, 205, 100, 235), (255, 240, 200, 255), 14)
                blit_text(s, self.F["bold"], label, (40, 24, 8), r.center, "center", None)
            else:
                panel(s, r, (14, 20, 44, 205), (140, 160, 220, 70), 14)
                blit_text(s, self.F["bold"], label, (205, 214, 240), r.center, "center", None)
        blit_text(s, self.F["small"], "↑↓ / мышь — выбор · Enter — подтвердить · M — звук · F11 — во весь экран",
                  (150, 165, 205), (SW // 2, SH - 26), "center")

    def draw_help(self, s):
        self.draw_menu_bg(s)
        panel(s, (140, 50, SW - 280, SH - 100), (8, 12, 28, 235), (255, 255, 255, 50), 18)
        blit_text(s, self.F["big"], "КАК ИГРАТЬ", GOLD, (SW // 2, 100), "center")
        rows = [
            ("WASD / стрелки", "ходить"),
            ("Shift (держать)", "красться: тихо и почти незаметно, но медленно"),
            ("E / Пробел", "дверь, ключ, лестница, выход, подножка учителю"),
            ("Esc / P", "пауза"),
            ("M · F11", "звук вкл/выкл · полный экран"),
        ]
        y = 160
        for k, v in rows:
            blit_text(s, self.F["bold"], k, (255, 220, 140), (190, y))
            blit_text(s, self.F["norm"], v, (225, 230, 245), (470, y))
            y += 44
        tips = ("Жёлтый конус — зона зрения учителя. Заметят — конус краснеет, а над головой "
                "появляется «?» и затем «!» (погоня).\n"
                "Беги — шумишь: учитель услышит и пойдёт проверить. Красться — тихо.\n"
                "Зелёные тени с куртками — укрытие: внутри тебя не видно.\n"
                "Закрытые двери не пропускают взгляд, но учителя открывают их сами.\n"
                "Подножка со спины (пока учитель тебя не заметил) отключает его на 6 секунд.\n"
                "Ключ открывает одну запертую дверь. Нужно найти 3 страницы журнала и выйти через главный вход.")
        yy = 400
        for line in wrap_text(self.F["small"], tips, SW - 400):
            blit_text(s, self.F["small"], line, (200, 210, 235), (190, yy))
            yy += 27
        blit_text(s, self.F["small"], "Нажми любую клавишу, чтобы вернуться", (150, 165, 205),
                  (SW // 2, SH - 80), "center")

    def draw_typed(self, s, slides, heading_color):
        head, text = slides[self.slide]
        blit_text(s, self.F["head"], head, heading_color, (SW // 2, 200), "center", (0, 0, 0))
        shown = text[:int(self.slide_t * 55)]
        done = len(shown) >= len(text)
        panel(s, (170, 300, SW - 340, 270), (8, 12, 28, 225), (255, 255, 255, 50), 18)
        yy = 326
        for line in wrap_text(self.F["norm"], shown, SW - 420):
            blit_text(s, self.F["norm"], line, (232, 236, 250), (210, yy))
            yy += 36
        if done and int(self.t * 2) % 2 == 0:
            blit_text(s, self.F["small"], "Пробел — дальше", (160, 175, 215), (SW - 210, 540), "topright")

    def draw_intro(self, s):
        s.blit(self.menu_sky, (0, 0))
        self.draw_snow(s)
        self.draw_typed(s, INTRO_SLIDES, (255, 205, 100))
        blit_text(s, self.F["small"], "Esc — пропустить", (130, 145, 185), (SW - 30, SH - 36), "topright")

    def draw_ending(self, s):
        s.blit(self.menu_sky, (0, 0))
        self.draw_snow(s)
        if self.slide < len(ENDING_SLIDES):
            self.draw_typed(s, ENDING_SLIDES, (255, 220, 140))
            return
        panel(s, (300, 120, SW - 600, 470), (8, 12, 28, 235), (255, 255, 255, 60), 18)
        blit_text(s, self.F["head"], "ПОБЕДА!", GOLD, (SW // 2, 200), "center")
        mins = int(self.play_time // 60)
        secs = int(self.play_time % 60)
        rating = "S" if self.caught_count == 0 else "A" if self.caught_count <= 2 else \
            "B" if self.caught_count <= 5 else "C"
        lines = [("Время", "%d:%02d" % (mins, secs)), ("Раз поймали", str(self.caught_count)),
                 ("Подножек", str(self.stuns)), ("Оценка", rating)]
        y = 290
        for k, v in lines:
            blit_text(s, self.F["norm"], k, (200, 210, 235), (400, y))
            blit_text(s, self.F["bold"], v, GOLD, (SW - 400, y), "topright")
            y += 50
        blit_text(s, self.F["small"], "Enter — в главное меню", (160, 175, 215), (SW // 2, 540), "center")

    def draw_world(self, s):
        lvl, p = self.level, self.player
        ox, oy = int(round(self.cam.x)), int(round(self.cam.y))
        s.fill(BG_COLOR)
        s.blit(lvl.static, (-ox, -oy))
        if self.alarm:
            for r in lvl.exits:
                g = self.assets.glow_green
                s.blit(g, g.get_rect(center=(r.centerx - ox, r.centery - oy)))
        lvl.draw_under(s, ox, oy, self.t)
        self.overlay.fill((0, 0, 0, 0))
        for tch in lvl.teachers:
            tch.draw_cone(self.overlay, lvl, ox, oy)
        s.blit(self.overlay, (0, 0))
        for tch in lvl.teachers:
            tch.draw(s, self.assets, ox, oy, self.t)
        p.draw(s, self.assets, ox, oy)
        lvl.draw_zones(s, ox, oy)
        s.blit(self.assets.vignette, (0, 0))
        for tch in lvl.teachers:
            tch.draw_icon(s, self.assets, ox, oy, self.t)
        if self.alarm:
            a = 24 + int(24 * (0.5 + 0.5 * math.sin(self.t * 7)))
            self.assets.red.set_alpha(a)
            s.blit(self.assets.red, (0, 0))

    def clock_text(self):
        mins = int(CLOCK_START + self.play_time * CLOCK_SPEED / 60.0) % 1440
        return "%02d:%02d" % (mins // 60, mins % 60)

    def draw_hud(self, s):
        p, lvl = self.player, self.level
        panel(s, (16, 16, 330, 132))
        blit_text(s, self.F["bold"], "%s · %s" % (lvl.data["name"].upper(), self.clock_text()), GOLD, (30, 24))
        s.blit(pygame.transform.smoothscale(self.assets.key_icon, (34, 34)), (28, 56))
        blit_text(s, self.F["norm"], "× %d" % self.progress.keys, WHITE, (66, 60))
        s.blit(pygame.transform.smoothscale(self.assets.note_icon, (34, 34)), (150, 56))
        blit_text(s, self.F["norm"], "%d / %d" % (self.progress.notes, NOTES_NEEDED), WHITE, (188, 60))
        chase = any(t.state == "CHASE" for t in lvl.teachers)
        top = max([t.alert for t in lvl.teachers] + [0.0])
        if chase:
            status, col = "ПОГОНЯ!", (255, 90, 90)
        elif p.hidden:
            status, col = "В УКРЫТИИ", (120, 255, 170)
        elif top > 0.08:
            status, col = "ТЕБЯ ЗАМЕЧАЮТ…", (255, 190, 80)
        elif p.sneaking:
            status, col = "ТИХО", (130, 220, 255)
        else:
            status, col = "СПОКОЙНО", (180, 190, 215)
        blit_text(s, self.F["bold"], status, col, (30, 100))
        pygame.draw.rect(s, (30, 36, 60), (190, 104, 140, 12), border_radius=6)
        fill = 1.0 if chase else clamp(top, 0, 1)
        if fill > 0:
            pygame.draw.rect(s, mix((255, 220, 90), (255, 60, 60), fill), (190, 104, int(140 * fill), 12), border_radius=6)
        pygame.draw.rect(s, (200, 210, 240), (190, 104, 140, 12), 1, border_radius=6)

        obj = lvl.data["obj_done"] if (self.floor, *self._note_tile()) in self.progress.collected \
            else lvl.data["obj_find"]
        if self.alarm:
            obj = "Все страницы собраны! Спускайся на 1 этаж и беги к главному выходу!" \
                if self.floor != len(FLOORS) - 1 else "Все страницы собраны! Беги к главному выходу внизу холла!"
        lines = wrap_text(self.F["small"], obj, 330)
        panel(s, (SW - 366, 16, 350, 46 + 24 * len(lines)))
        blit_text(s, self.F["bold"], "ЦЕЛЬ", (150, 200, 255), (SW - 350, 24))
        for i, ln in enumerate(lines):
            blit_text(s, self.F["small"], ln, (225, 232, 250), (SW - 350, 54 + i * 24))

        cand = self.find_interact()
        if cand:
            label = cand[3]
            w = self.F["bold"].size(label)[0] + 90
            r = pygame.Rect(0, 0, w, 46)
            r.center = (SW // 2, SH - 64)
            panel(s, r, (10, 14, 28, 215), (255, 220, 140, 120), 12)
            kb = pygame.Rect(r.x + 12, r.y + 9, 28, 28)
            pygame.draw.rect(s, (255, 220, 140), kb, border_radius=6)
            blit_text(s, self.F["bold"], "E", (40, 24, 8), kb.center, "center", None)
            blit_text(s, self.F["bold"], label, WHITE, (r.x + 52, r.y + 9))
        y = SH - 140
        for text, _t, color in reversed(self.toasts):
            blit_text(s, self.F["norm"], text, color, (SW // 2, y), "center")
            y -= 34
        if self.hint_t < 9 and self.floor == 0:
            blit_text(s, self.F["small"], "WASD — ходить · Shift — красться · E — действие · Esc — пауза",
                      (190, 205, 240), (SW // 2, SH - 24), "center")

    def _note_tile(self):
        for ty, row in enumerate(self.level.rows):
            for tx, ch in enumerate(row):
                if ch == "n":
                    return (tx, ty)
        return (-1, -1)

    def draw_play(self, s):
        self.draw_world(s)
        self.draw_hud(s)

    def draw_card(self, s):
        self.draw_world(s)
        a = clamp(min(self.card_t / 0.5, (2.6 - self.card_t) / 0.6), 0, 1)
        self.assets.black.set_alpha(int(190 * a))
        s.blit(self.assets.black, (0, 0))
        d = self.level.data
        blit_text(s, self.F["head"], d["name"].upper(), (255, 225, 150), (SW // 2, SH // 2 - 40), "center",
                  (0, 0, 0), int(255 * a))
        blit_text(s, self.F["big"], d["subtitle"], (190, 205, 245), (SW // 2, SH // 2 + 30), "center",
                  (0, 0, 0), int(255 * a))
        blit_text(s, self.F["norm"], self.clock_text(), (160, 175, 215), (SW // 2, SH // 2 + 84), "center",
                  (0, 0, 0), int(255 * a))

    def draw_note(self, s):
        self.draw_world(s)
        self.draw_hud(s)
        self.assets.black.set_alpha(170)
        s.blit(self.assets.black, (0, 0))
        title, text = self.note_text
        r = (SW // 2 - 330, 110, 660, 500)
        panel(s, r, (244, 238, 218, 255), (120, 100, 70, 255), 10)
        blit_text(s, self.F["big"], title, (70, 40, 20), (SW // 2, 160), "center", None)
        yy = 220
        for ln in wrap_text(self.F["norm"], text, 590):
            blit_text(s, self.F["norm"], ln, (50, 44, 40), (SW // 2 - 295, yy), "topleft", None)
            yy += 31
        if self.note_t > 0.5:
            blit_text(s, self.F["small"], "Пробел — убрать в карман", (110, 90, 70), (SW // 2, 580), "center", None)

    def draw_pause(self, s):
        self.draw_world(s)
        self.draw_hud(s)
        self.assets.black.set_alpha(150)
        s.blit(self.assets.black, (0, 0))
        blit_text(s, self.F["head"], "ПАУЗА", GOLD, (SW // 2, 220), "center")
        for i, label in enumerate(("Продолжить", "Начать этаж заново", "В главное меню")):
            r = pygame.Rect(0, 0, 400, 52)
            r.center = (SW // 2, 330 + i * 66)
            sel = i == self.pause_index
            panel(s, r, (255, 205, 100, 235) if sel else (14, 20, 44, 215),
                  (255, 240, 200, 255) if sel else (140, 160, 220, 80), 14)
            blit_text(s, self.F["bold"], label, (40, 24, 8) if sel else (205, 214, 240), r.center, "center", None)

    def draw_caught(self, s):
        self.draw_world(s)
        self.assets.red.set_alpha(90)
        s.blit(self.assets.red, (0, 0))
        self.assets.black.set_alpha(140)
        s.blit(self.assets.black, (0, 0))
        blit_text(s, self.F["head"], "ТЕБЯ ПОЙМАЛИ!", (255, 110, 100), (SW // 2, 230), "center")
        if self.caught_by is not None:
            panel(s, (240, 300, SW - 480, 130), (10, 14, 28, 225), (255, 120, 100, 120), 14)
            blit_text(s, self.F["bold"], self.caught_by.cfg["name"], GOLD, (270, 316))
            yy = 354
            for ln in wrap_text(self.F["norm"], self.caught_by.cfg["quote"], SW - 540):
                blit_text(s, self.F["norm"], ln, WHITE, (270, yy))
                yy += 32
        if self.caught_t > 0.8:
            blit_text(s, self.F["bold"], "R / Enter — ещё раз с начала этажа · Esc — в меню", (210, 220, 245),
                      (SW // 2, 500), "center")

    #главный цикл
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for ev in pygame.event.get():
                self.handle_event(ev)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


def main():
    Game().run()
    sys.exit()


if __name__ == "__main__":
    main()


def tile_of(v):
    return int(v // TILE)
