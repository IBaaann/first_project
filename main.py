import sys, math, pygame
pygame.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TILE_SIZE = 64

#цвета
BG_COLOR = (25, 28, 36)
WALL_COLOR = (50, 60, 75)
WALL_BORDER = (80, 95, 120)
PLAYER_COLOR = (0, 220, 130)
TEACHER_COLOR = (220, 60, 60)
TEACHER_STUN_COLOR = (120, 120, 120)
DOOR_COLOR = (180, 110, 50)
STEALTH_ZONE_COLOR = (40, 90, 60, 120)
#W - Стена, P - Игрок, T - Учитель, D - Дверь, S - Стелс-зона (туалет/стол)
LEVEL_MAP = ["WWWWWWWWWWWWWWWWWWWW",
             "W........W.........W",
             "W..S.....D....T....W",
             "W........W.........W",
             "WWWW D WWWWWWWW D WW",
             "W..................W",
             "W...P..............W",
             "WWWW D WWWWWWWWWWWWW",
             "W........W.........W",
             "W..S.....D.........W",
             "WWWWWWWWWWWWWWWWWWWW", ]
class Wall(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
    self.image.fill(WALL_COLOR)
    pygame.draw.rect(self.image, WALL_BORDER, (0, 0, TILE_SIZE, TILE_SIZE), 2)
    self.rect = self.image.get_rect(topleft=(x, y))
    
class Door(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.is_open = False
    self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
    self.rect = self.image.get_rect(topleft=(x, y))
    self.update_appearance()

  def update_appearance(self):
    if self.is_open:
      self.image.fill((100, 70, 40))
      pygame.draw.rect(self.image, (60, 40, 20), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    else:
      self.image.fill(DOOR_COLOR)
      pygame.draw.rect(self.image, (100, 50, 20), (0, 0, TILE_SIZE, TILE_SIZE), 4)

  def toggle(self):
    self.is_open = not self.is_open
    self.update_appearance()
  
class StealthZone(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    self.image.fill(STEALTH_ZONE_COLOR)
    pygame.draw.rect(self.image, (60, 180, 100), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    self.rect = self.image.get_rect(topleft=(x, y))

class Teacher(pygame.sprite.Sprite):
  def __init__(self, x, y, patrol_points):
    super().__init__()
    self.original_image = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(self.original_image, TEACHER_COLOR, (16, 16), 16)
    pygame.draw.line(self.original_image, (255, 255, 255), (16, 16), (30, 16), 3)

    self.image = self.original_image
    self.hitbox = pygame.Rect(0, 0, 24, 24)
    self.hitbox.center = (x, y)
    self.rect = self.image.get_rect(center=self.hitbox.center)

    self.pos = pygame.math.Vector2(x, y)
    self.speed = 120
    self.angle = 0

    # ИИ и патрулирование
    self.patrol_points = patrol_points
    self.current_point_idx = 0
    self.state = "PATROL"
    self.stun_timer = 0.0

  def stun(self, duration=5.0):
    self.state = "STUNNED"
    self.stun_timer = duration

    # Изменяем вид на оглушенного
    stun_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(stun_surf, TEACHER_STUN_COLOR, (16, 16), 16)
    self.image = stun_surf

  def update(self, dt, walls):
    if self.state == "STUNNED":
      self.stun_timer -= dt
      if self.stun_timer <= 0:
        self.state = "PATROL"
      return

    if not self.patrol_points:
      return

    target = self.patrol_points[self.current_point_idx]
    move_vec = target - self.pos

    if move_vec.length() < 5:
      self.current_point_idx = (self.current_point_idx + 1) % len(self.patrol_points)
    else:
      move_vec = move_vec.normalize()
      step = move_vec * self.speed * dt

      # Движение по X с проверкой столкновений
      self.pos.x += step.x
      self.hitbox.centerx = round(self.pos.x)
      for obstacle in walls:
        if self.hitbox.colliderect(obstacle.rect):
          if step.x > 0: self.hitbox.right = obstacle.rect.left
          elif step.x < 0: self.hitbox.left = obstacle.rect.right
          self.pos.x = self.hitbox.centerx

      # Движение по Y с проверкой столкновений
      self.pos.y += step.y
      self.hitbox.centery = round(self.pos.y)
      for obstacle in walls:
        if self.hitbox.colliderect(obstacle.rect):
          if step.y > 0: self.hitbox.bottom = obstacle.rect.top
          elif step.y < 0: self.hitbox.top = obstacle.rect.bottom
          self.pos.y = self.hitbox.centery

      # Поворот в сторону движения
      self.angle = math.degrees(math.atan2(-move_vec.y, move_vec.x))
      self.image = pygame.transform.rotate(self.original_image, self.angle)
      self.rect = self.image.get_rect(center=self.hitbox.center)

class Player(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.original_image = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(self.original_image, PLAYER_COLOR, (16, 16), 16)
    pygame.draw.line(self.original_image, (255, 255, 255), (16, 16), (30, 16), 3)

    self.image = self.original_image
    self.hitbox = pygame.Rect(0, 0, 24, 24)
    self.hitbox.center = (x, y)
    self.rect = self.image.get_rect(center=self.hitbox.center)

    self.pos = pygame.math.Vector2(x, y)
    self.speed = 300
    self.angle = 0
    self.is_hidden = False

  def get_input(self):
    keys = pygame.key.get_pressed()
    move_vec = pygame.math.Vector2(0, 0)

    if keys[pygame.K_w] or keys[pygame.K_UP]: move_vec.y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]: move_vec.y += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]: move_vec.x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_vec.x += 1

    if move_vec.length_squared() > 0:
      move_vec = move_vec.normalize()

    return move_vec

  def move_and_collide(self, dt, obstacles):
    move_vec = self.get_input()

    # Движение x
    self.pos.x += move_vec.x * self.speed * dt
    self.hitbox.centerx = round(self.pos.x)
    for obstacle in obstacles:
      if self.hitbox.colliderect(obstacle.rect):
        if move_vec.x > 0: self.hitbox.right = obstacle.rect.left
        elif move_vec.x < 0: self.hitbox.left = obstacle.rect.right
        self.pos.x = self.hitbox.centerx

    # Движение Y
    self.pos.y += move_vec.y * self.speed * dt
    self.hitbox.centery = round(self.pos.y)
    for obstacle in obstacles:
      if self.hitbox.colliderect(obstacle.rect):
        if move_vec.y > 0: self.hitbox.bottom = obstacle.rect.top
        elif move_vec.y < 0: self.hitbox.top = obstacle.rect.bottom
        self.pos.y = self.hitbox.centery

  def check_stealth(self, stealth_zones):
    self.is_hidden = False
    for zone in stealth_zones:
      if self.hitbox.colliderect(zone.rect):
        self.is_hidden = True
        break

  def rotate_towards_mouse(self):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    rel_x, rel_y = mouse_x - self.pos.x, mouse_y - self.pos.y
    self.angle = math.degrees(math.atan2(-rel_y, rel_x))

    self.image = pygame.transform.rotate(self.original_image, self.angle)
    self.rect = self.image.get_rect(center=self.hitbox.center)

  def update(self, dt, obstacles, stealth_zones):
    self.move_and_collide(dt, obstacles)
    self.check_stealth(stealth_zones)
    self.rotate_towards_mouse()



def main():
  screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
  pygame.display.set_caption("School Escape: Пьяный переполох")
  clock = pygame.time.Clock()

  walls_group = pygame.sprite.Group()
  doors_group = pygame.sprite.Group()
  stealth_group = pygame.sprite.Group()
  teachers_group = pygame.sprite.Group()
  all_sprites = pygame.sprite.Group()

  player = None

  for row_idx, row in enumerate(LEVEL_MAP):
    for col_idx, char in enumerate(row):
      x = col_idx * TILE_SIZE
      y = row_idx * TILE_SIZE
      if char == 'W':
        wall = Wall(x, y)
        walls_group.add(wall)
        all_sprites.add(wall)
      elif char == 'D':
        door = Door(x, y)
        doors_group.add(door)
        all_sprites.add(door)
      elif char == 'S':
        zone = StealthZone(x, y)
        stealth_group.add(zone)
        all_sprites.add(zone)
      elif char == 'P':
        player = Player(x + TILE_SIZE // 2, y + TILE_SIZE // 2)
      elif char == 'T':
        # Учитель патрулирует
        patrol_points = [pygame.math.Vector2(x - 96, y + 32), pygame.math.Vector2(x + 96, y + 32)]
        teacher = Teacher(x + 32, y + 32, patrol_points)
        teachers_group.add(teacher)
        all_sprites.add(teacher)

  if player:
    all_sprites.add(player)

  font = pygame.font.SysFont("Arial", 20, bold=True)

  running = True
  while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_e:
          # 1. Открытие/закрытие
          for door in doors_group:
            if player.hitbox.inflate(30, 30).colliderect(door.rect):
              door.toggle()
          # 2. Подножка учителю
          for teacher in teachers_group:
            if teacher.state != "STUNNED" and player.hitbox.inflate(40, 40).colliderect(teacher.hitbox):
              teacher.stun(5.0)

  
    active_obstacles = list(walls_group) + [d for d in doors_group if not d.is_open]
    if player:
      player.update(dt, active_obstacles, stealth_group)
    teachers_group.update(dt, active_obstacles)

    
    screen.fill(BG_COLOR)
    all_sprites.draw(screen)

    
    if player.is_hidden:
      status_txt = font.render("СТАТУС: СПРЯТАЛСЯ В ТЕНЬ / КАБИНКУ", True, (0, 255, 150))
    else:
      status_txt = font.render("СТАТУС: НА ВИДУ", True, (255, 200, 0))
    screen.blit(status_txt, (20, 20))

    pygame.display.flip()

  pygame.quit()
  sys.exit()

if __name__ == "__main__":
  main()
