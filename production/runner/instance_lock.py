"""
Instance Lock Manager

Prevents multiple bot instances from running on the same account.
Uses file-based locks with PID tracking and stale lock detection.
"""

import os
import json
import time
import socket
import atexit
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class InstanceLock:
    """
    File-based lock manager for trading bot instances.

    Features:
    - Creates lock file with PID, timestamp, hostname
    - Automatic release on exit
    - Stale lock detection (configurable timeout)
    - Heartbeat updates for long-running instances
    """

    def __init__(self, locks_dir: str = None, stale_timeout_hours: float = 1.0):
        """
        Initialize lock manager.

        Args:
            locks_dir: Directory for lock files (default: production/locks/)
            stale_timeout_hours: Hours before a lock is considered stale
        """
        if locks_dir is None:
            # Default to production/locks/ relative to this file
            base_dir = Path(__file__).parent.parent
            locks_dir = base_dir / "locks"

        self.locks_dir = Path(locks_dir)
        self.locks_dir.mkdir(parents=True, exist_ok=True)

        self.stale_timeout_seconds = stale_timeout_hours * 3600
        self.current_lock_path: Optional[Path] = None
        self.account_name: Optional[str] = None

        # Register cleanup on exit
        atexit.register(self.release)

    def _get_lock_path(self, account_name: str) -> Path:
        """Get lock file path for account."""
        return self.locks_dir / f"{account_name}.lock"

    def _create_lock_data(self) -> Dict[str, Any]:
        """Create lock file data."""
        return {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "timestamp": datetime.now().isoformat(),
            "heartbeat": datetime.now().isoformat()
        }

    def _read_lock(self, lock_path: Path) -> Optional[Dict[str, Any]]:
        """Read lock file data."""
        try:
            if lock_path.exists():
                with open(lock_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _is_lock_stale(self, lock_data: Dict[str, Any]) -> bool:
        """Check if lock is stale based on heartbeat."""
        try:
            heartbeat = datetime.fromisoformat(lock_data.get("heartbeat", lock_data["timestamp"]))
            age_seconds = (datetime.now() - heartbeat).total_seconds()
            return age_seconds > self.stale_timeout_seconds
        except (KeyError, ValueError):
            return True  # Invalid lock data is considered stale

    def _is_process_running(self, pid: int) -> bool:
        """Check if process with PID is still running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def is_locked(self, account_name: str) -> bool:
        """
        Check if account is currently locked.

        Args:
            account_name: Account to check

        Returns:
            True if locked by another active instance
        """
        lock_path = self._get_lock_path(account_name)
        lock_data = self._read_lock(lock_path)

        if lock_data is None:
            return False

        # Check if stale
        if self._is_lock_stale(lock_data):
            return False

        # Check if process is still running
        pid = lock_data.get("pid")
        if pid and not self._is_process_running(pid):
            return False

        return True

    def get_lock_info(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        Get lock information for account.

        Args:
            account_name: Account to check

        Returns:
            Lock data dict or None if not locked
        """
        if not self.is_locked(account_name):
            return None

        lock_path = self._get_lock_path(account_name)
        return self._read_lock(lock_path)

    def acquire(self, account_name: str, force: bool = False) -> bool:
        """
        Acquire lock for account.

        Args:
            account_name: Account to lock
            force: Force acquire even if locked (use with caution)

        Returns:
            True if lock acquired, False if already locked
        """
        lock_path = self._get_lock_path(account_name)

        # Check if already locked
        if not force and self.is_locked(account_name):
            lock_info = self._read_lock(lock_path)
            pid = lock_info.get("pid", "unknown") if lock_info else "unknown"
            hostname = lock_info.get("hostname", "unknown") if lock_info else "unknown"
            print(f"Account '{account_name}' is locked by PID {pid} on {hostname}")
            return False

        # Create lock
        lock_data = self._create_lock_data()

        try:
            with open(lock_path, 'w') as f:
                json.dump(lock_data, f, indent=2)

            self.current_lock_path = lock_path
            self.account_name = account_name

            print(f"Lock acquired for account '{account_name}' (PID: {os.getpid()})")
            return True

        except IOError as e:
            print(f"Failed to acquire lock: {e}")
            return False

    def release(self):
        """Release current lock."""
        if self.current_lock_path and self.current_lock_path.exists():
            try:
                # Verify we own the lock
                lock_data = self._read_lock(self.current_lock_path)
                if lock_data and lock_data.get("pid") == os.getpid():
                    self.current_lock_path.unlink()
                    print(f"Lock released for account '{self.account_name}'")
            except IOError as e:
                print(f"Failed to release lock: {e}")
            finally:
                self.current_lock_path = None
                self.account_name = None

    def update_heartbeat(self):
        """Update heartbeat timestamp for current lock."""
        if self.current_lock_path and self.current_lock_path.exists():
            lock_data = self._read_lock(self.current_lock_path)
            if lock_data and lock_data.get("pid") == os.getpid():
                lock_data["heartbeat"] = datetime.now().isoformat()
                try:
                    with open(self.current_lock_path, 'w') as f:
                        json.dump(lock_data, f, indent=2)
                except IOError:
                    pass

    def list_locks(self) -> Dict[str, Dict[str, Any]]:
        """
        List all locks and their status.

        Returns:
            Dict mapping account names to lock info (or None if not locked)
        """
        locks = {}

        for lock_file in self.locks_dir.glob("*.lock"):
            account_name = lock_file.stem
            if self.is_locked(account_name):
                locks[account_name] = self._read_lock(lock_file)
            else:
                # Clean up stale lock
                try:
                    lock_file.unlink()
                except IOError:
                    pass

        return locks

    def cleanup_stale_locks(self) -> int:
        """
        Remove all stale lock files.

        Returns:
            Number of locks cleaned up
        """
        cleaned = 0

        for lock_file in self.locks_dir.glob("*.lock"):
            lock_data = self._read_lock(lock_file)
            if lock_data:
                if self._is_lock_stale(lock_data):
                    try:
                        lock_file.unlink()
                        cleaned += 1
                        print(f"Cleaned stale lock: {lock_file.name}")
                    except IOError:
                        pass
                elif not self._is_process_running(lock_data.get("pid", 0)):
                    try:
                        lock_file.unlink()
                        cleaned += 1
                        print(f"Cleaned orphaned lock: {lock_file.name}")
                    except IOError:
                        pass

        return cleaned


# Global instance for convenience
_lock_manager: Optional[InstanceLock] = None


def get_lock_manager() -> InstanceLock:
    """Get or create global lock manager instance."""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = InstanceLock()
    return _lock_manager


def acquire_lock(account_name: str, force: bool = False) -> bool:
    """Convenience function to acquire lock."""
    return get_lock_manager().acquire(account_name, force)


def release_lock():
    """Convenience function to release lock."""
    get_lock_manager().release()


def is_locked(account_name: str) -> bool:
    """Convenience function to check if account is locked."""
    return get_lock_manager().is_locked(account_name)


def list_locks() -> Dict[str, Dict[str, Any]]:
    """Convenience function to list all locks."""
    return get_lock_manager().list_locks()
