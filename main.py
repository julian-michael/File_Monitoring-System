import sys
import time
import logging
import zipfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, DirCreatedEvent, DirModifiedEvent, DirMovedEvent,DirDeletedEvent
import os
from datetime import datetime, timedelta
import threading
import multiprocessing
import gc
# import psutil

# Define the file types to monitor
FILE_TYPES = ('.xlsx', '.xls', '.docx', '.doc', '.cpp', '.h', '.txt', '.jpg', '.png', '.pdf', '.exe', '.ppt')

# Create a log directory if not exists
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Function to get all available drives
def get_available_drives():
    drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    return drives

# Create or update log file
def get_log_file_path(drive):
    current_time = datetime.now()
    date_str = current_time.strftime('%Y-%m-%d')
    drive_log_dir = os.path.join(LOG_DIR, drive.replace(':\\', ''))
    if not os.path.exists(drive_log_dir):
        os.makedirs(drive_log_dir)
    log_file = os.path.join(drive_log_dir, f'{date_str}.log')
    return log_file

# Automatically clean up old log files
def clean_up_old_logs():
    while True:
        now = datetime.now()
        for root, dirs, files in os.walk(LOG_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if now - file_time > timedelta(days=30):
                    os.remove(file_path)
                    logging.info(f'Removed old log file: {file_path}')
        time.sleep(86400)  # Check every 24 hours

class CustomEventHandler(FileSystemEventHandler):
    def __init__(self, drive):
        self.drive = drive
        self.log_file = get_log_file_path(drive)
        self.setup_logging()
        self.last_compress_time = datetime.now()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()])

    def rotate_log(self):
        current_time = datetime.now()
        if os.path.basename(self.log_file) != f'{current_time.strftime("%Y-%m-%d")}.log':
            self.log_file = get_log_file_path(self.drive)
            self.setup_logging()

    def on_any_event(self, event):
        self.rotate_log()

    def on_created(self, event):
        if isinstance(event, DirCreatedEvent):
            logging.info(f'Directory created: {event.src_path}')
        else:
            logging.info(f'File created: {event.src_path}')


    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            if event.src_path.endswith(FILE_TYPES):
                logging.info(f'File modified: {event.src_path}')
        elif isinstance(event, DirModifiedEvent):
            logging.info(f'Directory modified: {event.src_path}')

    def on_deleted(self, event):
        if event.src_path.endswith(FILE_TYPES):
            logging.info(f'File deleted: {event.src_path}')
        elif isinstance(event, DirDeletedEvent):
            logging.info(f'Directory deleted: {event.src_path}')

    def on_moved(self, event):
         if isinstance(event, DirMovedEvent):
            logging.info(f'Directory moved from {event.src_path} to {event.dest_path}')
         else:
            logging.info(f'File moved from {event.src_path} to {event.dest_path}')


def monitor_drive(drive):
    path = f'{drive}\\'
    if os.path.exists(path):
        event_handler = CustomEventHandler(drive)
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        logging.info(f'Start watching drive {drive!r}')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

def garbage_collector():
    while True:
        gc.collect()
        time.sleep(60)  # Run garbage collection every 60 seconds

def auto_start_monitoring():
    drives = get_available_drives()
    processes = []
    for drive in drives:
        process = multiprocessing.Process(target=monitor_drive, args=(drive,))
        process.start()
        processes.append(process)
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    # Start garbage collector in a separate thread
    gc_thread = threading.Thread(target=garbage_collector)
    gc_thread.daemon = True
    gc_thread.start()

    # Start log cleanup thread
    cleanup_thread = threading.Thread(target=clean_up_old_logs)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    auto_start_monitoring()
