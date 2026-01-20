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

# Current application context
current_app = "chrome"  # Start with Chrome

# URLs to visit in Chrome
URLS = [
    "stackoverflow.com",
    "github.com",
    "developer.mozilla.org",
    "docs.python.org",
    "gmail.com",
    "google.com/search?q=python+best+practices",
    "google.com/search?q=javascript+tutorials",
    "calendar.google.com",
    "github.com/trending",
    "stackoverflow.com/questions/tagged/python"
]

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
        
        # Add micro-jitter
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

def random_click():
    """Perform a random click"""
    if random.random() < 0.2:  # 20% chance
        pyautogui.click()
        log("Performed click")

def press_key():
    """Press random keys like arrow keys or page down/up"""
    keys = ['down', 'up', 'pagedown', 'pageup']
    key = random.choice(keys)
    pyautogui.press(key)
    log(f"Pressed {key} key")

# ============ CHROME ACTIONS ============

def navigate_to_url():
    """Navigate to a random URL in Chrome"""
    url = random.choice(URLS)
    
    # Click address bar
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.3)
    
    # Type URL with human-like typing speed
    for char in url:
        pyautogui.write(char)
        time.sleep(random.uniform(0.05, 0.15))
    
    time.sleep(0.2)
    pyautogui.press('enter')
    log(f"Navigated to {url}")
    
    # Wait for page to load
    time.sleep(random.uniform(2, 4))

def chrome_action():
    """Perform a random action in Chrome"""
    actions = [
        (random_mouse_move, 0.3),
        (random_scroll, 0.3),
        (random_click, 0.1),
        (press_key, 0.2),
        (navigate_to_url, 0.1)  # 10% chance to navigate
    ]
    
    rand = random.random()
    cumulative = 0
    for action, weight in actions:
        cumulative += weight
        if rand <= cumulative:
            action()
            break

# ============ VS CODE ACTIONS ============

def vscode_switch_tab():
    """Switch between tabs in VS Code"""
    if random.choice([True, False]):
        pyautogui.hotkey('ctrl', 'tab')
        log("VS Code: Switched to next tab")
    else:
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        log("VS Code: Switched to previous tab")

def vscode_quick_open():
    """Use Ctrl+P to open quick file search"""
    pyautogui.hotkey('ctrl', 'p')
    time.sleep(0.3)
    
    # Type some random characters then escape
    random_chars = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(2, 5)))
    for char in random_chars:
        pyautogui.write(char)
        time.sleep(random.uniform(0.1, 0.2))
    
    time.sleep(0.3)
    pyautogui.press('escape')
    log(f"VS Code: Quick open search '{random_chars}'")

def vscode_scroll_code():
    """Scroll through code"""
    scroll_amount = random.randint(-5, 5)
    if scroll_amount != 0:
        pyautogui.scroll(scroll_amount * 50)
        direction = "up" if scroll_amount > 0 else "down"
        log(f"VS Code: Scrolled {direction}")

def vscode_move_cursor():
    """Move cursor with arrow keys"""
    directions = ['up', 'down', 'left', 'right']
    direction = random.choice(directions)
    times = random.randint(1, 5)
    
    for _ in range(times):
        pyautogui.press(direction)
        time.sleep(random.uniform(0.1, 0.3))
    
    log(f"VS Code: Moved cursor {direction} {times} times")

def vscode_action():
    """Perform a random action in VS Code"""
    actions = [
        (vscode_switch_tab, 0.2),
        (vscode_scroll_code, 0.3),
        (vscode_move_cursor, 0.2),
        (random_mouse_move, 0.2),
        (vscode_quick_open, 0.1)
    ]
    
    rand = random.random()
    cumulative = 0
    for action, weight in actions:
        cumulative += weight
        if rand <= cumulative:
            action()
            break

# ============ APP SWITCHING ============

def switch_application():
    """Switch between Chrome and VS Code using Alt+Tab"""
    global current_app
    
    pyautogui.hotkey('alt', 'tab')
    time.sleep(0.5)
    
    if current_app == "chrome":
        current_app = "vscode"
        log(">>> Switched to VS Code <<<")
    else:
        current_app = "chrome"
        log(">>> Switched to Chrome <<<")

def simulate_activity():
    """Perform actions based on current application"""
    if current_app == "chrome":
        chrome_action()
    else:
        vscode_action()

def main():
    global running
    
    print("=" * 60)
    print("  Activity Simulator - Chrome & VS Code Edition")
    print("=" * 60)
    print("\nThis script simulates realistic development activity by:")
    print("  - Navigating to developer sites in Chrome")
    print("  - Switching between VS Code tabs and scrolling code")
    print("  - Alternating between Chrome and VS Code")
    print("\n[!] REQUIREMENTS:")
    print("    - Chrome should be open (will start there)")
    print("    - VS Code should be open and running")
    print("\n[!] Press SPACE BAR to stop the script at any time")
    print("    OR press Ctrl+C")
    print("    OR move mouse to top-left corner for emergency stop")
    print("=" * 60)
    
    # Start keyboard listener in background
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    # Countdown before starting
    for i in range(5, 0, -1):
        print(f"\nStarting in {i}...", end="\r")
        time.sleep(1)
    
    print("\n\n[OK] Script is now running...")
    print("[OK] Starting in Chrome mode...")
    print("[OK] Will switch to VS Code in 2-5 minutes\n")
    
    # Track time in current app
    app_start_time = time.time()
    app_duration = random.uniform(120, 300)  # 2-5 minutes
    
    try:
        while running:
            # Check if it's time to switch apps
            if time.time() - app_start_time >= app_duration:
                switch_application()
                app_start_time = time.time()
                app_duration = random.uniform(120, 300)  # Next duration
            
            # Random interval between actions (3-10 seconds)
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