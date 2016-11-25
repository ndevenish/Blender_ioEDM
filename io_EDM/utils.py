

import contextlib, os

@contextlib.contextmanager
def chdir(to):
    original = os.getcwd()
    try: 
      os.chdir(to)
      yield
    finally:
      os.chdir(original)