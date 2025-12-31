import sys
import clr
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

clr.AddReference('System.Xml')
import math
import random
import System
from System import Uri
from System.Xml import XmlReader
from System.Windows import Application, Window, Input, Media, Threading, Controls, Shapes, Point
from System.Windows.Media import Brushes, SolidColorBrush, RotateTransform, TranslateTransform, TransformGroup, PointCollection
from System.Windows.Controls import Canvas
from System.Windows.Markup import XamlReader
from System.IO import StringReader

# --- Game Constants ---
WIDTH = 800
HEIGHT = 600
SHIP_SIZE = 15
ASTEROID_SIZE_LARGE = 40
ASTEROID_SIZE_MEDIUM = 20
ASTEROID_SIZE_SMALL = 10
BULLET_SPEED = 10
SHIP_THRUST = 0.5
SHIP_TURN_SPEED = 5
FRICTION = 0.99
MAX_SPEED = 10
SAFE_ZONE = 100 # Distance from center clear of asteroids at start

# --- XAML Definition ---
xaml_str = """
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="PyRevit Asteroids" Height="600" Width="800" Background="Black" WindowStartupLocation="CenterScreen">
    <Grid>
        <Canvas x:Name="gameCanvas" Focusable="True" Background="Black"/>
        <TextBlock x:Name="scoreText" Text="Score: 0" Foreground="White" FontSize="20" Margin="10,10,0,0" HorizontalAlignment="Left" VerticalAlignment="Top"/>
        <TextBlock x:Name="gameOverText" Text="GAME OVER\nPress R to Restart" TextAlignment="Center" Foreground="Red" FontSize="40" HorizontalAlignment="Center" VerticalAlignment="Center" Visibility="Hidden"/>
        <TextBlock x:Name="instructionsText" Text="Arrows: Move/Rotate | Space: Shoot" Foreground="Gray" FontSize="12" Margin="0,0,10,10" HorizontalAlignment="Right" VerticalAlignment="Bottom"/>
    </Grid>
</Window>
"""

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class GameObject(object):
    WIDTH = 800
    HEIGHT = 600

    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.angle = 0
        self.active = True
        self.shape = None

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Screen wrapping
        if self.x < 0: self.x = self.WIDTH
        if self.x > self.WIDTH: self.x = 0
        if self.y < 0: self.y = self.HEIGHT
        if self.y > self.HEIGHT: self.y = 0
        
        self.draw()

    def draw(self):
        if self.shape:
            # Update transformation
            group = TransformGroup()
            group.Children.Add(RotateTransform(self.angle, 0, 0)) # Rotate around defined center usually, but here we translate shape
            group.Children.Add(TranslateTransform(self.x, self.y))
            self.shape.RenderTransform = group

    def destroy(self):
        if self.shape and self.active:
            self.canvas.Children.Remove(self.shape)
            self.active = False

class Bullet(GameObject):
    BULLET_SPEED = 10

    def __init__(self, canvas, x, y, angle):
        GameObject.__init__(self, canvas, x, y)
        self.angle = angle
        rad = math.radians(angle)
        
        speed = self.BULLET_SPEED
        self.vel_x = math.sin(rad) * speed
        self.vel_y = -math.cos(rad) * speed
        self.life = 60 # Frames to live
        
        self.shape = Shapes.Ellipse()
        self.shape.Width = 4
        self.shape.Height = 4
        self.shape.Fill = Brushes.White
        # Center anchor
        self.shape.RenderTransformOrigin = Point(0.5, 0.5)
        self.canvas.Children.Add(self.shape)
        self.draw()

    def update(self):
        super(Bullet, self).update()
        self.life -= 1
        if self.life <= 0:
            self.destroy()

class Asteroid(GameObject):
    SIZE_LARGE = 40
    SIZE_MEDIUM = 20
    SIZE_SMALL = 10

    def __init__(self, canvas, x, y, size_category):
        GameObject.__init__(self, canvas, x, y)
        self.size_category = size_category
        
        # Determine properties based on size
        if size_category == 3: # Large
            self.radius = self.SIZE_LARGE
            speed_mult = 1
            self.score_val = 20
        elif size_category == 2: # Medium
            self.radius = self.SIZE_MEDIUM
            speed_mult = 1.5
            self.score_val = 50
        else: # Small
            self.radius = self.SIZE_SMALL
            speed_mult = 2.0
            self.score_val = 100
            
        # Random velocity
        angle = random.uniform(0, 360)
        speed = random.uniform(0.5, 2.0) * speed_mult
        rad = math.radians(angle)
        self.vel_x = math.cos(rad) * speed
        self.vel_y = math.sin(rad) * speed
        
        self.rot_speed = random.uniform(-2, 2)

        # Create jagged polygon shape
        self.shape = Shapes.Polygon()
        self.shape.Stroke = Brushes.White
        self.shape.StrokeThickness = 1
        points = PointCollection()
        num_points = random.randint(8, 12)
        for i in range(num_points):
            angle_p = (i / float(num_points)) * 2 * math.pi
            r = self.radius * random.uniform(0.8, 1.2)
            px = math.cos(angle_p) * r
            py = math.sin(angle_p) * r
            points.Add(Point(px, py))
        
        self.shape.Points = points
        self.canvas.Children.Add(self.shape)
        self.draw()

    def update(self):
        super(Asteroid, self).update()
        self.angle += self.rot_speed
        
class Ship(GameObject):
    def __init__(self, canvas, x, y):
        GameObject.__init__(self, canvas, x, y)
        self.FRICTION = 0.99
        self.THRUST = 0.5
        self.TURN_SPEED = 5
        self.MAX_SPEED = 10
        self.SHIP_SIZE = 15

        self.shape = Shapes.Polygon()
        self.shape.Stroke = Brushes.White
        self.shape.StrokeThickness = 1
        
        # Triangle shape pointing up
        points = PointCollection()
        points.Add(Point(0, -self.SHIP_SIZE))
        points.Add(Point(self.SHIP_SIZE/2, self.SHIP_SIZE))
        points.Add(Point(0, self.SHIP_SIZE*0.8)) # Indent at bottom
        points.Add(Point(-self.SHIP_SIZE/2, self.SHIP_SIZE))
        self.shape.Points = points
        
        self.canvas.Children.Add(self.shape)
        self.draw()
        
    def thrust(self):
        rad = math.radians(self.angle)
        self.vel_x += math.sin(rad) * self.THRUST
        self.vel_y -= math.cos(rad) * self.THRUST
        
        # Cap speed
        speed = math.sqrt(self.vel_x**2 + self.vel_y**2)
        if speed > self.MAX_SPEED:
            scale = self.MAX_SPEED / speed
            self.vel_x *= scale
            self.vel_y *= scale

    def turn(self, direction):
        self.angle += direction * self.TURN_SPEED

    def update(self):
        # Friction
        self.vel_x *= self.FRICTION
        self.vel_y *= self.FRICTION
        super(Ship, self).update()

class AsteroidsGameWindow(Window):
    WIDTH = 800
    HEIGHT = 600
    SAFE_ZONE = 100

    def __init__(self):
        # Load XAML
        reader = StringReader(xaml_str)
        try:
            self.window = XamlReader.Load(XmlReader.Create(reader))
        except Exception as e:
            print("Error loading XAML: {}".format(e))
            return

        # Controls
        self.canvas = self.window.FindName("gameCanvas")
        self.scoreText = self.window.FindName("scoreText")
        self.gameOverText = self.window.FindName("gameOverText")
        
        # Game State
        self.score = 0
        self.game_over = False
        self.left_down = False
        self.right_down = False
        self.up_down = False
        self.space_down = False
        self.space_prev = False
        
        self.ship = None
        self.bullets = []
        self.asteroids = []
        
        # Events
        self.window.KeyDown += self.KeyDown
        self.window.KeyUp += self.KeyUp
        
        # Game Loop
        self.timer = Threading.DispatcherTimer()
        self.timer.Interval = System.TimeSpan.FromMilliseconds(16) # ~60 FPS
        self.timer.Tick += self.GameLoop
        
        # Start
        self.InitGame()
        self.window.ShowDialog()

    def InitGame(self):
        self.canvas.Children.Clear()
        self.score = 0
        self.scoreText.Text = "Score: 0"
        self.game_over = False
        self.gameOverText.Visibility = System.Windows.Visibility.Hidden
        
        self.bullets = []
        self.asteroids = []
        
        # Center ship
        cx = self.WIDTH / 2
        cy = self.HEIGHT / 2
        self.ship = Ship(self.canvas, cx, cy)
        
        # Create initial asteroids (avoid center)
        for _ in range(5):
            self.SpawnAsteroid(safe_x=cx, safe_y=cy)
            
        self.timer.Start()

    def SpawnAsteroid(self, x=None, y=None, size=3, safe_x=None, safe_y=None):
        if x is None:
            # Random position, retry if too close to safe zone
            while True:
                x = random.randint(0, self.WIDTH)
                y = random.randint(0, self.HEIGHT)
                if safe_x is not None:
                    dist = math.sqrt((x-safe_x)**2 + (y-safe_y)**2)
                    if dist < self.SAFE_ZONE + 50:
                        continue
                break
        
        ast = Asteroid(self.canvas, x, y, size)
        self.asteroids.append(ast)

    def KeyDown(self, sender, e):
        if e.Key == Input.Key.Left: self.left_down = True
        if e.Key == Input.Key.Right: self.right_down = True
        if e.Key == Input.Key.Up: self.up_down = True
        if e.Key == Input.Key.Space: self.space_down = True
        if e.Key == Input.Key.R and self.game_over:
            self.InitGame()

    def KeyUp(self, sender, e):
        if e.Key == Input.Key.Left: self.left_down = False
        if e.Key == Input.Key.Right: self.right_down = False
        if e.Key == Input.Key.Up: self.up_down = False
        if e.Key == Input.Key.Space: self.space_down = False

    def CheckCollisions(self):
        # Bullet vs Asteroid
        bullets_to_remove = []
        asteroids_to_remove = []
        
        for b in self.bullets:
            if not b.active: continue
            for a in self.asteroids:
                if not a.active: continue
                
                dist = math.sqrt((b.x - a.x)**2 + (b.y - a.y)**2)
                if dist < a.radius:
                    bullets_to_remove.append(b)
                    asteroids_to_remove.append(a)
                    self.score += a.score_val
                    self.scoreText.Text = "Score: {}".format(self.score)
                    
                    # Split asteroid
                    if a.size_category > 1:
                        self.SpawnAsteroid(a.x, a.y, a.size_category - 1)
                        self.SpawnAsteroid(a.x, a.y, a.size_category - 1)
                    break
        
        for b in bullets_to_remove: b.destroy()
        for a in asteroids_to_remove: a.destroy()
        
        # Cleanup inactive lists
        self.bullets = [b for b in self.bullets if b.active]
        self.asteroids = [a for a in self.asteroids if a.active]
        
        # Ship vs Asteroid
        if not self.ship.active: return
        for a in self.asteroids:
            dist = math.sqrt((self.ship.x - a.x)**2 + (self.ship.y - a.y)**2)
            if dist < a.radius + self.ship.SHIP_SIZE/2:
                self.GameOver()

    def GameOver(self):
        self.game_over = True
        self.ship.destroy()
        self.gameOverText.Visibility = System.Windows.Visibility.Visible
        self.timer.Stop()

    def GameLoop(self, sender, e):
        try:
            if self.game_over:
                return

            # Input processing
            if self.left_down: self.ship.turn(-1)
            if self.right_down: self.ship.turn(1)
            if self.up_down: self.ship.thrust()
            if self.space_down and not self.space_prev:
                self.bullets.append(Bullet(self.canvas, self.ship.x, self.ship.y, self.ship.angle))
            
            self.space_prev = self.space_down

            # Updates
            self.ship.update()
            for b in self.bullets: b.update()
            for a in self.asteroids: a.update()
            
            # Level complete check - respawn if all clear
            if not self.asteroids:
                for _ in range(5 + int(self.score / 1000)):
                    self.SpawnAsteroid(safe_x=self.ship.x, safe_y=self.ship.y)

            self.CheckCollisions()
        except Exception as ex:
            print("Game Loop Error: " + str(ex))

if __name__ == "__main__":
    if hasattr(sys.modules['__main__'], '__file__'):
        AsteroidsGameWindow()
