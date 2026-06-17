import sqlite3
import time,os
from datetime import datetime
import win32gui
import win32process
import psutil


BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DB_NAME=os.path.join(BASE_DIR,"pclog.db") 



def init_db():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_title TEXT,
            app_name TEXT,
            start_time TEXT,
            end_time TEXT,
            duration_seconds INTEGER)""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL UNIQUE,
            category_name TEXT NOT NULL)""")

    conn.commit()
    conn.close()

def save_log(window_title,app_name,start_time,end_time,duration):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        INSERT INTO activity_logs
        (window_title,app_name,start_time,end_time,duration_seconds)
        VALUES(?,?,?,?,?)""",(window_title,app_name,start_time,end_time,duration))

    conn.commit()
    conn.close()


def get_active_window_info():
    hwnd=win32gui.GetForegroundWindow()

    window_title=win32gui.GetWindowText(hwnd)

    _, pid= win32process.GetWindowThreadProcessId(hwnd)

    try:
        process=psutil.Process(pid)
        app_name=process.name()
    except psutil.Error:
        app_name="Unknown"

    return window_title,app_name

init_db()

current_title=None
current_app_name=None
start_time=None

while True:
    new_title,new_app_name=get_active_window_info()

    if current_title is None:
        current_title=new_title
        current_app_name=new_app_name
        start_time=datetime.now()


    elif new_title != current_title:
        end_time=datetime.now()
        duration = (end_time - start_time).seconds

        save_log(current_title,
                 current_app_name,
                 start_time.strftime("%Y-%m-%d %H:%M:%S"),
                 end_time.strftime("%Y-%m-%d %H:%M:%S"),
                 duration)

        print("保存しました",current_title,current_app_name,duration)

        current_title=new_title
        current_app_name=new_app_name
        start_time=datetime.now()

    time.sleep(5)