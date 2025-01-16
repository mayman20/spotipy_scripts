import psutil # type: ignore
from pywinauto import Desktop # type: ignore

def list_chrome_windows():
    desktop = Desktop(backend="uia")
    chrome_windows = []
    
    # Iterate through all open windows
    for window in desktop.windows():
        try:
            pid = window.process_id()
            process = psutil.Process(pid)
            if 'chrome.exe' in process.name().lower():
                title = window.window_text()
                if title:  # Ensure the window has a title
                    chrome_windows.append(title)
        except Exception as e:
            # Handle any exceptions (e.g., access denied)
            print(f"Error accessing window: {e}")
    
    return chrome_windows

if __name__ == "__main__":
    windows = list_chrome_windows()
    if windows:
        print("Current Chrome Window Titles:")
        for title in windows:
            print(f" - {title}")
    else:
        print("No Chrome windows found.")
