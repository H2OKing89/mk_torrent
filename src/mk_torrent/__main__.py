"""Allow mk_torrent to be executed as a module with python -m mk_torrent."""

from .cli import main

if __name__ == "__main__":
    main()
