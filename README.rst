Live Translated Captions
========================

This is a simple CLI tool that uses Google's `Media Translation API`_ to do
real-time translation from speech to text. In particular this writes output to
a text file which can then be used in a text source as captions in `Open
Broadcaster Software (OBS)`_.


Installation
------------

Dependencies
^^^^^^^^^^^^

1. Setup a Google Cloud account following the instructions in
   https://cloud.google.com/translate/media/docs/streaming.

Be sure to save your ``key.json`` securely.

2. Install `poetry`_.

3. Install system dependencies for pyaudio.
   ::
    $ sudo apt install portaudio19-dev

4. Install this package.
   ::
    $ git clone https://github.com/lukehsiao/live-translation.git
    $ cd live_translation
    $ poetry install

Usage
-----

From inside a ``poetry shell``, you can access the script directly.
::
    Usage: translate [OPTIONS]

      Translate speech in one language to text in another using Google's Media
      Translation API.

      Press '`' to swap between source and target languages during runtime.

    Options:
      -f, --source-lang TEXT          The speaker's language  [default: en-US]
      -t, --target-lang TEXT          The language to translate captions to
                                      [default: es-MX]

      -o, --outfile TEXT              What to name the caption file.  [default:
                                      captions.txt]

      -w, --width INTEGER             The maximum length of lines in the caption
                                      file.  [default: 55]

      --help                          Show this message and exit.

This UI could use some more polish, but for a weekend project it seems to work
well. The purpose of this tool is to provide an interface for display real-time
translated captions in OBS. To do so, ``translate`` accepts a source and target
language, and outputs the streaming translation to a simple text file in a
specific format. The languages currently supported by the Media Translation API
are: English (US) (``en-US``), French (``fr-FR``), German (``de-DE``), Hindi
(``hi-IN``), Italian (``it-IT``), Portuguese (Brazil) (``pt-BR``), Portuguese
(Portugal) (``pt-PT``), Russian (``ru-RU``), Spanish (Mexico) (``es-MX``),
Spanish (Spain) (``es-ES``), and Thai (``th-TH``). In addition, Turkish
(``tu-TU``), Chinese (``zh-CN``) and Japanese (``ja-JP``) can be target
languages. Languages requiring special fonts have not been tested. These are
subject to change, so check
https://cloud.google.com/translate/media/docs/languages for a full list.

To keep the captions well contained, the translations are output to a text file
in a special format. First, long utterance strings are wrapped to the specified
number of characters. Then, these are joined using ``~^~`` as a special
delimiter. This delimiter allows us to work around encoding a multi-line string
on a single line. The included OBS script (``text-overdrive.py``) then decodes
these back into newlines for display in OBS. A special OBS script is required,
rather than just reading from a text file, because captions require a much
higher refresh rate than the ~1 Hz that OBS currently provides.

This was hacked together for a meeting with two spoken languages. So, in order
to be able to switch translations on the fly, you can also press ````` during
runtime in the terminal window to swap the source and target languages.

This script currently uses the enhanced video language model for translating
from ``en-US``, which seems to work reasonably well when displayed in realtime
as results are returned. However, the same cannot be said of ``es-MX`` to
``en-US``. The quality of this translation is far worse. In order to have a
reasonable experience, we only print the final translation as a chunk. So,
compared to the reverse translation, it will appear to have much longer latency
between the speaker talking and the captions appearing, but this way the
captions at least convey the gist of the message.

Displaying in OBS
^^^^^^^^^^^^^^^^^
The captions look best with a dark background. On an HD canvas, I use a
background of #c8000000 that is 1920x250 in size. Captions go on top of that in
#dedede. I like Lato Semibold, size 256. I show 3 lines of text with 55 chars.

Contributing
------------

You can quickly install the developer pre-commit hooks be running:
::
    $ make dev

From inside your poetry shell.

Roadmap
-------
- [ ] Code clean-up, e.g. enums for languages, rather than strings.
- [ ] Additional word filtering or blacklisting.
- [ ] Stop using a text file to pass information between processes. Perhaps
  just build this into a single stand-alone OBS plugin?


.. _Media Translation API: https://cloud.google.com/media-translation
.. _Open Broadcaster Software (OBS): https://obsproject.com/
.. _poetry: https://python-poetry.org/docs/#installation
