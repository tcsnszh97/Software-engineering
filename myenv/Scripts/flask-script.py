#!E:\python\szuprojects\flasky\myenv\Scripts\python3.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'Flask==0.12','console_scripts','flask'
__requires__ = 'Flask==0.12'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('Flask==0.12', 'console_scripts', 'flask')()
    )
