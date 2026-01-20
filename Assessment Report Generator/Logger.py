import pyautogui
import random
import time
import math
from datetime import datetime
from pynput import keyboard

# Prevent pyautogui from throwing exception on mouse movement to corner
pyautogui.FAILSAFE = True

# Global flag for stopping the script
running = True

def log(message):
    """Print timestamped log messages"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def on_press(key):
    """Keyboard listener callback for space bar"""
    global running
    try:
        if key == keyboard.Key.space:
            log("Space bar pressed - stopping script...")
            running = False
            return False  # Stop listener
    except AttributeError:
        pass

def human_like_mouse_move(dest_x, dest_y):
    """
    Move mouse with human-like curves, acceleration, and deceleration
    Uses Bezier curves for natural movement
    """
    start_x, start_y = pyautogui.position()
    
    # Generate control points for Bezier curve
    # Add some randomness to create curved paths
    cp1_x = start_x + random.randint(-100, 100)
    cp1_y = start_y + random.randint(-100, 100)
    cp2_x = dest_x + random.randint(-100, 100)
    cp2_y = dest_y + random.randint(-100, 100)
    
    # Number of steps (more = smoother)
    steps = random.randint(20, 40)
    
    # Calculate total duration with some randomness
    distance = math.sqrt((dest_x - start_x)**2 + (dest_y - start_y)**2)
    base_duration = distance / 1000  # Adjust speed
    duration = base_duration + random.uniform(-0.2, 0.5)
    duration = max(0.3, duration)  # Minimum duration
    
    for i in range(steps + 1):
        t = i / steps
        
        # Ease in-out function for acceleration/deceleration
        # Makes movement faster in middle, slower at start/end
        if t < 0.5:
            ease_t = 2 * t * t  # Accelerate
        else:
            ease_t = -1 + (4 - 2 * t) * t  # Decelerate
        
        # Cubic Bezier curve formula
        x = (1-ease_t)**3 * start_x + \
            3 * (1-ease_t)**2 * ease_t * cp1_x + \
            3 * (1-ease_t) * ease_t**2 * cp2_x + \
            ease_t**3 * dest_x
        
        y = (1-ease_t)**3 * start_y + \
            3 * (1-ease_t)**2 * ease_t * cp1_y + \
            3 * (1-ease_t) * ease_t**2 * cp2_y + \
            ease_t**3 * dest_y
        
        # Add micro-jitter (human hands aren't perfectly smooth)
        jitter_x = random.uniform(-2, 2)
        jitter_y = random.uniform(-2, 2)
        
        pyautogui.moveTo(int(x + jitter_x), int(y + jitter_y), _pause=False)
        time.sleep(duration / steps)
    
    # Ensure we end exactly at destination
    pyautogui.moveTo(dest_x, dest_y, _pause=False)

def random_mouse_move():
    """Move mouse to random position on screen with human-like movement"""
    screen_width, screen_height = pyautogui.size()
    x = random.randint(100, screen_width - 100)
    y = random.randint(100, screen_height - 100)
    human_like_mouse_move(x, y)
    log(f"Moved mouse to ({x}, {y})")

def random_scroll():
    """Scroll up or down randomly"""
    scroll_amount = random.randint(-3, 3)
    if scroll_amount != 0:
        pyautogui.scroll(scroll_amount * 100)
        direction = "up" if scroll_amount > 0 else "down"
        log(f"Scrolled {direction}")

def random_tab_switch():
    """Switch between browser tabs"""
    if random.choice([True, False]):
        pyautogui.hotkey('ctrl', 'tab')
        log("Switched to next tab")
    else:
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        log("Switched to previous tab")

def random_click():
    """Perform a random click"""
    if random.random() < 0.3:  # 30% chance
        pyautogui.click()
        log("Performed click")

def press_key():
    """Press random keys like arrow keys or page down/up"""
    keys = ['down', 'up', 'pagedown', 'pageup', 'left', 'right']
    key = random.choice(keys)
    pyautogui.press(key)
    log(f"Pressed {key} key")

def simulate_activity():
    """Main function to simulate various activities"""
    actions = [
        (random_mouse_move, 0.4),    # 40% chance
        (random_scroll, 0.2),         # 20% chance
        (random_tab_switch, 0.15),    # 15% chance
        (random_click, 0.1),          # 10% chance
        (press_key, 0.15)             # 15% chance
    ]
    
    # Weighted random choice
    rand = random.random()
    cumulative = 0
    for action, weight in actions:
        cumulative += weight
        if rand <= cumulative:
            action()
            break

def main():
    global running
    
    print("=" * 50)
    print("=" * 50)
    print("\nThis script simulates user activity to demonstrate")
    print("that presence-based tracking is not productivity tracking.")
    print("\n[!] Press SPACE BAR to stop the script at any time")
    print("    OR press Ctrl+C")
    print("    OR move mouse to top-left corner for emergency stop")
    print("=" * 50)
    
    # Start keyboard listener in background
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    # Countdown before starting
    for i in range(5, 0, -1):
        print(f"\nStarting in {i}...", end="\r")
        time.sleep(1)
    
    print("\n\n[OK] Script is now running...")
    print("[OK] Keyboard listener active - press SPACE to stop\n")
    
    try:
        while running:
            # Random interval between 3-10 seconds
            wait_time = random.uniform(3, 10)
            
            # Split wait time into smaller chunks to check running flag
            elapsed = 0
            while elapsed < wait_time and running:
                time.sleep(0.1)
                elapsed += 0.1
            
            if running:
                simulate_activity()
            
    except KeyboardInterrupt:
        log("\nScript stopped by Ctrl+C")
    except Exception as e:
        log(f"\nError occurred: {str(e)}")
    finally:
        listener.stop()
        log("Script terminated successfully")

if __name__ == "__main__":
    # Check if required libraries are available
    try:
        import pyautogui
    except ImportError:
        print("Error: pyautogui is not installed")
        print("Install it using: pip install pyautogui")
        exit(1)
    
    try:
        from pynput import keyboard
    except ImportError:
        print("Error: pynput is not installed")
        print("Install it using: pip install pynput")
        exit(1)
    
    main()