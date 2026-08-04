import os
import sys
import time
import threading

def watch_parent():
    """
    Monitors parent process status. If parent process dies (ppid == 1),
    terminates backend to prevent zombie processes on macOS/Linux.
    """
    while True:
        if os.getppid() == 1:
            print("[Backend] Parent process died. Exiting to prevent zombie process.", flush=True)
            os._exit(0)
        time.sleep(2)

def start_parent_watcher():
    """
    Starts watch_parent thread in background daemon mode.
    """
    threading.Thread(target=watch_parent, daemon=True).start()
