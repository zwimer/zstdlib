# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from tempfile import TemporaryDirectory, NamedTemporaryFile as NTF
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import multiprocessing as mp
from pathlib import Path
from typing import Any
import unittest
import time
import os

from zstdlib.ip_lock import LockPathInUseError, NotAcquiredError, AbstractIPLock, LockHungError
from zstdlib import GlobalIPLock as GIPL, RIPLock, IPLock, normpath

DELAY = 0.25  # Lower is faster but less accurate


@contextmanager
def mk_gipl() -> Iterator[GIPL]:
    with NTF(delete_on_close=False) as f:
        f.close()
        yield GIPL.new(Path(f.name))


@contextmanager
def mk_lock[T: (IPLock, RIPLock)](lock_t: type[T]) -> Iterator[T]:
    assert lock_t in (IPLock, RIPLock)
    with NTF(delete_on_close=False) as f:
        f.close()
        yield lock_t(Path(f.name))


@contextmanager
def enter(lock: AbstractIPLock, timeout: int | float = 10) -> Iterator[None]:
    assert 0 <= timeout <= 10
    old = lock.acquired
    if not lock.acquire(timeout_per=timeout):
        raise RuntimeError("Failed to acquire")
    try:
        yield
    finally:
        lock.release()
    if old != lock.acquired:
        raise RuntimeError("Different state")


class IPLog:  # Not thread-safe

    def __init__(self) -> None:
        self._q: mp.Queue[tuple[float, int, str]] = mp.Queue()
        self._q.put((0, 0, ""))
        self._main: int = os.getpid()
        self._done: bool = False

    def __call__(self, s: str, pid: int | None = None) -> None:
        main = os.getpid() == self._main
        assert main == (pid is None)
        if main:
            pid = 1
        assert not self._done and isinstance(pid, int) and (main or pid > 1)
        self._q.put((time.monotonic(), pid, s))

    def read(self) -> list[str]:
        assert not self._done
        self._done = True
        self._q.put((-1, 0, ""))
        contents: list[tuple[float, int, str]] = []
        while not contents or contents[-1][0] != -1:
            contents.append(self._q.get())
        contents = contents[1:-1]
        if not contents:
            return []
        pids = list({i[1] for i in contents})
        rv = sorted(f"{i}|PID-{pids.index(j)+1}: {k}" for i, j, k in contents)
        return [i.split("|", 1)[1] for i in rv]


# For remote testing


class RemoteProc:

    type Logger = Callable[[str], None]

    def __init__(self, fn: Callable[[Logger, Path], None], log: IPLog, path: Path, *, pid: int) -> None:
        if pid < 2:
            raise ValueError("Bad pid")
        self._p = mp.get_context("spawn").Process(target=self._wrapper)
        self._func = fn
        self._pid = pid
        self._done = False
        self._path = path
        self._log = log

    def start(self) -> None:
        self._p.start()

    def die(self, timeout: int) -> None:
        assert isinstance(timeout, int) and 0 <= timeout <= 10
        self._p.join(timeout)
        if self._p.is_alive():
            self._log("Alive")
            self._p.kill()

    def _wrapper(self) -> None:

        def log(s: str) -> None:
            self._log(s, pid=self._pid)

        log("START")
        try:
            self._func(log, self._path)
            log("FIN")
        except Exception as e:  # noqa: BLE001
            log(f"{e.__class__.__name__}: {e.args}")


def gipl_p1(log: RemoteProc.Logger, path: Path) -> None:
    with GIPL.new(path) as lock:
        log("Locked")
        time.sleep(DELAY)
        with lock:
            log("Double locked; sleeping")
            time.sleep(DELAY)
            log("Awake")


# Unit tests


class TestGlobalProcessLock(unittest.TestCase):

    def test_bad_usage(self) -> None:
        # Path
        bad = Path("a/b/../c")
        norm = normpath(bad)
        fixed = norm.absolute()
        assert bad != norm != fixed and fixed == Path.cwd() / norm
        with self.assertRaises(ValueError):
            GIPL(bad)
        self.assertEqual(GIPL.new(bad).path, fixed)
        self.assertEqual(GIPL.new(str(bad)).path, fixed)
        with self.assertRaises(TypeError):
            GIPL(str(fixed))  # type: ignore[arg-type]
        # File
        with TemporaryDirectory() as _td:
            td = GIPL.normalize(_td, check=False)
            with self.assertRaises(FileExistsError):
                _ = GIPL(td)
            no_exist = td / "no_exist"
            self.assertIs(GIPL(no_exist), GIPL.new(no_exist))
            norm = td / "normal"
            norm.touch()
            self.assertIs(GIPL(norm), GIPL.new(norm))
            symlink = td / "symlink"
            symlink.symlink_to(norm)
            assert symlink.resolve() == norm
            with self.assertRaises(FileExistsError):  # test for Path, easier here b/c temp dir
                _ = GIPL(symlink)
            with self.assertRaises(FileExistsError):
                GIPL.new(symlink)
            hardlink = td / "hardlink"
            hardlink.hardlink_to(norm)
            with self.assertRaises(FileExistsError):
                GIPL(hardlink)
            with self.assertRaises(FileExistsError):
                GIPL(hardlink)
        # Timeout
        with mk_gipl() as lock:
            self.assertFalse(lock.acquired)
            with self.assertRaises(TypeError):
                lock.acquire(timeout_per="q")  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                lock.acquire(timeout_per=-1)
            with self.assertRaises(ValueError):
                lock.acquire(blocking=False, timeout_per=1)
            self.assertFalse(lock.acquired)
            self.assertTrue(lock.acquire(timeout_per=1))
            lock.release()
            self.assertFalse(lock.acquired)
            self.assertTrue(lock.acquire(timeout_per=1.0))
            lock.release()
            self.assertFalse(lock.acquired)

    def test_sole_owner(self) -> None:
        with mk_gipl() as lock:
            self.assertFalse(lock.acquired)
            # Can acquire existing file
            self.assertTrue(lock.acquire(timeout_per=0))
            self.assertTrue(lock.acquired)
            # Re-acquisition, count == 2
            self.assertTrue(lock.acquire(timeout_per=0))
            self.assertTrue(lock.acquired)
            # Release 1/2
            lock.release()
            self.assertTrue(lock.acquired)
            # Release 2/2
            lock.release()
            self.assertFalse(lock.acquired)
            # Release 3/2
            with self.assertRaises(NotAcquiredError):
                lock.release()
            self.assertFalse(lock.acquired)
            # CM exit, lock file removed by NTF
        # Fresh acquire on non-existing file
        lock.acquire(timeout_per=0)
        lock.release()

    def test_global(self) -> None:
        with mk_gipl() as lock:
            other = GIPL(lock.path)
            self.assertFalse(lock.acquired or other.acquired)
            self.assertTrue(lock.acquire(timeout_per=1))
            self.assertTrue(lock.acquired and other.acquired)
            self.assertTrue(lock.acquire(timeout_per=1))
            other.release()
            self.assertTrue(lock.acquired and other.acquired)
            other.release()
            self.assertFalse(lock.acquired or other.acquired)

    def test_ipc(self) -> None:
        log = IPLog()
        with mk_gipl() as lock:
            p = RemoteProc(gipl_p1, log, lock.path, pid=2)
            with enter(lock):
                log("Starting child")
                p.start()
                time.sleep(DELAY)
                log("Releasing")
                lock.release()
                time.sleep(DELAY)
                log("Reclaiming")
                lock.acquire(timeout_per=1)
                log("Got")
        expected: list[str] = [
            "PID-1: Starting child",
            "PID-2: START",
            "PID-1: Releasing",
            "PID-2: Locked",
            "PID-1: Reclaiming",
            "PID-2: Double locked; sleeping",
            "PID-2: Awake",
            "PID-2: FIN",
            "PID-1: Got",
        ]
        self.assertEqual(log.read(), expected)


class TestIPLocks(unittest.TestCase):

    def test_locks(self) -> None:
        # Test using a basic IPLock b/c more likely to err if we do something dumb
        # We already trust GlobalProcessLock, threading.Lock, and threading.RLock
        # so instead of spinning up threads and processes, just verify their states
        with mk_lock(IPLock) as lock:
            lock2 = IPLock(lock.path)
            self.assertIsNot(lock, lock2)
            self.assertEqual(lock.path, lock2.path)
            # pylint: disable=protected-access
            self.assertIs(lock._gipl, lock2._gipl)
            self.assertFalse(lock._gipl.acquired)
            with enter(lock):

                def chk() -> None:
                    self.assertTrue(lock._gipl.acquired)
                    self.assertTrue(lock.acquired)
                    self.assertTrue(lock._sync_lock.locked())
                    self.assertFalse(lock2.acquired)
                    self.assertTrue(lock2._sync_lock.locked())

                chk()
                self.assertFalse(lock2.acquire(timeout_per=2))
                chk()
            self.assertFalse(lock._gipl.acquired or lock2._gipl.acquired)
            self.assertFalse(lock._sync_lock.locked())
            self.assertFalse(lock2._sync_lock.locked())
            # pylint: enable=protected-access
        # Test releasing when we don't have
        self.assertFalse(lock.acquired)
        with self.assertRaises(NotAcquiredError):
            lock.release()
        # pylint: disable=protected-access
        lock._rc += 1
        with self.assertRaises(RuntimeError):
            lock.release()
        lock._rc += 1
        lock._sync_lock.acquire()
        self.assertFalse(lock._gipl.acquired)
        # pylint: enable=protected-access
        with self.assertRaises(OSError):
            lock.release()

        # Fake GIPL cannot acquire test
        class FakeGIPL:
            def acquire(self, *_: Any, **__: Any) -> bool:
                return False

        with mk_lock(IPLock) as lock:
            # pylint: disable=protected-access
            old = lock._gipl
            lock._gipl = FakeGIPL()  # type: ignore[assignment ,misc]
            self.assertFalse(lock.acquire(timeout_per=3))
            lock._gipl = old  # type: ignore[misc]
            # pylint: enable=protected-access

    def test_lock_types(self) -> None:
        # pylint: disable=protected-access
        self.assertFalse(IPLock._cls_reentrant)
        self.assertTrue(RIPLock._cls_reentrant)
        with mk_lock(IPLock) as lock:
            self.assertFalse(lock._instance_reentrant)
        del lock
        with mk_lock(RIPLock) as rlock:
            self.assertTrue(rlock._instance_reentrant)
        del rlock

        # pylint: enable=protected-access
        with mk_lock(IPLock) as lock, enter(lock):
            self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquire(timeout_per=2))
            self.assertTrue(lock.acquired)
        self.assertFalse(lock.acquired)
        del lock
        with mk_lock(RIPLock) as rlock, enter(rlock), enter(rlock):
            self.assertTrue(rlock.acquired)
        self.assertFalse(rlock.acquired)
        del rlock

        with mk_lock(IPLock) as lock, self.assertRaises(LockPathInUseError):
            _ = RIPLock(lock.path)
        del lock
        with mk_lock(RIPLock) as rlock, self.assertRaises(LockPathInUseError):
            _ = IPLock(rlock.path)
        del rlock

    def test_lock_hung(self) -> None:
        with mk_lock(IPLock) as lock, enter(lock), self.assertRaises(LockHungError):
            _ = lock.acquire()


if __name__ == "__main__":
    unittest.main()
