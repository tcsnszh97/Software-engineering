#!e:\python\szuprojects\flasky\myenv\scripts\python3.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'alembic==0.8.10','console_scripts','alembic'
__requires__ = 'alembic==0.8.10'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('alembic==0.8.10', 'console_scripts', 'alembic')()
    )
