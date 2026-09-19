"""
db.py - 个人博客数据库模块
负责：数据库连接、建表、用户/文章/评论的增删改查
"""
import sqlite3
from datetime import datetime
import bcrypt

DB_PATH = "blog.db"


# ==================== 数据库连接 ====================
def get_conn():
    """获取数据库连接，开启外键约束"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 查询结果可以按列名访问
    conn.execute("PRAGMA foreign_keys = ON")  # 开启外键约束
    return conn


# ==================== 初始化建表 ====================
def init_db():
    """创建三张表：user / article / comment"""
    conn = get_conn()
    cur = conn.cursor()

    # 用户表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    """)

    # 文章表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            user_id     INTEGER NOT NULL,
            category    TEXT DEFAULT '未分类',
            view_count  INTEGER DEFAULT 0,
            create_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
    """)

    # 评论表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comment (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id  INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            content     TEXT NOT NULL,
            create_time TEXT NOT NULL,
            FOREIGN KEY (article_id) REFERENCES article(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("数据库初始化完成（表已创建）")


# ==================== 用户表操作 ====================
def create_user(username, password):
    """注册新用户，密码用 bcrypt 加密存储。返回 (成功?, 消息)"""
    # bcrypt 要求密码是 bytes，且最长 72 字节
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO user (username, password, create_time) VALUES (?, ?, ?)",
            (username, hashed.decode("utf-8"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        return False, "用户名已存在"


def verify_user(username, password):
    """登录验证：比对密码。返回 user_id 或 None"""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, password FROM user WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    # bcrypt 比对
    if bcrypt.checkpw(password.encode("utf-8"), row["password"].encode("utf-8")):
        return row["id"]
    return None


def get_user_by_id(user_id):
    """根据 id 查用户信息（不含密码）"""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username, create_time FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== 文章表操作 ====================
def create_article(title, content, user_id, category="未分类"):
    """发布新文章"""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO article (title, content, user_id, category, create_time)
           VALUES (?, ?, ?, ?, ?)""",
        (title, content, user_id, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    article_id = cur.lastrowid
    conn.close()
    return article_id


def get_article_by_id(article_id):
    """根据 id 查文章详情，联表查作者名"""
    conn = get_conn()
    row = conn.execute(
        """SELECT a.*, u.username AS author
           FROM article a JOIN user u ON a.user_id = u.id
           WHERE a.id = ?""",
        (article_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_articles_paged(page=1, per_page=5):
    """分页查询文章列表（首页用），返回 (文章列表, 总条数)"""
    offset = (page - 1) * per_page
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.id, a.title, a.category, a.view_count, a.create_time, u.username AS author
           FROM article a JOIN user u ON a.user_id = u.id
           ORDER BY a.create_time DESC
           LIMIT ? OFFSET ?""",
        (per_page, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) AS cnt FROM article").fetchone()["cnt"]
    conn.close()
    return [dict(r) for r in rows], total


def get_articles_by_user(user_id, page=1, per_page=5):
    """查某用户的文章（个人主页用）"""
    offset = (page - 1) * per_page
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, title, category, view_count, create_time
           FROM article WHERE user_id = ?
           ORDER BY create_time DESC
           LIMIT ? OFFSET ?""",
        (user_id, per_page, offset),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS cnt FROM article WHERE user_id = ?", (user_id,)
    ).fetchone()["cnt"]
    conn.close()
    return [dict(r) for r in rows], total


def update_article(article_id, title, content, category):
    """编辑文章（权限校验在路由层做）"""
    conn = get_conn()
    conn.execute(
        "UPDATE article SET title = ?, content = ?, category = ? WHERE id = ?",
        (title, content, category, article_id),
    )
    conn.commit()
    conn.close()


def delete_article(article_id):
    """删除文章（外键 ON DELETE CASCADE 会自动删关联评论）"""
    conn = get_conn()
    conn.execute("DELETE FROM article WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()


def increment_view(article_id):
    """浏览量 +1"""
    conn = get_conn()
    conn.execute(
        "UPDATE article SET view_count = view_count + 1 WHERE id = ?", (article_id,)
    )
    conn.commit()
    conn.close()


# ==================== 评论表操作 ====================
def create_comment(article_id, user_id, content):
    """发表评论"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO comment (article_id, user_id, content, create_time)
           VALUES (?, ?, ?, ?)""",
        (article_id, user_id, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_comments_by_article(article_id):
    """查某篇文章的全部评论，联表查评论人名字"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.id, c.content, c.create_time, u.username AS author
           FROM comment c JOIN user u ON c.user_id = u.id
           WHERE c.article_id = ?
           ORDER BY c.create_time ASC""",
        (article_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_comment(comment_id):
    """删除评论"""
    conn = get_conn()
    conn.execute("DELETE FROM comment WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()


# ==================== 自测入口 ====================
if __name__ == "__main__":
    # 运行此文件会自动建表
    init_db()

    # 简单自测：注册 → 登录 → 发文章 → 评论
    print("\n--- 自测 ---")
    ok, msg = create_user("testuser", "123456")
    print(f"注册: {msg}")

    uid = verify_user("testuser", "123456")
    print(f"登录验证: {'成功 uid=' + str(uid) if uid else '失败'}")

    aid = create_article("第一篇博客", "这是正文内容", uid, category="随笔")
    print(f"发布文章: id={aid}")

    increment_view(aid)
    create_comment(aid, uid, "写得不错！")

    arts, total = get_articles_paged()
    print(f"分页查询: 共{total}篇, 当前页{len(arts)}篇")
    print("文章列表:", [a["title"] for a in arts])

    comments = get_comments_by_article(aid)
    print(f"评论: {[c['content'] for c in comments]}")
