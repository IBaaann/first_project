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
    self.hitbox = pygame.Rect(0, 0, 24, 24)
    self.hitbox.center = (x, y)
    
    self.rect = self.image.get_rect(center= self.hitbox.center)
    
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
    self.hitbox.centerx = round(self.pos.x)
    for wall in walls:
      if self.hitbox.colliderect(wall.rect):
        if move_vec.x > 0:
          self.hitbox.right = wall.rect.left
        if move_vec.x < 0:
          self.hitbox.left = wall.rect.right
        self.pos.x = self.hitbox.centerx
        
    self.pos.y += move_vec.y * self.speed * dt
    self.hitbox.centery = round(self.pos.y)
    for wall in walls:
      if self.hitbox.colliderect(wall.rect):
        if move_vec.y > 0:
          self.hitbox.bottom = wall.rect.top
        if move_vec.y < 0:
          self.hitbox.top = wall.rect.bottom
        self.pos.y = self.hitbox.centery
        

    

  
  def rotate_towards_mouse(self):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    rel_x, rel_y = mouse_x - self.pos.x, mouse_y - self.pos.y
    self.angle = math.degrees(math.atan2(-rel_y, rel_x))
    
    self.image = pygame.transform.rotate(self.original_image, self.angle)
    self.rect = self.image.get_rect(center=self.hitbox.center)
    
  
  def update(self, dt, walls):
    self.move_and_collide(dt, walls)
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
    if player:
      player.update(dt, walls_group)
    
    screen.fill(bg_color)
    all_sprites.draw(screen)
    
    pygame.display.flip()
    
  pygame.quit()
  sys.exit()

if __name__ == '__main__':
  main()

        
    
    
    



