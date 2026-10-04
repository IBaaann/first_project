import sys
import math
import pygame

pygame.init()

screen_width = 1280
screen_height = 720
fps = 60
TILE_SIZE = 64

bg_color = (15, 18, 24)
wall_color = (40, 50, 68)
wall_border_color = (60, 85, 115)
player_color = (0, 220, 130)
dir_pointer_color = (255, 255, 255)


level_map = ['WWWWWWWWWWWWWWWWWWWW',
             'W..................W',
             'W..WWWWWW...WWWW...W',
             'W..W........W......W',
             'W..W...P....W..WWWWW',
             'W..WWWWWW...W......W',
             'W.......W...WWWW...W',
             'WWWW....W..........W',
             'W.......WWWWWWWW...W',
             'W..................W',
             'WWWWWWWWWWWWWWWWWWWW']


class Wall(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
    self.image.fill(wall_color)
    pygame.draw.rect(self.image, wall_border_color, (0, 0, TILE_SIZE, TILE_SIZE), 2)
    self.rect = self.image.get_rect(topleft = (x, y))



class Player(pygame.sprite.Sprite):
  def __init__(self, x, y):
    super().__init__()
    self.original_image = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(self.original_image, player_color, (16, 16), 16)
    pygame.draw.line(self.original_image, dir_pointer_color, (16, 16), (30, 16), 3)
    
    self.image = self.original_image
    self.rect = self.image.get_rect(center=(x, y))
    
    #физика
    self.pos = pygame.math.Vector2(x, y)
    self.speed = 300 #частота в секунду
    self.angle = 0
    
    
  def get_input(self):
    keys = pygame.key.get_pressed()
    move_vec = pygame.math.Vector2(0, 0)
    
    if keys[pygame.K_w] or keys[pygame.K_UP]:
      move_vec.y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
      move_vec.y += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
      move_vec.x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
      move_vec.x += 1
    
    if move_vec.length_squared() > 0:
      move_vec = move_vec.normalize()
    
    return move_vec
  
  def move_and_collide(self, dt, walls):
    move_vec = self.get_input()
    
    #Движение по x
    self.pos.x += move_vec.x * self.speed * dt
    self.rect.centerx = round(self.pos.x)
    self.check_collision('x', walls, move_vec.x)
    
    #Движение по y
    self.pos.y += move_vec.y * self.speed * dt
    self.rect.centery = round(self.pos.y)
    self.check_collision('y', walls, move_vec.y)
    
  def check_collision(self, direction, walls, vel_component):
    hits = pygame.sprite.spritecollide(self, walls, False)
    if hits:
      if direction == 'x':
        if vel_component > 0:
          self.rect.right = hits[0].rect.left
        if vel_component < 0:
          self.rect.left = hits[0].rect.right
        self.pos.x = self.rect.centerx
      if direction == 'y':
        if vel_component > 0:
          self.rect.bottom = hits[0].rect.top
        if vel_component < 0:
          self.rect.top = hits[0].rect.bottom
        self.pos.y = self.rect.centery
          
  
  
  def rotate_towards_mouse(self):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    rel_x, rel_y = mouse_x - self.pos.x, mouse_y - self.pos.y
    self.angle = math.degrees(math.atan2(-rel_y, rel_x))
    
    self.image = pygame.transform.rotate(self.original_image, self.angle)
    self.rect = self.image.get_rect(center=self.rect.center)
    
  
  def update(self, dt, walls):
    self.move_and_collide(dt, walls)
    #move_vec = self.get_input()
    #self.pos += move_vec * self.speed * dt
    #self.rect.center = self.pos
    
    self.rotate_towards_mouse()
    






def main():
  screen = pygame.display.set_mode((screen_width, screen_height))
  pygame.display.set_caption('sleth')
  clock = pygame.time.Clock()
  
  walls_group = pygame.sprite.Group()
  all_sprites = pygame.sprite.Group()
  
  player = None
  
  for row_idx, row in enumerate(level_map):
    for col_idx, char in enumerate(row):
      x = col_idx * TILE_SIZE
      y = row_idx * TILE_SIZE
      if char == 'W':
        wall = Wall(x, y)
        walls_group.add(wall)
        all_sprites.add(wall)
      elif char == 'P':
        player = Player(x + TILE_SIZE // 2, y + TILE_SIZE // 2)
  if player:
    all_sprites.add(player)
  
  running = True
  while running:
    dt = clock.tick(fps) / 1000.0
    
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
    player.update(dt, walls_group)
    
    screen.fill(bg_color)
    all_sprites.draw(screen)
    
    pygame.display.flip()
    
  pygame.quit()
  sys.exit()

if __name__ == '__main__':
  main()

        
    
    
    



