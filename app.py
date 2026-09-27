from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
import sqlite3
from db import init_db

app = Flask(__name__)
# 密钥，用于session加密，可自行修改
app.secret_key = "blog_secret_key_2026"

# 数据库连接工具函数
def get_db_conn():
    conn = sqlite3.connect("blog.db")
    conn.row_factory = sqlite3.Row
    return conn

# ========== 路由：首页 / 文章列表 ==========
@app.route('/')
def index():
    conn = get_db_conn()
    # 分页，默认第1页，每页5篇
    page = request.args.get("page", 1, type=int)
    page_size = 5
    offset = (page - 1) * page_size
    articles = conn.execute(
        "SELECT a.*, u.username FROM article a JOIN user u ON a.user_id=u.id ORDER BY create_time DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM article").fetchone()[0]
    conn.close()
    return render_template("index.html", articles=articles, page=page, total=total, page_size=page_size)

# ========== 用户注册 ==========
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"].encode("utf-8")
        hashed_pwd = bcrypt.hashpw(password, bcrypt.gensalt())
        conn = get_db_conn()
        try:
            conn.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, hashed_pwd))
            conn.commit()
            flash("注册成功，请登录")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("用户名已存在")
        finally:
            conn.close()
    return render_template("register.html")

# ========== 用户登录 ==========
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"].encode("utf-8")
        conn = get_db_conn()
        user = conn.execute("SELECT * FROM user WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and bcrypt.checkpw(password, user["password"]):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("登录成功")
            return redirect(url_for("index"))
        else:
            flash("账号或密码错误")
    return render_template("login.html")

# ========== 退出登录 ==========
@app.route('/logout')
def logout():
    session.clear()
    flash("已退出登录")
    return redirect(url_for("index"))

# ========== 发布文章 ==========
@app.route('/article/new', methods=["GET", "POST"])
def new_article():
    # 校验是否登录
    if "user_id" not in session:
        flash("请先登录")
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        user_id = session["user_id"]
        conn = get_db_conn()
        conn.execute("INSERT INTO article(title,content,user_id) VALUES (?,?,?)",(title,content,user_id))
        conn.commit()
        conn.close()
        flash("文章发布成功")
        return redirect(url_for("index"))
    return render_template("new_article.html")

# ========== 文章详情 + 评论 ==========
@app.route('/article/<int:article_id>', methods=["GET","POST"])
def article_detail(article_id):
    conn = get_db_conn()
    if request.method == "POST":
        # 提交评论
        if "user_id" not in session:
            flash("登录后才能评论")
            return redirect(url_for("login"))
        comment_content = request.form["content"]
        user_id = session["user_id"]
        conn.execute("INSERT INTO comment(article_id,user_id,content) VALUES (?,?,?)",(article_id,user_id,comment_content))
        conn.commit()
    # 查询文章信息
    art = conn.execute("SELECT a.*,u.username FROM article a JOIN user u ON a.user_id=u.id WHERE a.id=?",(article_id,)).fetchone()
    # 查询评论
    comments = conn.execute("SELECT c.*,u.username FROM comment c JOIN user u ON c.user_id=u.id WHERE c.article_id=?",(article_id,)).fetchall()
    conn.close()
    return render_template("detail.html",article=art,comments=comments)

# ========== 删除文章（仅作者可删） ==========
@app.route('/article/delete/<int:article_id>', methods=["POST"])
def del_article(article_id):
    if "user_id" not in session:
        flash("请登录")
        return redirect(url_for("login"))
    conn = get_db_conn()
    art = conn.execute("SELECT * FROM article WHERE id=?",(article_id,)).fetchone()
    if art and art["user_id"] == session["user_id"]:
        conn.execute("DELETE FROM article WHERE id=?",(article_id,))
        conn.commit()
        flash("删除成功")
    conn.close()
    return redirect(url_for("index"))

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
