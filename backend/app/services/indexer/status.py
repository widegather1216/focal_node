import asyncio

# Thread-safe global status representation of background indexer
indexing_status = {
    "status": "idle",
    "total_files": 0,
    "processed_files": 0,
    "current_file": ""
}

pause_event = asyncio.Event()
pause_event.set()  # set() means running, clear() means paused
cancel_requested = False

def pause_indexing():
    global indexing_status
    if indexing_status["status"] == "processing":
        pause_event.clear()
        indexing_status["status"] = "paused"
        print("[Indexer] Background indexing paused.", flush=True)

def resume_indexing():
    global indexing_status
    if indexing_status["status"] == "paused":
        pause_event.set()
        indexing_status["status"] = "processing"
        print("[Indexer] Background indexing resumed.", flush=True)

def cancel_indexing():
    global indexing_status, cancel_requested
    if indexing_status["status"] in ["processing", "paused"]:
        cancel_requested = True
        pause_event.set()  # Unblock pause wait if currently paused
        indexing_status["status"] = "cancelled"
        print("[Indexer] Background indexing cancelled.", flush=True)
