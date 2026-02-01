"""
Thread-safe logging handlers для многопоточного Gunicorn (gthread/gevent).

Проблема: стандартный logging.StreamHandler может вызвать 
RuntimeError: reentrant call inside <_io.BufferedWriter name='<stderr>'>
при одновременной записи из нескольких потоков.

Решение: использовать QueueHandler + QueueListener для асинхронного логирования,
или ThreadSafeStreamHandler с дополнительным lock'ом.
"""
import logging
import logging.handlers
import sys
import threading
import queue
import atexit
from typing import Optional


class ThreadSafeStreamHandler(logging.StreamHandler):
    """
    Thread-safe версия StreamHandler.
    
    Использует RLock для предотвращения reentrant ошибок при
    одновременной записи из нескольких потоков.
    """
    
    _write_lock = threading.RLock()
    
    def emit(self, record):
        """
        Emit a record с thread-safe write.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # Используем RLock для thread-safe записи
            with self._write_lock:
                try:
                    stream.write(msg + self.terminator)
                    self.flush()
                except RecursionError:
                    raise
                except Exception:
                    self.handleError(record)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
    
    def handleError(self, record):
        """
        Handle error без рекурсии.
        """
        # Подавляем ошибки чтобы не вызвать рекурсию
        pass


class NonBlockingStreamHandler(logging.Handler):
    """
    Неблокирующий handler через очередь.
    
    Записывает логи в отдельном потоке, что полностью исключает
    reentrant проблемы и не блокирует основной поток.
    """
    
    _instances = []  # Для cleanup при shutdown
    
    def __init__(self, stream=None, level=logging.NOTSET):
        super().__init__(level)
        self.stream = stream or sys.stderr
        self._queue = queue.Queue(maxsize=10000)
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        NonBlockingStreamHandler._instances.append(self)
    
    def emit(self, record):
        """
        Put record в очередь (non-blocking).
        """
        try:
            # Форматируем сразу чтобы не было проблем с record в другом потоке
            msg = self.format(record)
            # Non-blocking put - если очередь полная, пропускаем
            try:
                self._queue.put_nowait(msg)
            except queue.Full:
                pass  # Пропускаем если очередь переполнена
        except Exception:
            pass  # Никогда не падаем
    
    def _worker(self):
        """
        Worker thread для записи логов.
        """
        while not self._shutdown.is_set():
            try:
                msg = self._queue.get(timeout=0.5)
                if msg is None:
                    break
                try:
                    self.stream.write(msg + '\n')
                    self.stream.flush()
                except Exception:
                    pass
            except queue.Empty:
                continue
            except Exception:
                pass
    
    def close(self):
        """
        Закрыть handler и дождаться завершения worker.
        """
        self._shutdown.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        super().close()
    
    @classmethod
    def shutdown_all(cls):
        """
        Закрыть все instances при shutdown приложения.
        """
        for handler in cls._instances:
            try:
                handler.close()
            except Exception:
                pass
        cls._instances.clear()


# Регистрируем cleanup при выходе
atexit.register(NonBlockingStreamHandler.shutdown_all)


# QueueHandler + QueueListener подход (рекомендуется Python 3.2+)
_queue_listener: Optional[logging.handlers.QueueListener] = None
_log_queue: Optional[queue.Queue] = None


def setup_queue_logging():
    """
    Настроить Queue-based логирование для thread-safety.
    
    Возвращает QueueHandler который нужно добавить в LOGGING config.
    """
    global _queue_listener, _log_queue
    
    if _log_queue is not None:
        return logging.handlers.QueueHandler(_log_queue)
    
    _log_queue = queue.Queue(-1)  # Неограниченная очередь
    
    # Создаём реальные handlers которые будут писать в отдельном потоке
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(
        '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
        style='{'
    ))
    
    # QueueListener обрабатывает записи из очереди в отдельном потоке
    _queue_listener = logging.handlers.QueueListener(
        _log_queue,
        console_handler,
        respect_handler_level=True
    )
    _queue_listener.start()
    
    # Регистрируем остановку при выходе
    atexit.register(_queue_listener.stop)
    
    return logging.handlers.QueueHandler(_log_queue)
