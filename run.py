"""PyInstaller entry point. For development use:  py -m hermetiks"""
import sys

from hermetiks.ui import run

if __name__ == "__main__":
    run(sys.argv[1:])
