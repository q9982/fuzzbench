`archive_race` is a synthetic reproducer for the corpus archiving race described
in `~/26-03/fuzzbench` commit `04e8254c78815cac7d9d9569453ad950298b4848`.

Instead of trying to find target-specific bugs, it keeps several corpus files
oscillating between a very large sparse size and a tiny truncated size. That
makes it much more likely that `experiment/runner.py` will `stat()` a large
file and then hit `tarfile.ReadError: unexpected end of data` after the file is
shrunk during `tar.add(...)`.
