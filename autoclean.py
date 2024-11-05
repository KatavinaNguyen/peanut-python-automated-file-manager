import os
import datetime
import hashlib
import schedule
import threading
import time
from pathlib import Path
from database import DatabaseHandler

class AutoCleanHandler:
    def __init__(self):
        self.previous_cleaning_time = None
        self.user_home_directory = str(Path.home())
        self.next_cleaning_time = None
        self.frequency = None
        self.clean_recycling_bin_flag = None
        self.clean_browser_history_flag = None
        self.clean_duplicate_files_flag = None
        self.clean_unused_files_flag = None
        self.clean_empty_folders_flag = None
        self.db_handler = DatabaseHandler()
        self.is_running = False
        self.load_settings()

    def load_settings(self):
        try:
            settings = self.db_handler.get_autoclean_settings()
            if settings:
                self.clean_empty_folders_flag = settings['clean_empty_folders_flag']
                self.clean_unused_files_flag = settings['clean_unused_files_flag']
                self.clean_duplicate_files_flag = settings['clean_duplicate_files_flag']
                self.clean_recycling_bin_flag = settings['clean_recycling_bin_flag']
                self.clean_browser_history_flag = settings['clean_browser_history_flag']
                self.frequency = settings['autoclean_frequency']
                next_cleaning_time_str = settings['next_cleaning_time']
                self.next_cleaning_time = datetime.datetime.fromisoformat(
                    next_cleaning_time_str) if next_cleaning_time_str else None
            else:
                self.clean_empty_folders_flag = False
                self.clean_unused_files_flag = False
                self.clean_duplicate_files_flag = False
                self.clean_recycling_bin_flag = False
                self.clean_browser_history_flag = False
        except Exception as e:
            self.db_handler.log_error(f"Error loading settings: {str(e)}")

    def save_settings(self):
        self.db_handler.update_clean_flags(
            clean_empty_folders_flag=self.clean_empty_folders_flag,
            clean_unused_files_flag=self.clean_unused_files_flag,
            clean_duplicate_files_flag=self.clean_duplicate_files_flag,
            clean_recycling_bin_flag=self.clean_recycling_bin_flag,
            clean_browser_history_flag=self.clean_browser_history_flag,
            autoclean_frequency=self.frequency,
            next_cleaning_time=self.next_cleaning_time.isoformat() if self.next_cleaning_time else None
        )

    def set_clean_frequency(self, frequency):
        self.frequency = frequency
        self.update_next_cleaning_time()
        self.save_settings()

    def update_next_cleaning_time(self):
        now = datetime.datetime.now()
        frequency_map = {
            'never': None,
            'day': datetime.timedelta(days=1),
            'week': datetime.timedelta(weeks=1),
            'month': datetime.timedelta(days=30),
            'quarter': datetime.timedelta(days=90),
            'year': datetime.timedelta(days=365)
        }
        self.next_cleaning_time = now + frequency_map.get(self.frequency, datetime.timedelta()) if frequency_map.get(self.frequency) else None

    def get_next_cleaning_time(self):
        if not self.next_cleaning_time:
            return "N/A"
        remaining_time = self.next_cleaning_time - datetime.datetime.now()
        days, seconds = remaining_time.days, remaining_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{days} days {hours} hours {minutes} minutes"

    def toggle_clean_empty_folders(self, value):
        self.clean_empty_folders_flag = value
        self.save_settings()

    def toggle_clean_unused_files(self, value):
        self.clean_unused_files_flag = value
        self.save_settings()

    def toggle_clean_duplicate_files(self, value):
        self.clean_duplicate_files_flag = value
        self.save_settings()

    def toggle_clean_recycling_bin(self, value):
        self.clean_recycling_bin_flag = value
        self.save_settings()

    def toggle_clean_browser_history(self, value):
        self.clean_browser_history_flag = value
        self.save_settings()

    def activate_selected_AC(self, force=False):
        if force or (self.next_cleaning_time and datetime.datetime.now() >= self.next_cleaning_time):
            print("Cleaning started...")
            self.previous_cleaning_time = datetime.datetime.now()
            self.save_settings()
            self.update_next_cleaning_time()
            self.save_settings()

            directories = [
                os.path.join(self.user_home_directory, 'Desktop'),
                os.path.join(self.user_home_directory, 'Downloads'),
                os.path.join(self.user_home_directory, 'Desktop'),
                os.path.join(self.user_home_directory, 'AppData', 'Local', 'Temp')
            ]

            if self.clean_empty_folders_flag:
                for directory in directories:
                    self.clean_empty_folders(directory)

            if self.clean_unused_files_flag:
                for directory in directories:
                    self.clean_unused_files(directory)

            if self.clean_duplicate_files_flag:
                for directory in directories:
                    self.clean_duplicate_files(directory)

            if self.clean_recycling_bin_flag:
                self.clean_recycling_bin()

            if self.clean_browser_history_flag:
                self.clean_browser_history()

    def clean_empty_folders(self, root_directory):
        try:
            for root, dirs, _ in os.walk(root_directory):
                for d in dirs:
                    folder_path = os.path.join(root, d)
                    if not os.listdir(folder_path):
                        print(f"Deleting empty folder: {folder_path}")
                        os.rmdir(folder_path)
        except Exception as e:
            self.db_handler.log_error(f"Error cleaning empty folders in {root_directory}: {str(e)}")


    def clean_unused_files(self, root_directory):
        try:
            threshold = datetime.datetime.now() - datetime.timedelta(days=90)
            for root, _, files in os.walk(root_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.getatime(file_path) < threshold.timestamp():
                        os.remove(file_path)
        except Exception as e:
            self.db_handler.log_error(f"Error cleaning unused files in {root_directory}: {str(e)}")

    def clean_duplicate_files(self, root_directory):
        try:
            seen_files = {}
            for root, _, files in os.walk(root_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_hash = self.hash_file(file_path)
                    if file_hash in seen_files:
                        os.remove(file_path)
                    else:
                        seen_files[file_hash] = file_path
        except Exception as e:
            self.db_handler.log_error(f"Error cleaning duplicate files in {root_directory}: {str(e)}")


    def hash_file(self, file_path):
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.db_handler.log_error(f"Error hashing file {file_path}: {str(e)}")
            return None

    def clean_recycling_bin(self):
        try:
            os.system('powershell.exe Clear-RecycleBin -Force')
        except Exception as e:
            self.db_handler.log_error(f"Error cleaning recycling bin: {str(e)}")

    def clean_browser_history(self):
        browsers = {
            "Chrome": os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "Default", "History"),
            "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles"),
            "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Windows", "WebCache", "WebCacheV01.dat")
        }

        for browser, path in browsers.items():
            if browser == "Firefox":
                if os.path.exists(path):
                    for profile in os.listdir(path):
                        profile_path = os.path.join(path, profile, "places.sqlite")
                        if os.path.exists(profile_path):
                            try:
                                os.remove(profile_path)
                            except Exception as e:
                                self.db_handler.log_error(f"Error cleaning browser history: {str(e)}")
            else:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        self.db_handler.log_error(f"Error cleaning browser history: {str(e)}")

    def run_auto_cleaning(self):
        if not self.is_running:
            self.activate_selected_AC()

    def schedule_cleaning(self, frequency):
        self.set_clean_frequency(frequency)
        schedule.every().day.at("05:00").do(self.run_auto_cleaning).tag('auto_clean')

        def scheduler_thread():
            while self.is_running:  # Keep checking if the scheduler is active
                schedule.run_pending()
                time.sleep(1)

        # If a thread is already running, don't start a new one
        if not hasattr(self, 'scheduler_thread') or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=scheduler_thread, daemon=True)
            self.scheduler_thread.start()

    def pause_operations(self):
        self.is_running = False
        schedule.clear('auto_clean')

    def resume_operations(self):
        if not self.is_running:
            self.is_running = True
            self.schedule_cleaning(self.frequency)
