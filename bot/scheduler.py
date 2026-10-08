# -*- coding: utf-8 -*-
import logging
import threading
import time

from bot.funnel import process_due

log = logging.getLogger(__name__)


class JobLoop(object):
    def __init__(self, bot, interval=8):
        self.bot = bot
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, name="funnel-jobs")
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        while not self._stop.is_set():
            try:
                process_due(self.bot)
            except Exception:
                log.exception("Scheduler tick failed")
            time.sleep(self.interval)
