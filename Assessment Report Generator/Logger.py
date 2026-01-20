import pyautogui
import random
import time
from datetime import datetime

# Prevent pyautogui from throwing exception on mouse movement to corner
pyautogui.FAILSAFE = True

def log(message):
    """Print timestamped log messages"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def random_mouse_move():
    """Move mouse to random position on screen"""
    screen_width, screen_height = pyautogui.size()
    x = random.randint(100, screen_width - 100)
    y = random.randint(100, screen_height - 100)
    duration = random.uniform(0.5, 1.5)
    pyautogui.moveTo(x, y, duration=duration)
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
    print("=" * 50)
    print("Activity Simulator - Trackabi Demonstration Tool")
    print("=" * 50)
    print("\nThis script simulates user activity to demonstrate")
    print("that presence-based tracking is not productivity tracking.")
    print("\nPress Ctrl+C to stop the script")
    print("Move mouse to top-left corner for emergency stop")
    print("=" * 50)
    
    # Countdown before starting
    for i in range(5, 0, -1):
        print(f"\nStarting in {i}...", end="\r")
        time.sleep(1)
    
    print("\n\nScript is now running...\n")
    
    try:
        while True:
            # Random interval between 3-10 seconds
            wait_time = random.uniform(3, 10)
            time.sleep(wait_time)
            
            simulate_activity()
            
    except KeyboardInterrupt:
        log("\nScript stopped by user")
    except Exception as e:
        log(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    # Check if pyautogui is available
    try:
        import pyautogui
    except ImportError:
        print("Error: pyautogui is not installed")
        print("Install it using: pip install pyautogui")
        exit(1)
    
    main()