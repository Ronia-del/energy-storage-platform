import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import threading
from datetime import datetime
from contextlib import closing
import shutil

# -------------------------- 页面基础配置 --------------------------
st.set_page_config(
    page_title="储能项目匹配平台",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 数据库锁（防止多人并发写入冲突）
DB_LOCK = threading.Lock()

# -------------------------- 数据库初始化核心 --------------------------
def init_database():
    """初始化所有数据表：用户表、新项目表、历史项目表"""
    with closing(sqlite3.connect('energy_storage.db', check_same_thread=False)) as conn:
        cursor = conn.cursor()

        # 用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '普通用户'
        )
        ''')

        # 待审核新项目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            产品型号版本 TEXT,
            变流单元类型 TEXT,
            变压器规格 TEXT,
            环网柜规格 TEXT,
            SCC规格 TEXT,
            售卖区域 TEXT,
            项目名称 TEXT,
            手册料号 TEXT,
            网址链接 TEXT,
            创建时间 TEXT,
            处理状态 TEXT DEFAULT '待审核',
            处理人 TEXT DEFAULT ''
        )
        ''')

        # 历史项目库
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            产品型号版本 TEXT,
            变流单元类型 TEXT,
            变压器规格 TEXT,
            环网柜规格 TEXT,
            SCC规格 TEXT,
            售卖区域 TEXT,
            项目名称 TEXT,
            手册料号 TEXT,
            网址链接 TEXT,
            创建时间 TEXT,
            处理状态 TEXT,
            处理人 TEXT
        )
        ''')

        # 初始化默认管理员账号（admin/admin123）
        default_admin_pwd = encrypt_password("admin123")
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", default_admin_pwd, "管理员")
            )

        conn.commit()

# -------------------------- 通用工具函数 --------------------------
def encrypt_password(pwd):
    """密码加密"""
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

def load_table(table_name):
    """从数据库读取表为DataFrame"""
    with DB_LOCK:
        with closing(sqlite3.connect('energy_storage.db', check_same_thread=False)) as conn:
            return pd.read_sql(f"SELECT * FROM {table_name}", conn)

def save_table(df, table_name):
    """保存DataFrame到数据库表（覆盖写入）"""
    with DB_LOCK:
        with closing(sqlite3.connect('energy_storage.db', check_same_thread=False)) as conn:
            conn.execute(f"DELETE FROM {table_name}")
            df.to_sql(table_name, conn, index=False, if_exists="append")

def backup_database():
    """数据库备份"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_energy_storage_{now}.db"
    shutil.copy("energy_storage.db", backup_file)
    return backup_file

# -------------------------- 登录/注册/权限 --------------------------
def login_user(username, pwd):
    encrypted = encrypt_password(pwd)
    with closing(sqlite3.connect('energy_storage.db', check_same_thread=False)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, encrypted))
        return cursor.fetchone()

def add_user(username, pwd, role="普通用户"):
    try:
        encrypted = encrypt_password(pwd)
        with closing(sqlite3.connect('energy_storage.db', check_same_thread=False)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, encrypted, role)
            )
            conn.commit()
            return True
    except:
        return False

# -------------------------- 页面功能：登录 --------------------------
def show_login_page():
    st.title("⚡ 储能项目匹配平台 - 登录")
    username = st.text_input("账号")
    pwd = st.text_input("密码", type="password")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("登录"):
            user = login_user(username, pwd)
            if user:
                st.session_state["login"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user[3]
                st.success(f"欢迎回来，{username}！")
                st.rerun()
            else:
                st.error("账号或密码错误")

    with col2:
        if st.button("注册新用户"):
            if add_user(username, pwd):
                st.success("注册成功！请登录")
            else:
                st.error("注册失败：账号已存在")

    st.caption("默认管理员：admin / admin123")

# -------------------------- 页面功能：首页 --------------------------
def show_home():
    st.title("⚡ 储能项目匹配管理平台")
    st.markdown("""
    ### 平台功能
    - ✅ 提交储能项目信息
    - ✅ 管理员审核项目
    - ✅ 历史项目库查询
    - ✅ 多人在线协作
    """)
    st.success(f"当前登录：{st.session_state['username']} | 权限：{st.session_state['role']}")

# -------------------------- 页面功能：提交新项目 --------------------------
def show_submit_project():
    st.title("📝 提交新项目")
    with st.form("new_project"):
        col1, col2 = st.columns(2)
        with col1:
            产品型号版本 = st.text_input("产品型号版本")
            变流单元类型 = st.text_input("变流单元类型")
            变压器规格 = st.text_input("变压器规格")
            环网柜规格 = st.text_input("环网柜规格")
        with col2:
            SCC规格 = st.text_input("SCC规格")
            售卖区域 = st.text_input("售卖区域")
            项目名称 = st.text_input("项目名称")
            手册料号 = st.text_input("手册料号")
            网址链接 = st.text_input("网址链接")

        submitted = st.form_submit_button("提交项目")

    if submitted:
        new_data = {
            "产品型号版本": 产品型号版本,
            "变流单元类型": 变流单元类型,
            "变压器规格": 变压器规格,
            "环网柜规格": 环网柜规格,
            "SCC规格": SCC规格,
            "售卖区域": 售卖区域,
            "项目名称": 项目名称,
            "手册料号": 手册料号,
            "网址链接": 网址链接,
            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "处理状态": "待审核",
            "处理人": st.session_state["username"]
        }

        df = load_table("new_projects")
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_table(df, "new_projects")
        st.success("✅ 项目提交成功，等待管理员审核！")

# -------------------------- 页面功能：项目审核（管理员） --------------------------
def show_audit_project():
    if st.session_state["role"] != "管理员":
        st.error("❌ 仅管理员可访问")
        return

    st.title("🔍 项目审核")
    df = load_table("new_projects")

    if df.empty:
        st.info("暂无待审核项目")
        return

    st.dataframe(df, use_container_width=True)
    select_id = st.number_input("输入要审核的项目ID", min_value=0, value=0)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 通过审核（移入历史库）"):
            item = df[df["id"] == select_id]
            if item.empty:
                st.error("项目不存在")
            else:
                history_df = load_table("history_projects")
                history_df = pd.concat([history_df, item], ignore_index=True)
                save_table(history_df, "history_projects")
                new_df = df[df["id"] != select_id]
                save_table(new_df, "new_projects")
                st.success("审核通过，已归档至历史库")
                st.rerun()

    with col2:
        if st.button("❌ 驳回项目"):
            df = df[df["id"] != select_id]
            save_table(df, "new_projects")
            st.success("已驳回该项目")
            st.rerun()

# -------------------------- 页面功能：历史项目库 --------------------------
def show_history():
    st.title("📚 历史项目库")
    df = load_table("history_projects")
    st.dataframe(df, use_container_width=True)

# -------------------------- 页面功能：用户管理（管理员） --------------------------
def show_user_admin():
    if st.session_state["role"] != "管理员":
        st.error("❌ 仅管理员可访问")
        return

    st.title("👥 用户管理")
    users_df = load_table("users")
    st.dataframe(users_df, use_container_width=True)

    st.subheader("新增用户")
    new_user = st.text_input("新账号")
    new_pwd = st.text_input("新密码", type="password")
    new_role = st.selectbox("权限", ["普通用户", "管理员"])

    if st.button("添加用户"):
        if add_user(new_user, new_pwd, new_role):
            st.success("用户添加成功")
            st.rerun()
        else:
            st.error("用户已存在")

# -------------------------- 页面功能：系统备份 --------------------------
def show_backup():
    if st.session_state["role"] != "管理员":
        st.error("❌ 仅管理员可访问")
        return

    st.title("💾 数据库备份")
    if st.button("立即备份"):
        file = backup_database()
        st.success(f"备份完成：{file}")

# -------------------------- 主程序路由 --------------------------
def main():
    # 初始化数据库
    init_database()

    # 会话状态初始化
    if "login" not in st.session_state:
        st.session_state["login"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""

    # 未登录 → 显示登录页
    if not st.session_state["login"]:
        show_login_page()
        return

    # 已登录 → 显示侧边栏菜单
    menu = [
        "🏠 首页",
        "📝 提交新项目",
        "📚 历史项目库",
        "🔍 项目审核（管理员）",
        "👥 用户管理（管理员）",
        "💾 系统备份（管理员）"
    ]
    choice = st.sidebar.radio("菜单", menu)

    # 路由
    if choice == "🏠 首页":
        show_home()
    elif choice == "📝 提交新项目":
        show_submit_project()
    elif choice == "📚 历史项目库":
        show_history()
    elif choice == "🔍 项目审核（管理员）":
        show_audit_project()
    elif choice == "👥 用户管理（管理员）":
        show_user_admin()
    elif choice == "💾 系统备份（管理员）":
        show_backup()

    # 退出登录
    if st.sidebar.button("🚪 退出登录"):
        st.session_state["login"] = False
        st.rerun()

if __name__ == "__main__":
    main()