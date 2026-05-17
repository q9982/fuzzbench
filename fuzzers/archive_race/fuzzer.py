# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Synthetic fuzzer for reproducing corpus archive races."""

import os
import threading
import time

from fuzzers.libfuzzer import fuzzer as libfuzzer_fuzzer

_RACING_CORPUS_FILES = 4
_STABLE_CORPUS_FILES = 2
_LARGE_ELEMENT_BYTES = 256 * 1024 * 1024
_SMALL_ELEMENT_BYTES = 32
_LARGE_WINDOW_SECONDS = 0.05
_SMALL_WINDOW_SECONDS = 0.005


def build():
    """Build benchmark with libFuzzer's toolchain."""
    libfuzzer_fuzzer.build()


def _write_stable_input(path):
    """Create a stable corpus element so cycle 1 is never completely empty."""
    with open(path, 'wb') as file_handle:
        file_handle.write(b'archive-race-stable-input\n')


def _race_archive_worker(path, ready_event, phase_offset):
    """Continuously resize one corpus file to race tar archiving."""
    time.sleep(phase_offset)
    while True:
        with open(path, 'wb') as file_handle:
            file_handle.truncate(_LARGE_ELEMENT_BYTES)
        ready_event.set()
        time.sleep(_LARGE_WINDOW_SECONDS)

        with open(path, 'r+b') as file_handle:
            file_handle.truncate(_SMALL_ELEMENT_BYTES)
            file_handle.write(b'archive-race-input\n')
        time.sleep(_SMALL_WINDOW_SECONDS)


def fuzz(input_corpus, output_corpus, target_binary):  # pylint: disable=unused-argument
    """Keep mutating the corpus so tarfile can observe a shrinking file."""
    if not os.path.exists(target_binary):
        raise FileNotFoundError(target_binary)

    os.makedirs(output_corpus, exist_ok=True)

    for index in range(_STABLE_CORPUS_FILES):
        file_path = os.path.join(output_corpus, f'stable-input-{index}')
        _write_stable_input(file_path)

    ready_events = []
    for index in range(_RACING_CORPUS_FILES):
        ready_event = threading.Event()
        ready_events.append(ready_event)
        file_path = os.path.join(output_corpus, f'racing-input-{index}')
        worker = threading.Thread(target=_race_archive_worker,
                                  args=(file_path, ready_event,
                                        index * _SMALL_WINDOW_SECONDS),
                                  daemon=True)
        worker.start()

    for ready_event in ready_events:
        ready_event.wait()

    while True:
        time.sleep(60)
