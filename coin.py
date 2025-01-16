import subprocess
import time
import os
from screeninfo import get_monitors # type: ignore
from pywinauto import Desktop # type: ignore
from pywinauto.keyboard import send_keys # type: ignore
import psutil # type: ignore

# Install required libraries if not already installed:
# pip install screeninfo pywinauto psutil

# Paths to Chrome executable and URLs
chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"  # Update if necessary
bitcoin_url = "https://www.google.com/search?q=bitcoin+price&rlz=1C1CHBF_enUS853US853&oq=bitcoin+price&gs_lcrp=EgZjaHJvbWUqDggAEEUYJxg7GIAEGIoFMg4IABBFGCcYOxiABBiKBTITCAEQABiDARiRAhixAxiABBiKBTINCAIQABiDARixAxiABDINCAMQABiDARixAxiABDINCAQQABiDARixAxiABDINCAUQABiDARixAxiABDINCAYQABiDARixAxiABDIGCAcQRRg80gEIMTUxMWoxajmoAgCwAgE&sourceid=chrome&ie=UTF-8"
ethereum_url = "https://www.google.com/search?q=eth+price&rlz=1C1CHBF_enUS853US853&oq=eth+price&gs_lcrp=EgZjaHJvbWUqDggAEEUYJxg7GIAEGIoFMg4IABBFGCcYOxiABBiKBTIGCAEQRRhAMhIIAhAAGEMYgwEYsQMYgAQYigUyDQgDEAAYgwEYsQMYgAQyEggEEAAYQxiDARixAxiABBiKBTIMCAUQABhDGIAEGIoFMhIIBhAAGEMYgwEYsQMYgAQYigUyBggHEEUYPNIBCDMxNTZqMWo5qAIAsAIA&sourceid=chrome&ie=UTF-8"

# Function to verify Chrome path
def verify_chrome_path(path):
    return os.path.exists(path)

if not verify_chrome_path(chrome_path):
    print(f"Chrome executable not found at: {chrome_path}")
    print("Please verify the path and update the 'chrome_path' variable accordingly.")
    exit()

# Get monitor information
monitors = get_monitors()

print("\nDetected Monitors:")
for i, m in enumerate(monitors):
    print(f"Monitor {i}: x={m.x}, y={m.y}, width={m.width}, height={m.height}")

# Ensure at least two monitors are detected
if len(monitors) < 2:
    print("\nA secondary monitor was not detected. Please ensure it is connected and configured as an extended display.")
    exit()

# Use the secondary monitor (assuming it's the second in the list)
secondary_monitor = monitors[1]
secondary_x, secondary_y = secondary_monitor.x, secondary_monitor.y
secondary_width, secondary_height = secondary_monitor.width, secondary_monitor.height

print(f"\nSecondary Monitor - x: {secondary_x}, y: {secondary_y}, width: {secondary_width}, height: {secondary_height}")

# Define window sizes and positions (each window takes up a quarter of the secondary monitor)
window_width = secondary_width // 2
window_height = secondary_height // 2

# Bitcoin window at top-right quarter
bitcoin_x = secondary_x + window_width
bitcoin_y = secondary_y

# Ethereum window at bottom-right quarter
ethereum_x = secondary_x + window_width
ethereum_y = secondary_y + window_height

# Define unique user data directories for separate Chrome instances
bitcoin_profile = os.path.abspath("bitcoin_profile")
ethereum_profile = os.path.abspath("ethereum_profile")

# Create the profile directories if they don't exist
os.makedirs(bitcoin_profile, exist_ok=True)
os.makedirs(ethereum_profile, exist_ok=True)

# Launch Chrome windows with unique profiles and '--app' flag
print("\nLaunching Bitcoin window...")
subprocess.Popen([
    chrome_path,
    "--app=" + bitcoin_url,
    "--new-window",
    f"--user-data-dir={bitcoin_profile}",
    f"--window-position={bitcoin_x},{bitcoin_y}",
    f"--window-size={window_width},{window_height}"
])

time.sleep(3)  # Wait for the first window to open

print("Launching Ethereum window...")
subprocess.Popen([
    chrome_path,
    "--app=" + ethereum_url,
    "--new-window",
    f"--user-data-dir={ethereum_profile}",
    f"--window-position={ethereum_x},{ethereum_y}",
    f"--window-size={window_width},{window_height}"
])

print("\nChrome windows launched. Waiting for them to initialize...")
time.sleep(5)  # Wait for the windows to fully open

# Using pywinauto to interact with the windows
desktop = Desktop(backend="uia")

# Function to move and resize window using pywinauto by partial title
def move_and_resize_window(partial_title, x, y, width, height):
    try:
        # Find all windows that contain the partial title (case-insensitive)
        windows = desktop.windows(title_re=f".*{partial_title}.*")
        if not windows:
            print(f"No window found with title containing '{partial_title}'.")
            return
        for window in windows:
            # Get the process ID
            pid = window.process_id()
            try:
                process = psutil.Process(pid)
                if 'chrome.exe' in process.name().lower():
                    # Move and resize
                    window.move_window(x, y, width, height, repaint=True)
                    print(f"Moved and resized window: '{window.window_text()}' to ({x}, {y}, {width}, {height})")
                    return  # Assume only one window per partial_title
            except psutil.NoSuchProcess:
                print(f"No process found with PID {pid}.")
        print(f"No Chrome window found with title containing '{partial_title}'.")
    except Exception as e:
        print(f"Error moving window with title containing '{partial_title}': {e}")

# Function to scroll down the window by sending keystrokes
def scroll_window(partial_title, scroll_amount=1):
    try:
        # Find all windows that contain the partial title (case-insensitive)
        windows = desktop.windows(title_re=f".*{partial_title}.*")
        if not windows:
            print(f"No window found with title containing '{partial_title}' for scrolling.")
            return
        for window in windows:
            # Get the process ID
            pid = window.process_id()
            try:
                process = psutil.Process(pid)
                if 'chrome.exe' in process.name().lower():
                    # Set focus to the window
                    window.set_focus()
                    print(f"Setting focus to window: '{window.window_text()}'")
                    time.sleep(0.5)  # Brief pause to ensure focus
                    # Scroll down using Page Down key
                    for _ in range(scroll_amount):
                        send_keys("{PGDN}", pause=0.1)
                    print(f"Scrolled window: '{window.window_text()}' down by {scroll_amount} page(s).")
                    return  # Assume only one window per partial_title
            except psutil.NoSuchProcess:
                print(f"No process found with PID {pid}.")
        print(f"No Chrome window found with title containing '{partial_title}' for scrolling.")
    except Exception as e:
        print(f"Error scrolling window with title containing '{partial_title}': {e}")

# Debugging: List all current Chrome window titles
print("\nCurrent Chrome Window Titles:")
for window in desktop.windows():
    try:
        pid = window.process_id()
        process = psutil.Process(pid)
        if 'chrome.exe' in process.name().lower():
            title = window.window_text()
            if title:
                print(f" - {title}")
    except Exception as e:
        print(f"Error accessing window: {e}")


bitcoin_window_name = "bitcoin price - Google Search"
ethereum_window_name = "eth price - Google Search"
# Position Bitcoin window at the top-right quarter of the secondary monitor
move_and_resize_window(bitcoin_window_name, bitcoin_x, bitcoin_y, window_width, window_height)

# Position Ethereum window at the bottom-right quarter of the secondary monitor
move_and_resize_window(ethereum_window_name, ethereum_x, ethereum_y, window_width, window_height)


print("\nWindows positioned and scrolled successfully on the secondary monitor.")
