import sys
import clr
import System

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('WindowsBase')

from System import Uri
from System.Windows import Window, Application, MessageBox, Visibility
from System.Windows.Controls import Canvas, TextBlock
from System.Windows.Shapes import Rectangle
from System.Windows.Media import Brushes, SolidColorBrush, Color
from System.Windows.Threading import DispatcherTimer
from System.Windows.Input import Key
from System.Windows.Markup import XamlReader
from System.IO import StringReader
import random

# Start pyRevit context
from pyrevit import script

# Simple XAML for the Window
xaml_str = """
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="pyRevit Snake" Height="450" Width="400" Focusable="True" WindowStartupLocation="CenterScreen">
    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>
        
        <TextBlock x:Name="ScoreText" Text="Score: 0" FontSize="20" HorizontalAlignment="Center" Margin="5"/>
        <Border Grid.Row="1" BorderBrush="Black" BorderThickness="2" Margin="5">
            <Canvas x:Name="GameCanvas" Background="White" ClipToBounds="True"/>
        </Border>
        
        <Grid x:Name="GameOverGrid" Grid.Row="1" Background="#CCFFFFFF" Visibility="Collapsed">
            <StackPanel VerticalAlignment="Center" HorizontalAlignment="Center">
                <TextBlock Text="GAME OVER!" FontSize="40" FontWeight="Bold" Foreground="Red" HorizontalAlignment="Center" Margin="0,0,0,20"/>
                <Button x:Name="RestartButton" Content="Restart" FontSize="20" Padding="20,10" HorizontalAlignment="Center"/>
            </StackPanel>
        </Grid>
    </Grid>
</Window>
"""

class SnakeGame:
    def __init__(self):
        # Create Window from XAML
        self.window = XamlReader.Parse(xaml_str)
        
        # Connect UI elements
        self.canvas = self.window.FindName("GameCanvas")
        self.score_text = self.window.FindName("ScoreText")
        self.game_over_grid = self.window.FindName("GameOverGrid")
        self.restart_button = self.window.FindName("RestartButton")
        
        self.restart_button.Click += self.restart_click
        
        # Game Settings
        self.tile_size = 20
        self.width_tiles = 0
        self.height_tiles = 0
        self.direction = "Right"
        self.next_direction = "Right"
        self.snake = []
        self.food = None
        self.score = 0
        self.is_running = False
        
        # Timer
        self.timer = DispatcherTimer()
        self.timer.Tick += self.game_tick
        self.timer.Interval = System.TimeSpan.FromMilliseconds(150)
        
        # Events
        self.window.KeyDown += self.on_key_down
        self.window.Loaded += self.on_loaded
        
    def on_loaded(self, sender, args):
        # Calculate grid size based on canvas actual size
        self.width_tiles = int(self.canvas.ActualWidth / self.tile_size)
        self.height_tiles = int(self.canvas.ActualHeight / self.tile_size)
        self.start_game()

    def start_game(self):
        self.snake = [{'x': 5, 'y': 5}, {'x': 4, 'y': 5}, {'x': 3, 'y': 5}]
        self.direction = "Right"
        self.next_direction = "Right"
        self.score = 0
        self.spawn_food()
        self.update_score()
        self.is_running = True
        self.game_over_grid.Visibility = Visibility.Collapsed
        self.timer.Start()
        self.draw()

    def spawn_food(self):
        while True:
            x = random.randint(0, self.width_tiles - 1)
            y = random.randint(0, self.height_tiles - 1)
            # Ensure food doesn't spawn on snake
            on_snake = False
            for part in self.snake:
                if part['x'] == x and part['y'] == y:
                    on_snake = True
                    break
            if not on_snake:
                self.food = {'x': x, 'y': y}
                break

    def on_key_down(self, sender, args):
        if not self.is_running:
            return
            
        key = args.Key
        if key == Key.Up and self.direction != "Down":
            self.next_direction = "Up"
        elif key == Key.Down and self.direction != "Up":
            self.next_direction = "Down"
        elif key == Key.Left and self.direction != "Right":
            self.next_direction = "Left"
        elif key == Key.Right and self.direction != "Left":
            self.next_direction = "Right"

    def game_tick(self, sender, args):
        if not self.is_running:
            return
            
        self.direction = self.next_direction
        
        head = self.snake[0].copy()
        
        if self.direction == "Up":
            head['y'] -= 1
        elif self.direction == "Down":
            head['y'] += 1
        elif self.direction == "Left":
            head['x'] -= 1
        elif self.direction == "Right":
            head['x'] += 1
            
        # Check Collision with Walls
        if head['x'] < 0 or head['x'] >= self.width_tiles or \
           head['y'] < 0 or head['y'] >= self.height_tiles:
            self.game_over()
            return

        # Check Collision with Self
        for part in self.snake:
            if part['x'] == head['x'] and part['y'] == head['y']:
                self.game_over()
                return
        
        self.snake.insert(0, head)
        
        # Check Food
        if head['x'] == self.food['x'] and head['y'] == self.food['y']:
            self.score += 10
            self.update_score()
            self.spawn_food()
            # Increase speed slightly? Maybe later
        else:
            self.snake.pop() # Remove tail if didn't eat
            
        self.draw()

    def game_over(self):
        self.is_running = False
        self.timer.Stop()
        self.game_over_grid.Visibility = Visibility.Visible

    def restart_click(self, sender, args):
        self.start_game()

    def update_score(self):
        self.score_text.Text = "Score: {}".format(self.score)

    def draw(self):
        self.canvas.Children.Clear()
        
        # Draw Food
        r = Rectangle()
        r.Width = self.tile_size - 2
        r.Height = self.tile_size - 2
        r.Fill = Brushes.Red
        Canvas.SetLeft(r, self.food['x'] * self.tile_size + 1)
        Canvas.SetTop(r, self.food['y'] * self.tile_size + 1)
        self.canvas.Children.Add(r)
        
        # Draw Snake
        for part in self.snake:
            r = Rectangle()
            r.Width = self.tile_size - 2
            r.Height = self.tile_size - 2
            r.Fill = Brushes.Green
            Canvas.SetLeft(r, part['x'] * self.tile_size + 1)
            Canvas.SetTop(r, part['y'] * self.tile_size + 1)
            self.canvas.Children.Add(r)

    def show(self):
        # pyRevit output window handling might interfere, best to showDialog
        self.window.ShowDialog()

if __name__ == "__main__":
    game = SnakeGame()
    game.show()
