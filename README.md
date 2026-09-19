# 个人博客系统
基于Flask开发的简易个人博客，实现用户注册登录、文章发布管理、评论、分页浏览功能。
## 技术栈
Python3, Flask, SQLite, bcrypt, Jinja2, Bootstrap
## 功能
1. 用户注册、登录，密码bcrypt加密存储，基于session会话管理
2. 文章发布、编辑、删除，作者权限控制
3. 文章分页展示，文章浏览量统计
4. 文章评论功能
5. 基础文章分类
## 运行方式
1. pip install -r requirements.txt
2. python db.py 初始化数据库
3. python app.py 启动服务，访问 http://127.0.0.1:5000
## 项目说明
后端CRUD练习项目，学习用户鉴权、数据库一对多关系、分页查询。
