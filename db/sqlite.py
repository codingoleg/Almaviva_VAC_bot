import sqlite3 as sq
from typing import Tuple

import db
import telegram.loggers as loggers

__all__ = [
    'user_id_exists', 'check_data_acc', 'check_data_person', 'reset_values',
    'select_data', 'delete_user', 'update_value', 'update_values',
    'insert_row', 'select_active_users', 'create_all_tables'
]
DB_PATH = './db/users.db'


def create_table_acc():
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {db.ACCOUNT} (
                {db.USER_ID}         INTEGER NOT NULL PRIMARY KEY,
                {db.USERNAME_ALMA}   TEXT,
                {db.PASSWORD_ALMA}   TEXT,
                {db.NUM_OF_PERSONS}  TEXT,
                {db.CITY}            TEXT,
                {db.ST_MONTH}        INTEGER,
                {db.ST_DAY}          INTEGER,
                {db.FIN_MONTH}       INTEGER,
                {db.FIN_DAY}         INTEGER,
                {db.AUTH_TOKEN}      TEXT,
                {db.START_TIME}      TEXT,
                {db.IS_ACTIVE}       INTEGER DEFAULT 0,
                {db.LAST_REQUEST}    TEXT,
                {db.ATTEMPTS}        INTEGER DEFAULT 0 
            )''')


def create_table_person(table_person: str):
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_person} (
                {db.USER_ID}   INTEGER NOT NULL PRIMARY KEY,
                {db.NAME}      TEXT,
                {db.SURNAME}   TEXT,
                {db.PASSPORT}  TEXT,
                {db.PHONE}     TEXT,
                {db.EMAIL}     TEXT
            )''')


def create_table_success():
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {db.SUCCESS} (
                {db.USER_ID}       INTEGER,
                {db.SUCCESS_MONTH} INTEGER,
                {db.SUCCESS_DAY}   INTEGER,
                {db.SUCCESS_TIME}  TEXT,
                {db.ATTEMPTS}      INTEGER DEFAULT 0 
            )''')


def create_banned():
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {db.BANNED} (
                {db.USER_ID}  INTEGER,
                {db.BAN}      INTEGER DEFAULT 0 
            )''')


def create_all_tables():
    create_table_acc()
    create_table_person(db.PERSON_1)
    create_table_person(db.PERSON_2)
    create_table_success()
    create_banned()


def drop_all_tables():
    """Except 'banned'"""
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        for table in (db.ACCOUNT, db.PERSON_1, db.PERSON_2, db.SUCCESS):
            cur.execute(f'DROP TABLE IF EXISTS {table}')


def execute_query(query: str | tuple):
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(query)


def user_id_exists(user_id: int, table: str) -> bool:
    query = f'SELECT * FROM {table} WHERE {db.USER_ID}={user_id}'
    loggers.log(user_id, query)
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(query)
    return True if len(list(cur)) else False


def insert_row(table: str, column: tuple | str, values: tuple | str | int):
    if len(column) == 1:
        column = f'({str(column[0])})'
    if len(values) == 1:
        values = f'({str(values[0])})'
    query = f'INSERT INTO {table} {column} VALUES {values}'
    execute_query(query)


def update_value(user_id: int, table: str, column: str,
                 value: str | int | None):
    query = (f'UPDATE {table} SET {column}=? '
             f'WHERE {db.USER_ID}={user_id}', (value,))
    loggers.log(user_id, str(query), loggers.DEBUG)
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(*query)


def update_values(user_id: int, table: str, columns: tuple[str, str],
                  values: tuple[str | int | None, str | int | None]):
    query = (f'UPDATE {table} SET {columns[0]}=?, {columns[1]}=? '
             f'WHERE {db.USER_ID}={user_id}', (values[0], values[1]))
    loggers.log(user_id, str(query), loggers.DEBUG)
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(*query)


def delete_user(user_id: int):
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        for table in (db.ACCOUNT, db.PERSON_1, db.PERSON_2, db.SUCCESS):
            query = f'DELETE FROM {table} WHERE {db.USER_ID}={user_id}'
            loggers.log(user_id, query, loggers.INFO)
            cur.execute(query)


def select_data(user_id: int, table: str, column: str | int | tuple) -> Tuple:
    query = f'SELECT {column} FROM {table} WHERE {db.USER_ID}={user_id}'
    loggers.log(user_id, query)
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        return cur.execute(query).fetchone()


def select_active_users() -> list[Tuple[int]]:
    query = f'SELECT {db.USER_ID} FROM {db.ACCOUNT} WHERE {db.IS_ACTIVE}=1'
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        return cur.execute(query).fetchall()


def reset_values(table: str, column: str, value=False):
    query = f'UPDATE {table} SET {column}={value}'
    execute_query(query)


def check_data_acc() -> list[Tuple[int]]:
    query = f'SELECT * FROM {db.ACCOUNT}'
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        return cur.execute(query).fetchall()


def check_data_person(num_of_persons: str) -> list[Tuple[int]]:
    query = f'SELECT * FROM person_{num_of_persons}'
    with sq.connect(DB_PATH) as con:
        cur = con.cursor()
        return cur.execute(query).fetchall()
