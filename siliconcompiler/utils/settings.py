import json
import os
import logging

import os.path

from typing import Optional

from fasteners import InterProcessLock

from siliconcompiler import sc_open


class SettingsManager:
    """
    A class to manage user settings stored in a JSON file.
    Supports categories, robust error handling for malformed files,
    and simple get/set operations.
    """

    def __init__(self, filepath: str, logger: logging.Logger, timeout: float = 1.0):
        """
        Initialize the settings manager.

        Args:
            filepath (str): The path to the JSON file where settings are stored.
        """
        self.__filepath = filepath
        self.__lock = InterProcessLock(self.__filepath + ".lock")
        self.__timeout = timeout
        self.__logger = logger.getChild("settings")
        self.__settings = {}
        self._load()

    def _load(self):
        """
        Internal method to load settings from disk.
        It handles missing files and malformed JSON gracefully.
        """
        if not os.path.exists(self.__filepath):
            self.__settings = {}
            return

        try:
            if self.__lock.acquire(timeout=self.__timeout):
                try:
                    with sc_open(self.__filepath, encoding='utf-8') as f:
                        data = json.load(f)
                finally:
                    self.__lock.release()
            else:
                self.__logger.error(f"Timeout acquiring lock for {self.__filepath}. "
                                    "Starting with empty settings.")
                data = {}

            # Ensure the loaded data is actually a dictionary
            if isinstance(data, dict):
                self.__settings = data
            else:
                # If valid JSON but not a dict (e.g. a list), reset to empty
                self.__logger.warning(f"File {self.__filepath} did not contain a JSON object. "
                                      "Resetting.")
                self.__settings = {}

        except json.JSONDecodeError:
            self.__logger.error(f"File {self.__filepath} is malformed. "
                                "Starting with empty settings.")
            self.__settings = {}
        except Exception as e:
            # Catch-all for permission errors, etc., to ensure __init__ doesn't crash
            self.__logger.error(f"Unexpected error loading settings: {e}")
            self.__settings = {}

    def save(self):
        """
        Save the current settings to the disk in JSON format.
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(self.__filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with self.__lock:
                with open(self.__filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.__settings, f, indent=4)
        except Exception as e:
            self.__logger.error(f"Failed to save settings to {self.__filepath}: {e}")
            raise e

    def set(self, category: str, key: str, value):
        """
        Set a specific setting within a category.

        Args:
            category (str): The group name (e.g., 'showtools', 'options').
            key (str): The specific setting name.
            value: The value to store (must be JSON serializable).
        """
        if category not in self.__settings:
            self.__settings[category] = {}

        self.__settings[category][key] = value

    def get(self, category: str, key: str, default=None):
        """
        Retrieve a setting.

        Args:
            category (str): The group name.
            key (str): The specific setting name.
            default: The value to return if the category or key is missing.

        Returns:
            The stored value or the default.
        """
        if category not in self.__settings:
            return default

        return self.__settings[category].get(key, default)

    def get_category(self, category: str):
        """
        Retrieve all settings for a specific category.
        Returns an empty dict if category does not exist.
        """
        return self.__settings.get(category, {})

    def delete(self, category: str, key: Optional[str] = None):
        """
        Remove a setting.
        """
        if category in self.__settings:
            if key:
                if key in self.__settings[category]:
                    del self.__settings[category][key]
                    # Clean up empty categories
                    if not self.__settings[category]:
                        del self.__settings[category]
            else:
                del self.__settings[category]
