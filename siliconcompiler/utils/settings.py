import json
import os
import logging
import threading

import os.path

from typing import Optional

from fasteners import InterProcessLock

from siliconcompiler import sc_open


class SettingsManager:
    """
    A class to manage user settings stored in a JSON file.
    Supports categories, robust error handling for malformed files,
    and simple get/set operations.

    An optional read-only, administrator-managed *system* settings file can be
    layered underneath the user file. System settings act as defaults that the
    user may override, except for values the system marks with *system
    priority*, which take precedence over the user's own value. This provides
    both soft defaults and administrator-enforced values from a single file
    (see ``system_filepath``).

    In the system file, a value is given system priority by co-locating a flag
    with it. Instead of a bare value, the setting is written as an object with a
    ``"system_priority"`` flag (and, optionally, a ``"value"``)::

        {
            "record": {
                "region": {"value": "us-east-1", "system_priority": true}
            },
            "scheduler-slurm": {
                "sharedpaths": ["/nfs/tools"]
            }
        }

    Here ``region`` is a system-priority value that the user cannot override
    while ``sharedpaths`` is a plain, overridable default. The priority flag is
    only interpreted in the system file; a value written this way in a user file
    is treated as an ordinary (dictionary) value, so existing user files are
    unaffected.
    """

    #: Key that marks a system value as taking priority over the user value.
    __PRIORITY_FLAG = "system_priority"
    #: Key that carries the actual value alongside a priority flag.
    __VALUE_FLAG = "value"

    def __init__(self, filepath: str, logger: logging.Logger, timeout: float = 1.0,
                 system_filepath: Optional[str] = None):
        """
        Initialize the settings manager.

        Args:
            filepath (str): The path to the JSON file where user settings are
                stored. If None, settings are kept in memory only.
            logger (logging.Logger): Logger for logging errors and information.
            timeout (float): Timeout in seconds for acquiring the file lock.
            system_filepath (str): Optional path to a read-only, system-wide
                settings file providing administrator-managed defaults and
                system-priority (non-overridable) values. If None, no system
                layer is applied.
        """
        self.__filepath = filepath
        if self.__filepath is not None:
            self.__lock = InterProcessLock(self.__filepath + ".lock")
        self.__settings_lock = threading.Lock()
        self.__timeout = timeout
        self.__logger = logger.getChild("settings")
        self.__settings = {}

        # System layer state: resolved (unwrapped) values plus the set of
        # system-priority keys per category.
        self.__system_filepath = system_filepath
        self.__system_settings = {}
        self.__priority = {}

        self._load()
        self._load_system()

    def _load(self):
        """
        Internal method to load settings from disk.
        It handles missing files and malformed JSON gracefully.
        """
        if self.__filepath is None or not os.path.exists(self.__filepath):
            self.__settings = {}
            return

        with self.__settings_lock:
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

    def _load_system(self):
        """
        Internal method to load the read-only system settings file, if any.

        Unlike the user file, the system file is never locked (it is
        administrator-managed and typically lives in a location such as
        ``/etc`` where regular users cannot create the sibling lock file) and is
        never written to. Any failure to read it is logged and treated as if no
        system file were present, so it can never prevent startup.

        Inline priority flags are unwrapped here into ``__system_settings``
        (bare values) and ``__priority`` (the set of system-priority keys per
        category).
        """
        self.__system_settings = {}
        self.__priority = {}

        if self.__system_filepath is None or not os.path.exists(self.__system_filepath):
            return

        try:
            with sc_open(self.__system_filepath, encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.__logger.error(f"System settings file {self.__system_filepath} is malformed. "
                                "Ignoring system settings.")
            return
        except Exception as e:
            self.__logger.error(f"Unexpected error loading system settings: {e}")
            return

        if not isinstance(data, dict):
            self.__logger.warning(f"System settings file {self.__system_filepath} did not contain "
                                  "a JSON object. Ignoring system settings.")
            return

        self._unwrap_system(data)

    def _is_priority_wrapper(self, value) -> bool:
        """
        Return True if a raw system value is a co-located priority wrapper, i.e.
        a JSON object carrying a ``system_priority`` flag.
        """
        return isinstance(value, dict) and self.__PRIORITY_FLAG in value

    def _unwrap_system(self, data: dict):
        """
        Split raw system data into resolved values and system-priority keys.

        Each setting is either a bare value (a plain, overridable default) or a
        priority wrapper (an object with a ``system_priority`` flag and optional
        ``value``). System-priority keys are recorded per category; a wrapper
        without a ``value`` gives priority to "unset", forcing callers to fall
        back to their default.
        """
        for category, entries in data.items():
            if not isinstance(entries, dict):
                self.__logger.warning(f"System settings category '{category}' is not a JSON "
                                      "object. Ignoring.")
                continue

            values = {}
            priority = set()
            for key, raw in entries.items():
                if self._is_priority_wrapper(raw):
                    if raw.get(self.__PRIORITY_FLAG):
                        priority.add(key)
                    if self.__VALUE_FLAG in raw:
                        values[key] = raw[self.__VALUE_FLAG]
                else:
                    values[key] = raw

            self.__system_settings[category] = values
            if priority:
                self.__priority[category] = priority

    def _has_priority(self, category: str, key: str) -> bool:
        """
        Return True if the given category/key is a system-priority value and
        therefore not user-overridable.
        """
        return key in self.__priority.get(category, ())

    def save(self):
        """
        Save the current settings to the disk in JSON format.
        """
        if self.__filepath is None:
            return

        try:
            # Ensure directory exists
            directory = os.path.dirname(self.__filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with self.__settings_lock:
                with self.__lock:
                    with open(self.__filepath, 'w', encoding='utf-8') as f:
                        json.dump(self.__settings, f, indent=4)
        except Exception as e:
            self.__logger.error(f"Failed to save settings to {self.__filepath}: {e}")
            raise

    def set(self, category: str, key: str, value, keep: bool = False):
        """
        Set a specific setting within a category.

        Args:
            category (str): The group name (e.g., 'showtools', 'options').
            key (str): The specific setting name.
            value: The value to store (must be JSON serializable).
            keep (bool): If True, do not overwrite existing value.
        """
        if self._has_priority(category, key):
            self.__logger.warning(f"Setting '{category}.{key}' has system priority and cannot be "
                                  "overridden. Ignoring.")
            return

        with self.__settings_lock:
            if category not in self.__settings:
                self.__settings[category] = {}

            if keep and key in self.__settings[category]:
                return
            self.__settings[category][key] = value

    def get(self, category: str, key: str, default=None):
        """
        Retrieve a setting.

        Resolution order:

        1. If the key has system priority, the system value is returned (or
           ``default`` if the system file does not define it); the user value is
           ignored.
        2. Otherwise, the user value is returned if present.
        3. Otherwise, the (overridable) system default is returned if present.
        4. Otherwise, ``default`` is returned.

        Args:
            category (str): The group name.
            key (str): The specific setting name.
            default: The value to return if the category or key is missing.

        Returns:
            The stored value or the default.
        """
        with self.__settings_lock:
            if self._has_priority(category, key):
                return self.__system_settings.get(category, {}).get(key, default)

            if category in self.__settings and key in self.__settings[category]:
                return self.__settings[category][key]

            return self.__system_settings.get(category, {}).get(key, default)

    def get_category(self, category: str):
        """
        Retrieve all settings for a specific category, merging system defaults
        with user overrides.

        System values provide the baseline, user values override them, and
        system-priority keys are forced back to the system value (or removed if
        the system file does not define them). Returns an empty dict if the
        category exists in neither layer.
        """
        with self.__settings_lock:
            return self._merge_category(category)

    def _merge_category(self, category: str):
        """
        Build the effective view of a category. Assumes ``__settings_lock`` is
        held by the caller.
        """
        system_cat = self.__system_settings.get(category, {})

        merged = dict(system_cat)
        merged.update(self.__settings.get(category, {}))

        # Re-apply system-priority values so user values cannot leak through.
        for priority_key in self.__priority.get(category, ()):
            if priority_key in system_cat:
                merged[priority_key] = system_cat[priority_key]
            else:
                merged.pop(priority_key, None)

        return merged

    def delete(self, category: str, key: Optional[str] = None):
        """
        Remove a user setting.

        System-priority settings are administrator-managed and cannot be
        removed; such requests are ignored with a warning. Note that deletion
        only affects the user layer; system defaults remain in effect.
        """
        if key is not None and self._has_priority(category, key):
            self.__logger.warning(f"Setting '{category}.{key}' has system priority and cannot be "
                                  "removed. Ignoring.")
            return

        with self.__settings_lock:
            if category in self.__settings:
                if key:
                    if key in self.__settings[category]:
                        del self.__settings[category][key]
                        # Clean up empty categories
                        if not self.__settings[category]:
                            del self.__settings[category]
                else:
                    del self.__settings[category]
