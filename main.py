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
CONE_PATROL_COLOR = (255, 255, 100, 60)
CONE_ALERT_COLOR = (255, 40, 40, 120)
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


class Camera():
  def __init__(self, width, height):
    self.offset = pygame.math.Vector2(0, 0)
    self.width = width
    self.height = height
  def update(self, target):
    self.offset.x = target.hitbox.centerx - SCREEN_WIDTH // 2
    self.offset.y = target.hitbox.centery - SCREEN_HEIGHT // 2


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

    self.vision_radius = 280
    self.vision_fov = 60
    self.sees_player = False

    self.image = self.original_image
    self.hitbox = pygame.Rect(0, 0, 24, 24)
    self.hitbox.center = (x, y)
    self.rect = self.image.get_rect(center=self.hitbox.center)

    self.pos = pygame.math.Vector2(x, y)
    self.speed = 120
    self.angle = 0

    #патрулирование
    self.patrol_points = patrol_points
    self.current_point_idx = 0
    self.state = "PATROL"
    self.stun_timer = 0.0

  def stun(self, duration=5.0):
    self.state = "STUNNED"
    self.stun_timer = duration
    self.sees_player = False
    #оглушенние
    stun_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(stun_surf, TEACHER_STUN_COLOR, (16, 16), 16)
    self.image = stun_surf

  def check_vision(self, player, obstacles):
    if self.state == "STUNNED" or player.is_hidden:
      self.sees_player = False
      return False
    
    vec_to_player = player.pos - self.pos
    dist = vec_to_player.length()
    
    if dist > self.vision_radius or dist == 0:
      self.sees_player = False
      return False


    rad = math.radians(-self.angle)
    facing_vec = pygame.math.Vector2(math.cos(rad), math.sin(rad))
    
    angle_between = facing_vec.angle_to(vec_to_player)

    if abs(angle_between) > self.vision_fov / 2:
      self.sees_player = False
      return False
    
    steps = int(dist // 12)
    step_vec = vec_to_player.normalize() * 12
    curr_pos = pygame.math.Vector2(self.pos)
    
    for _ in range(steps):
      curr_pos += step_vec
      for obs in obstacles:
        if obs.rect.collidepoint(curr_pos.x, curr_pos.y):
          self.sees_player = False
          return False
        
    self.sees_player = True
    return True
  
  def move_and_collide(self, dt, obstacles, move_vec):
    self.pos.x += move_vec.x * self.speed * dt
    self.hitbox.centerx = round(self.pos.x)
    for obs in obstacles:
      if self.hitbox.colliderect(obs.rect):
        if move_vec.x > 0: self.hitbox.right = obs.rect.left
        elif move_vec.x < 0: self.hitbox.left = obs.rect.right
        self.pos.x = self.hitbox.centerx
        self.current_point_idx = (self.current_point_idx + 1) % len(self.patrol_points)
    
    self.pos.y += move_vec.y * self.speed * dt
    self.hitbox.centery = round(self.pos.y)
    for obs in obstacles:
      if self.hitbox.colliderect(obs.rect):
        if move_vec.y > 0: self.hitbox.bottom = obs.rect.top
        elif move_vec.y < 0: self.hitbox.top = obs.rect.bottom
        self.pos.y = self.hitbox.centery
        self.current_point_idx = (self.current_point_idx + 1) % len(self.patrol_points)
  
  
  def draw_vision_cone(self, surface, camera_offset):
    if self.state == "STUNNED":
      return
    
    cone_color = CONE_ALERT_COLOR if self.sees_player else CONE_PATROL_COLOR
    cone_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    center = self.pos - camera_offset
    points = [center]
    
    start_angle = self.angle - (self.vision_fov / 2)
    end_angle = self.angle + (self.vision_fov / 2)
    num_rays = 20
    
    for i in range(num_rays + 1):
      curr_angle = start_angle + (end_angle - start_angle) * (i / num_rays)
      rad = math.radians(-curr_angle)
      ray_dir = pygame.math.Vector2(math.cos(rad), math.sin(rad))
      points.append(center + ray_dir * self.vision_radius)
    
    pygame.draw.polygon(cone_surface, cone_color, points)
    surface.blit(cone_surface, (0, 0))



  def update(self, dt, walls, obstacles, player):
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
      target = self.patrol_points[self.current_point_idx]
      move_vec = target - self.pos

    if move_vec.length() > 0:
      norm_move = move_vec.normalize()
      step = norm_move * self.speed * dt

      # Движение по X
      self.pos.x += step.x
      self.hitbox.centerx = round(self.pos.x)
      for obstacle in walls:
        if self.hitbox.colliderect(obstacle.rect):
          if step.x > 0: self.hitbox.right = obstacle.rect.left
          elif step.x < 0: self.hitbox.left = obstacle.rect.right
          self.pos.x = self.hitbox.centerx

      # Движение по Y
      self.pos.y += step.y
      self.hitbox.centery = round(self.pos.y)
      for obstacle in walls:
        if self.hitbox.colliderect(obstacle.rect):
          if step.y > 0: self.hitbox.bottom = obstacle.rect.top
          elif step.y < 0: self.hitbox.top = obstacle.rect.bottom
          self.pos.y = self.hitbox.centery


      self.angle = math.degrees(math.atan2(-norm_move.y, norm_move.x))
      self.image = pygame.transform.rotate(self.original_image, self.angle)
      self.rect = self.image.get_rect(center=self.hitbox.center)


    self.check_vision(player, obstacles)

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

  def rotate_towards_mouse(self, camera_offset):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_mouse_x = mouse_x + camera_offset.x
    world_mouse_y = mouse_y + camera_offset.y
    rel_x = world_mouse_x - self.pos.x
    rel_y = world_mouse_y - self.pos.y
    self.angle = math.degrees(math.atan2(-rel_y, rel_x))

    self.image = pygame.transform.rotate(self.original_image, self.angle)
    self.rect = self.image.get_rect(center=self.hitbox.center)

  def update(self, dt, obstacles, stealth_zones, camera_offset):
    self.move_and_collide(dt, obstacles)
    self.check_stealth(stealth_zones)
    self.rotate_towards_mouse(camera_offset)



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
        #Учитель патрулирует
        patrol_points = [pygame.math.Vector2(x + 32, y + 32), pygame.math.Vector2(x + 96, y + 280)]
        teacher = Teacher(x + 32, y + 32, patrol_points)
        teachers_group.add(teacher)
        all_sprites.add(teacher)

  if player:
    all_sprites.add(player)

  font = pygame.font.SysFont("Arial", 20, bold=True)
  camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

  running = True
  while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_e:
          #Открытие/закрытие
          for door in doors_group:
            if player.hitbox.inflate(30, 30).colliderect(door.rect):
              door.toggle()
          #Подножка учителю
          for teacher in teachers_group:
            if teacher.state != "STUNNED" and player.hitbox.inflate(40, 40).colliderect(teacher.hitbox):
              teacher.stun(5.0)

  
    active_obstacles = list(walls_group) + [d for d in doors_group if not d.is_open]
    if player:
      camera.update(player)
      player.update(dt, active_obstacles, stealth_group, camera.offset)
    teachers_group.update(dt, active_obstacles, active_obstacles, player)
    

    
    screen.fill(BG_COLOR)
    

    

    for sprite in walls_group:
        screen.blit(sprite.image, sprite.rect.topleft - camera.offset)
    for sprite in doors_group:
        screen.blit(sprite.image, sprite.rect.topleft - camera.offset)
    for sprite in stealth_group:
        screen.blit(sprite.image, sprite.rect.topleft - camera.offset)
        

    for teacher in teachers_group:
        teacher.draw_vision_cone(screen, camera.offset)
        

    for teacher in teachers_group:
        screen.blit(teacher.image, teacher.rect.topleft - camera.offset)
    if player:
        screen.blit(player.image, player.rect.topleft - camera.offset)


    
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
