# -*- coding: utf-8 -*-

# Copyright 2020 Google LLC
# Modifications copyright 2021 Luke Hsiao
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import queue

import sounddevice as sd

RATE = 16000
CHUNK = int(RATE / 10)  # ~100ms


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self):
        self.rate = RATE
        self.chunk = CHUNK
        # Create a thread-safe buffer of audio data
        self.buff = queue.SimpleQueue()

        self.closed = True

    def __enter__(self):
        self.stream = sd.RawInputStream(
            samplerate=RATE,
            #  blocksize=CHUNK,
            channels=1,
            dtype="int16",
            latency="low",
            callback=self.audio_callback,
        )
        self.stream.start()
        self.closed = False

        return self

    def audio_callback(self, indata, frames, time, status):
        """Continuously collect data from the audio stream, into the buffer."""
        if status:
            print(f"[INFO] {status}", file=sys.stderr)

        self.buff.put(bytes(indata))

        return None

    def __exit__(self, type=None, value=None, traceback=None):
        self.stream.stop()
        self.stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self.buff.put(None)

    def exit(self):
        self.__exit__()

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self.buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self.buff.get_nowait()
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)
