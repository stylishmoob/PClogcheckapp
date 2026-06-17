import sqlite3
from flask import Flask,render_template,request,redirect,url_for,session
from werkzeug.security import generate_password_hash,check_password_hash
import math,os

app=Flask(__name__)

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DB_NAME=os.path.join(BASE_DIR,"pclog.db")

def get_logs(period):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    where_sql=check_period(period)

    cur.execute(f"""SELECT * FROM activity_logs {where_sql} ORDER BY start_time DESC""")
    logs=cur.fetchall()

    conn.close()
    return logs

def get_app_summary(period):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()
    
    where_sql=check_period(period)
    
    cur.execute(f"""
        SELECT app_name,SUM(duration_seconds)
        FROM activity_logs 
        {where_sql}
        GROUP BY app_name
        ORDER BY SUM(duration_seconds) DESC
        """)

    summary=cur.fetchall()
    conn.close()
    return summary

def get_daily_summary(period):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    where_sql=check_period(period)

    cur.execute(f"""
        SELECT DATE(start_time),
                SUM(duration_seconds)
        FROM activity_logs {where_sql}
        GROUP BY DATE(start_time)
        ORDER BY DATE(start_time)""")
    
    result=cur.fetchall()

    conn.close()
    return result

def get_category(app_name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT category_name
            FROM app_categories
            WHERE app_name = ?""",(app_name,))
    
    result=cur.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        return "その他"
#アプリのすべてを見ることで処理が重くなるため変更
#def get_category_summary(period):
    # summary=get_app_summary(period)

    # category_totals={}

    # for app_name,seconds in summary:
    #     category=get_category(app_name)

    #     if category not in category_totals:
    #         category_totals[category]=0

    #     category_totals[category] += seconds

    # return sorted(
    #     category_totals.items(),
    #     key=lambda x:x[1],
    #     reverse=True
    # )
def get_category_summary(period):
    summary=get_app_summary(period)
    category_map=get_category_map()

    category_totals={}

    for app_name,seconds in summary:
        category=category_map.get(app_name,"その他")

        if category not in category_totals:
            category_totals[category]=0

        category_totals[category] += seconds

    return sorted(
        category_totals.items(),
        key=lambda x:x[1],
        reverse=True
    )

def get_category_map():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT app_name,category_name
        FROM app_categories""")
    
    rows=cur.fetchall()
    conn.close()

    category_map={}

    for app_name,category_name in rows:
        category_map[app_name]=category_name

    return category_map

def get_daily_category_summary(period):
    logs=get_logs(period)

    daily_category_totals={}

    for log in logs:
        app_name=log[2]
        start_time=log[3]
        seconds=log[5]

        date=start_time[:10]
        category=get_category(app_name)

        key=(date,category)

        if key not in daily_category_totals:
            daily_category_totals[key]=0

        daily_category_totals[key] +=seconds

    return sorted(daily_category_totals.items())

def check_period(period):
    if period == "today":
        where="WHERE DATE(start_time)=DATE('now','localtime')"
    elif period =="week":
        where="WHERE DATE(start_time)>=DATE('now','-6 days','localtime')"
    elif period =="month":
        where="WHERE strftime('%Y-%m',start_time) =strftime('%Y-%m','now','localtime')"
    elif period=="year":
        where="WHERE strftime('%Y',start_time)=strftime('%Y','now','localtime')"
    else:
        where=""
    
    return where

def add_app_category(app_name,category):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO app_categories (app_name,category_name)
                VALUES (?,?)""",(app_name,category))

    conn.commit()
    conn.close()

def get_app_categories():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT app_name, category_name
        FROM app_categories
        ORDER BY app_name""")
    
    categories=cur.fetchall()
    
    conn.close()
    return categories

def get_uncategorized_apps():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT DISTINCT app_name
        FROM activity_logs
        WHERE app_name NOT IN (
            SELECT app_name FROM app_categories)
            ORDER BY app_name
                """)
    
    apps=cur.fetchall()

    conn.close()
    return apps

def delete_app_category(app_name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()
    cur.execute("""
        DELETE FROM app_categories
        WHERE app_name = ?""",(app_name,))
    
    conn.commit()
    conn.close()

def edit_app_category(app_name,category_name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()
    cur.execute("""
        UPDATE app_categories
        SET category_name=?
        WHERE app_name=?""",(category_name,app_name))

    conn.commit()
    conn.close()

#今日のタイムラインを作るため今日だけのlogを返してる
def get_today_timeline():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT window_title, app_name,start_time,end_time,duration_seconds
        FROM activity_logs
        WHERE DATE(start_time)=DATE('now','localtime')
        ORDER BY start_time
        """)
    logs=cur.fetchall()
    conn.close()
    return logs
#カテゴリー名のみのテーブル生成
def init_category_names():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS category_names(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE)""")
    
    conn.commit()
    conn.close()
#カテゴリー名テーブルに追加
def add_category_name(name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO category_names(name)
        VALUES (?)""",(name,))
    
    conn.commit()
    conn.close()
#kカテゴリーテーブルからカテゴリー名取得
def get_category_names():
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        SELECT name FROM category_names ORDER BY name""")

    names=cur.fetchall()

    conn.close()

    return names
#カテゴリー名を変更,同様にapp_categoriesテーブルのカテゴリー名も変更
def edit_category_name(old_name,new_name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        UPDATE category_names
        SET name= ?
        WHERE name=?""",(new_name,old_name))
    
    cur.execute("""
        UPDATE app_categories
        SET category_name = ?
        WHERE category_name =?""",(new_name,old_name))
    
    conn.commit()
    conn.close()
#カテゴリー名削除と同時にそれに紐づいたアプリ名を'その他'へ
def delete_category_name(name):
    conn=sqlite3.connect(DB_NAME)
    cur=conn.cursor()

    cur.execute("""
        DELETE FROM category_names
        WHERE name =?""",(name,))
        
    cur.execute("""
        UPDATE app_categories
        SET category_name = 'その他'
        WHERE category_name = ?""",(name,))
    
    conn.commit()
    conn.close()

@app.route("/")
def home():
    summary_hours=[]
    unit=request.args.get("unit","minutes")
    period=request.args.get("period","all")

    logs=get_logs(period)
    summary=get_app_summary(period)


    for app_name, seconds in summary:
        if unit=="seconds":
            value=seconds

        elif unit=="minutes":
            value=round(seconds/60,2)

        else:
            value=round(seconds/3600,2)
        
        summary_hours.append((app_name,value))

    app_ranking=summary_hours[:5]

    daily_summary=get_daily_summary(period)
    daily_hours=[]

    for date,seconds in daily_summary:
        if unit=="seconds":
            value=seconds

        elif unit=="minutes":
            value=round(seconds/60,2)

        else:
            value=round(seconds/3600,2)
        
        daily_hours.append(
            (date,value)
        )

    daily_ranking=sorted(
        daily_hours,
        key=lambda x:x[1],
        reverse=True)[:5]

    category_summary=get_category_summary(period)
    category_hours=[]

    for category,seconds in category_summary:
        if unit=="seconds":
            value=seconds
        elif unit == "minutes":
            value=round(seconds/60,2)
        else:
            value=round(seconds/3600,2)

        category_hours.append((category,value))

    category_ranking=category_hours[:5]

    daily_category_hours=[]
    daily_category_summary=get_daily_category_summary(period)


    for (date,category),seconds in daily_category_summary:
        if unit=="seconds":
            value=seconds

        elif unit=="minutes":
            value=round(seconds/60,2)

        else:
            value=round(seconds/3600,2)
        
        daily_category_hours.append({
        "date":date,
        "category":category,
        "value":value
        })

    daily_category_ranking=sorted(
        daily_category_hours,
        key=lambda x:x["value"],
        reverse=True)[:5]

    period_labels={
        "all":"全期間",
        "today":"今日",
        "week":"今週",
        "month":"今月",
        "year":"今年"
    }
    unit_labels={
        "seconds":"秒",
        "minutes":"分",
        "hours":"時間"
    }

    today_category_ranking=[]
    
    today_category=get_category_summary("today")

    for category,seconds in today_category:
        if unit=="seconds":
            value=seconds
        elif unit=="minutes":
            value=round(seconds/60,2)
        elif unit=="hours":
            value=round(seconds/3600,2)

        today_category_ranking.append(
            (category,value)
        )

    today_timeline=get_today_timeline()

    return render_template("index.html",logs=logs,
            summary=summary_hours,daily_summary=daily_hours,
            category_summary=category_hours,daily_category_summary=daily_category_hours,
            unit=unit,period=period,period_labels=period_labels,unit_labels=unit_labels,
            app_ranking=app_ranking,daily_ranking=daily_ranking,category_ranking=category_ranking,daily_category_ranking=daily_category_ranking,
            today_category_ranking=today_category_ranking,today_timeline=today_timeline)

@app.route("/categories",methods=["POST","GET"])
def categories():
    if request.method=="POST":
        action=request.form["action"]

        if action == "add_category_name":
            name=request.form["name"]
            add_category_name(name)

        elif action == "add_app_name":
            app_name=request.form["app_name"]
            category_name=request.form["category_name"]
            add_app_category(app_name,category_name)

        elif action =="edit_category_name":
            old_name=request.form["old_name"]
            new_name=request.form["new_name"]
            edit_category_name(old_name,new_name)

        elif action =="delete_category_name":
            name=request.form["name"]
            delete_category_name(name)
            
        return redirect(url_for("categories"))
    
    categories=get_app_categories()
    uncategorized_apps=get_uncategorized_apps()
    category_names=get_category_names()

    return render_template("categories.html",categories=categories,uncategorized_apps=uncategorized_apps,category_names=category_names)

@app.route("/delete_category/<app_name>",methods=["POST"])
def delete_category(app_name):
    delete_app_category(app_name)

    return redirect(url_for("categories"))

@app.route("/edit_category/<app_name>",methods=["POST"])
def edit_category(app_name):
    category_name=request.form["category_name"]

    edit_app_category(app_name,category_name)

    return redirect(url_for("categories"))


init_category_names()

if __name__ == "__main__":
    app.run(debug=True)