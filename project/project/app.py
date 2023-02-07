import os
from requests import request
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import hashlib
import uuid

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SECRET_KEY'] = 'secret_key'

# Configure CS50 Library to use SQLite database

db = SQL("sqlite:///chattest.db")

#初期画面
@app.route("/")
def index():
    return render_template("index.html")

#登録画面
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        check_name = db.execute("SELECT * FROM users WHERE name = ?", request.form.get('username'))

        if username == '' or password == '' or confirmation == '' or password != confirmation:
            if username == '':
                flash('ユーザーネームを入力してください')
            if len(check_name) != 0:
                flash('このユーザーネームは使用できません')
            if password == '':
                flash('パスワードを入力してください')
            if confirmation == '':
                flash('確認用パスワードを入力してください')
            elif password != confirmation:
                flash('パスワードと確認用パスワードが違います。')
            return redirect("/register")

        hash = generate_password_hash(password)

        try:
            db.execute("INSERT INTO users (name, password) VALUES (?, ?)", username, hash)
            return redirect("/login")
        except:
            return redirect("/register")

    else:
        return render_template("register.html")

#ログイン画面
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()
    if request.method == "POST":

        if request.form.get("username") == '' or request.form.get("password") == '':
            if request.form.get("username") == '':
                flash('ユーザー名を入力してください')
            if request.form.get("password") == '':
                flash('パスワードを入力してください')
            return render_template("login.html")

        rows = db.execute("SELECT * FROM users WHERE name = ?", request.form.get("username"))

        if len(rows) != 1or not check_password_hash(rows[0]["password"], request.form.get("password")):
            flash('ユーザーネームまたはパスワードが違います')
            return render_template("login.html")

        # Remember which user has logged in
        session["id"] = rows[0]["id"]


        # Redirect user to home page
        return redirect("/home")

    else:
        return render_template("login.html")

#ログアウト画面
@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

#ホーム画面（ログイン後）
@app.route("/home")
def home():
#友達のリクエストまたは自分のメモを表示する
        user = db.execute("SELECT name FROM users WHERE id = ?", session["id"])
        requests = db.execute("SELECT * FROM requests where receive_user=? and status = ?", user[0]["name"], "送信済")
        if len(requests) == 0:
            requests_text = ('未実行のリクエストはありません。')
        else:
            requests_text = (str(len(requests)) + '件のリクエストがあります')

        #表示するデータはto_userがログインしているユーザのモノのみ！！！！！！！！！！！！！！

        return render_template("home.html", requests=requests,requests_text=requests_text)

#ユーザー画面
@app.route("/user")
def user():
    name = db.execute("select name from users where id=?", session["id"])
    fusers1 = db.execute("select receive_user from friends where send_user = ? and status = ?", name[0]["name"], "承認")
    fusers2 = db.execute("select send_user from friends where receive_user = ? and status = ?", name[0]["name"], "承認") #フレンドを表示
    send_users = db.execute("select id, receive_user from friends where send_user = ? and status = ?",name[0]["name"], "申請")         #自分が申請した人
    receive_users = db.execute("select id, send_user from friends where receive_user = ? and status = ?",name[0]["name"], "申請")          #自分に申請している人

    return render_template("user.html", name=name[0]["name"], fusers1=fusers1, fusers2=fusers2 , send_users=send_users, receive_users=receive_users)


#ユーザー検索
@app.route('/search', methods=["GET", "POST"])
def search():
    if request.method== "POST":
        userid = request.form.get("id")
        if request.form.get("id") == '':
            flash('ユーザーIDを入力してください')
            return render_template("search.html")
        try:
            search_users = db.execute("select id, name from users where id = ?", userid)#検索した人を表示
            return render_template("search.html",search_users=search_users)
        except:
            return redirect("/search")
    else:
        return render_template("search.html")

#フレンド申請
@app.route('/apply/<int:id>', methods=["GET", "POST"])
def apply(id):
    user_id = id
    search_user = db.execute("SELECT id, name FROM users where id = ?", user_id)
    user = db.execute("SELECT name FROM users WHERE id = ?", session["id"])
    friend = db.execute("SELECT id from friends where send_user = ? and receive_user = ?", user[0]["name"], search_user[0]["name"])

    if request.method == "POST":
        try:
            if len(friend) == 0:
                db.execute("INSERT INTO friends (send_user, receive_user, status) VALUES (?, ?, ?)", user[0]["name"], search_user[0]["name"], "申請")
                flash('申請しました')
                return redirect("/home")
            else:
                flash('すでに申請しているか相手から申請が届いています')
                return redirect("/home")
        except:
            return "申請できませんでした"

    else:
        return render_template("apply.html", search_user=search_user, id=user_id)#idを取得して、applyでもデータベースを参照できるようにする

#フレンド申請承認
@app.route('/apply_ok/<int:id>', methods=["GET", "POST"])
def user_ok(id):
    user_id = id
    apply_user = db.execute("SELECT send_user FROM friends where id = ?", user_id)
    user = db.execute("SELECT name FROM users WHERE id = ?", session["id"])

    if request.method == "POST":
       #o_user = db.execute("SELECT name from users where id = ?", id)
        try:
            db.execute("UPDATE friends set status = '承認' where id = ?", id)
            flash('申請を承認しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return redirect("/home")

    else:
        return render_template("apply_ok.html", apply_user=apply_user, id=user_id)

#フレンド申請拒否
@app.route("/apply_no/<int:id>", methods=["GET", "POST"])
def user_no(id):
    user_id = id
    apply_user = db.execute("SELECT send_user FROM friends where id = ?", user_id)
    user = db.execute("SELECT name FROM users WHERE id = ?", session["id"])

    if request.method == "POST":
        try:
            db.execute("UPDATE friends set status = '拒否' where id = ?", id)
            flash('申請を拒否しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return redirect("/home")

    else:
        return render_template("apply_no.html", apply_user=apply_user, id=user_id)

#フレンド申請削除
@app.route("/apply_delete/<int:id>", methods=["GET", "POST"])
def apply_delete(id):
    user_id = id
    apply_user = db.execute("SELECT receive_user FROM friends where id = ?", user_id)
    user = db.execute("SELECT name FROM users WHERE id = ?", session["id"])

    if request.method == "POST":
        try:
            db.execute("DELETE FROM friends where id = ?", user_id)
            flash('申請を削除しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return redirect("/home")

    else:
        return render_template("apply_delete.html", apply_user=apply_user, id=user_id)

#マイリクエスト画面
@app.route("/cook_request")
def cook_request():
    user = db.execute("SELECT name from users where id = ?", session["id"])
    cook_request = db.execute("SELECT id, title, detail, type,  receive_user from requests where send_user = ?", user[0]["name"])
    receive_request = db.execute("select id, title, detail from requests where receive_user = ? and status = ?", user[0]["name"], '送信済')

    return render_template("request.html", requests=cook_request, receive_request=receive_request)

#新規リクエスト作成
@app.route("/request_new", methods=["GET", "POST"])
def request_new():
    user = db.execute("SELECT name from users where id = ?", session["id"])
    friends1 = db.execute("SELECT receive_user from friends where send_user = ? and status = ? ", user[0]["name"], '承認')
    friends2 = db.execute("SELECT send_user from friends where receive_user = ? and status = ?", user[0]["name"], '承認')

    if request.method == "POST":
        title = request.form.get('title')
        detail = request.form.get('detail')
        receive_user = request.form.get('lists')
        type = request.form.get('type')

        if title == '' or detail == '' or receive_user == '' or type == '':
            if title == '':
                flash('タイトルを入力してください')
            if detail == '':
                flash('詳細を入力してください')
            if receive_user == '':
                flash('送信相手を選択してください')
            if type == '':
                flash('タイプを入力してください')
            return redirect("/request_new")

        try:
            db.execute("INSERT INTO requests (title, detail, send_user, receive_user, type, status) VALUES (?, ?, ?, ?, ?, ?)", title, detail, user[0]["name"], receive_user, type, '送信済')
            flash('リクエストを送信しました')
            return redirect("/home")
        except:
            flash('エラーで作成できませんでした')
            return render_template("request_new.html", title=title, detail=detail, receive_user=receive_user, type=type)

    else:
        return render_template("request_new.html", user=user, friends1=friends1, friends2=friends2)

#リクエスト編集
@app.route('/request_edit/<int:id>', methods=["GET", "POST"])
def request_edit(id):
    request_id = id
    old_request = db.execute("SELECT title, detail, receive_user, type FROM requests where id = ?", request_id)
    user = db.execute("SELECT name from users where id = ?", session["id"])
    friends1 = db.execute("SELECT receive_user from friends where send_user = ? and status = ? ", user[0]["name"], '承認')
    friends2 = db.execute("SELECT send_user from friends where receive_user = ? and status = ?", user[0]["name"], '承認')

    if request.method == "POST":
       title = request.form.get('title')
       detail = request.form.get('detail')
       receive_user = request.form.get('lists')
       request_type = request.form.get('type')
       try:
           db.execute("UPDATE requests set title = ?, detail = ?, receive_user = ?, type = ?, 	update_date = (DATETIME('now', 'localtime')) where id = ?", title, detail, receive_user, request_type, request_id)
           flash('データを編集しました')
           return render_template("home.html")
       except:
           flash('不具合が生じました')
           return redirect("/home")
    else:
        return render_template("request_edit.html", old_request=old_request, user=user, friends1=friends1, friends2=friends2, id = request_id)

#リクエスト削除
@app.route("/request_delete/<int:id>", methods=["GET", "POST"])
def request_delete(id):
    request_title = db.execute("SELECT title FROM requests where id = ?", id)

    if request.method == "POST":
        try:
            db.execute("DELETE FROM requests where id = ?", id)
            flash('リクエストを削除しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return redirect("/home")

    else:
        return render_template("request_delete.html", request_title=request_title, id=id)

#リクエスト完了(未動作確認)
@app.route("/request_finish/<int:id>", methods=["GET", "POST"])
def request_finish(id):
    request_title = db.execute("SELECT title FROM requests where id = ?", id)

    if request.method == "POST":
        try:
            db.execute("UPDATE requests set status = '完了', update_date = (DATETIME('now', 'localtime')) where id = ?", request_id)
            flash('リクエストを完了しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return redirect("/home")

    else:
        return render_template("request_finish.html", request_title=request_title, id=id)

#レシピ一覧
@app.route("/my/recipe_all")
def recipe_all():
    user = db.execute("SELECT name from users where id = ?", session["id"])
    myrecipes = db.execute("SELECT id, title, update_date from recipes_title where create_user= ?", user[0]["name"])
    return render_template("recipe_all.html", recipes=myrecipes, user=user[0]["name"], login_user=user[0]["name"])

#フレンドレシピ一覧
@app.route("/friend_recipe_all/<string:name>")
def friend_recipe_all(name):
    login_user= db.execute("SELECT name from users where id = ?", session["id"])
    friend_name = name
    friend_recipes = db.execute("SELECT title, update_date from recipes_title where create_user = ?", friend_name)

    return render_template("recipe_all.html", recipes=friend_recipes, user=friend_name, login_user=login_user[0]["name"])



#レシピ追加
@app.route("/recipe_new", methods=["GET", "POST"])#レシピ追加
def recipe_new():
    create_user = db.execute("SELECT name from users where id = ?", session["id"])

    if request.method == "POST":
        title = request.form.get("title")
        material = request.form.getlist("material")
        amount = request.form.getlist("amount")
        step = request.form.getlist("step")
        comment = request.form.get("comment")

        try:

            db.execute("INSERT INTO recipes_title (title, comment, create_user) VALUES (?, ?, ?)", title, comment, create_user[0]["name"])
            material_count = len(material)
            step_count = len(step)+1
            recipe_id = db.execute("SELECT id from recipes_title where title = ? and create_user = ?", title, create_user[0]["name"])
            if material_count != 0:
                for n in range(material_count):
                    if material[n] != '' and amount[n] != '':
                        db.execute("INSERT INTO recipes_material (id, material_count, material, amount) VALUES (?, ?, ?, ?)", recipe_id[0]["id"], n+1, material[n], amount[n])
            if len(step) != 0:
                for n in range(1, step_count):
                    if step[n-1] != '':
                        db.execute("INSERT INTO recipes_step (id, step_count, step_text) VALUES (?, ?, ?)", recipe_id[0]["id"], n, step[n-1])
            flash('成功しました')
            return render_template("home.html")
        except:
            flash('不具合が生じました')
            return render_template("recipe_new.html", title=title, material=material, amount=amount, step=step, create_user=create_user[0]["name"], a=len(material), b=len(step))

    return render_template("recipe_new.html", create_user=create_user[0]["name"])


#レシピ詳細
@app.route("/recipe_detail/<int:id>", methods=["GET", "POST"])#レシピ詳細
def recipe_detail(id):
    recipe_id = id
    recipe_title = db.execute("SELECT title FROM recipes_title WHERE id = ?", recipe_id)
    recipe_materials = db.execute("SELECT material, amount FROM recipes_material WHERE id = ?", recipe_id)
    material_count = len(recipe_materials)
    recipe_steps = db.execute("SELECT step_count, step_text FROM recipes_step WHERE id = ?", recipe_id)
    step_count = len(recipe_steps)
    recipe_create_user = db.execute("SELECT create_user FROM recipes_title WHERE id = ?", recipe_id)
    recipe_update_date = db.execute("SELECT update_date FROM recipes_title WHERE id = ?", recipe_id)
    recipe_comment = db.execute("SELECT comment FROM recipes_title WHERE id = ?", recipe_id)
    user = db.execute("SELECT name from users where id = ?", session["id"])

    return render_template("recipe_detail.html",user=user[0]["name"], recipe_id=recipe_id, recipe_title=recipe_title, recipe_materials=recipe_materials, material_count=material_count, recipe_steps=recipe_steps, step_count=step_count, recipe_create_user=recipe_create_user[0]["create_user"], recipe_update_date=recipe_update_date, recipe_comment=recipe_comment)

#レシピ削除
@app.route("/recipe_delete/<int:id>", methods=["GET", "POST"])
def recipe_delete(id):
    recipe_id = id
    recipe_title = db.execute("SELECT title FROM recipes_title where id = ?", recipe_id)

    if request.method == "POST":
        try:
            db.execute("DELETE FROM recipes_title where id = ?", recipe_id)
            db.execute("DELETE FROM recipes_material where id = ?", recipe_id)
            db.execute("DELETE FROM recipes_step where id = ?", recipe_id)
            flash('リクエストを削除しました')
            return redirect("/my/recipe_all")
        except:
            flash('不具合が生じました')
            return redirect("/my/recipe_all")

    else:
        return render_template("recipe_delete.html", recipe_title=recipe_title[0]["title"], id=recipe_id)


#レシピ編集
"""
@app.route("/recipe_edit/<int:id>", methods=["GET", "POST"])
def recipe_edit(id):
    recipe_id = id
    recipe_title = db.execute("SELECT title FROM recipes_title WHERE id = ?", recipe_id)
    recipe_materials = db.execute("SELECT material, amount FROM recipes_material WHERE id = ?", recipe_id)
    recipe_material_count = len(recipe_materials)
    recipe_steps = db.execute("SELECT step_text FROM recipes_step WHERE id = ?", recipe_id)
    recipe_step_count = len(recipe_steps)
    recipe_comment = db.execute("SELECT comment FROM recipes_title WHERE id = ?", recipe_id)
    recipe_create_user = db.execute("SELECT create_user FROM recipes_title WHERE id = ?", recipe_id)

    if request.method == "POST":
        new_title = request.form.get("title")
        new_material = request.form.getlist("material")
        new_amount = request.form.getlist("amount")
        new_step = request.form.getlist("step")
        new_comment = request.form.get("comment")
        new_material_count = len(new_material)
        new_step_count = len(new_step)
        material_diff = new_material_count - recipe_material_count
        step_diff = new_step_count - recipe_step_count
        try:
            db.execute("UPDATE recipes_title set title = ?, comment = ?, update_date = (DATETIME('now', '+9 hours')) where id = ?", new_title, new_comment, recipe_id)
            for n in range(recipe_material_count):
                db.execute("UPDATE recipes_material set material = ?, amount = ? where id = ? and recipe_count = ?", new_material[n], new_amount[n], recipe_id, n+1)
            if material_diff > 0:#更新分の方が多い場合
                for n in range(material_diff):
                    db.execute("INSERT INTO recipe_material (id, material_count, material, amount) VALUES (?, ?, ?, ?)", recipe_id[0]["id"], n+recipe_material_count+1, new_material[n+recipe_material_count], new_amount[n+recipe_material_count])
            if material_diff < 0:#元々の方が多い場合
                for n in range(abs(material_diff)):
                    db.execute("DELETE FROM recipes_material where id = ? and material_count = ?", recipe_id, n+new_material_count+1)
            for n in range(recipe_step_count):
                db.execute("UPDATE recipes_step set step_text = ? where id = ? and step_count = ?", new_step[n], recipe_id, n+1)
            if material_diff > 0:
                for n in range(step_diff):
                    db.execute("INSERT INTO recipes_step (id, step_count, step_text) VALUES (?, ?, ?)", recipe_id[0]["id"], n+recipe_step_count+1, new_step[n+recipe_step_count])
            if material_diff < 0:
                for n in range(abs(step_diff)):
                    db.execute("DELETE FROM recipes_step where id = ? and step_count = ?", recipe_id, n+recipe_material_count+1)
            flash('編集しました')
            return render_template("recipe_edit.html", recipe_title=new_title, new_material=recipe_material, new_amount=new_amount, new_step=new_step, new_comment=new_comment, material_count=len(new_material)+1, step_count=len(new_step)+1)
        except:
            flash('不具合が生じました')
            return render_template("recipe_edit.html", new_material=new_material, recipe_id=recipe_id, recipe_title=recipe_title, recipe_materials=recipe_materials, material_count=len(new_material), recipe_steps=recipe_steps, step_count=len(new_step), recipe_create_user=recipe_create_user[0]["create_user"], recipe_comment=recipe_comment)

    return render_template("recipe_edit.html", recipe_id=recipe_id, recipe_title=recipe_title, recipe_materials=recipe_materials, material_count=recipe_material_count, recipe_steps=recipe_steps, step_count=recipe_step_count, recipe_create_user=recipe_create_user[0]["create_user"], recipe_comment=recipe_comment)
"""

@app.route("/fridge_new", methods=["GET", "POST"])#冷蔵庫登録
def fridge_new():
    create_user = db.execute("SELECT name from users where id = ?", session["id"])
    if request.method == "POST":
        foodstaff = request.form.get('foodstaff')
        amount = request.form.get('amount')
        fridge_class = request.form.get('lists')


        if foodstaff == '' or amount == '' or fridge_class == '':
            if foodstaff == '':
                flash('食材名を入力してください')
            if amount == '':
                flash('量を入力してください')
            if fridge_class == '':
                flash('分類を選択してください')

            return redirect("/fridge_new")

        try:
            db.execute("INSERT INTO fridge (foodstaff, amount, fridge_class, create_user) VALUES (?, ?, ?, ?)", foodstaff, amount, fridge_class, create_user[0]["name"])
            flash('リクエストを送信しました')
            return redirect("/fridge_all")
        except:
            flash('エラーで作成できませんでした')
            return render_template("fridge_new.html")

    else:
        return render_template("fridge_new.html", create_user=create_user[0]["name"])

#冷蔵庫管理
@app.route("/fridge_all")#冷蔵庫登録
def fridge_all():
    create_user = db.execute("SELECT name from users where id = ?", session["id"])
    fridge_id = db.execute("SELECT id from fridge where create_user=?", create_user[0]["name"])
    foodstaff = db.execute("SELECT foodstaff from fridge where create_user=?", create_user[0]["name"])
    fridge_count = len(foodstaff)
    amount = db.execute("SELECT amount from fridge where create_user=?", create_user[0]["name"])
    fridge_class = db.execute("SELECT fridge_class from fridge where create_user=?", create_user[0]["name"])
    update_date = db.execute("SELECT update_date from fridge where create_user=?", create_user[0]["name"])

    return render_template("fridge_all.html", fridge_count=fridge_count, fridge_id=fridge_id, foodstaff=foodstaff, amount=amount, fridge_class=fridge_class, update_date=update_date)

#食材削除
@app.route("/fridge_delete/<int:id>", methods=["GET", "POST"])
def fridge_delete(id):
    fridge_id = id
    foodstaff = db.execute("SELECT foodstaff FROM fridge where id = ?", fridge_id)

    if request.method == "POST":
        try:
            db.execute("DELETE FROM fridge where id = ?", fridge_id)
            flash('食材を削除しました')
            return redirect("/fridge_all")
        except:
            flash('不具合が生じました')
            return redirect("/fridge_all")

    else:
        return render_template("fridge_delete.html", foodstaff=foodstaff[0]["foodstaff"], id=fridge_id)

#食材編集
@app.route('/fridge_edit/<int:id>', methods=["GET", "POST"])
def fridge_edit(id):
    fridge_id = id
    create_user = db.execute("SELECT name from users where id = ?", session["id"])
    foodstaff = db.execute("SELECT foodstaff FROM fridge where id = ?", fridge_id)
    amount = db.execute("SELECT amount from fridge where id = ?", fridge_id)
    fridge_class = db.execute("SELECT fridge_class from fridge where id = ?", fridge_id)

    if request.method == "POST":
       new_foodstaff = request.form.get('foodstaff')
       new_amount = request.form.get('amount')
       new_fridge_class = request.form.get('lists')
       try:
           db.execute("UPDATE fridge set foodstaff = ?, amount = ?, fridge_class = ?, update_date = (DATETIME('now', '+9 hours')) where id = ?", new_foodstaff, new_amount, new_fridge_class, fridge_id)
           flash('データを編集しました')
           return render_template("home.html")
       except:
           flash('不具合が生じました')
           return redirect("/fridge_all")
    else:
        return render_template("fridge_edit.html", fridge_id=fridge_id, foodstaff=foodstaff,amount=amount, fridge_class=fridge_class)


