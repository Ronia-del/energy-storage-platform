import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib
from io import BytesIO

# ===================== 全局样式美化（大气商务版） =====================
st.markdown("""
<style>
/* 整体背景 */
.stApp {
    background-color: #f8f9fa;
}
/* 左侧边栏加宽 */
section[data-testid="stSidebar"] {
    min-width: 260px;
    max-width: 260px;
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}
/* 侧边栏标题 */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 2rem;
    padding-bottom: 1rem;
}
/* 菜单选项美化 */
div[data-testid="stRadio"] > label {
    font-size: 15px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 10px;
}
div[data-testid="stRadio"] > div > div {
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 500;
    margin-bottom: 6px;
    transition: all 0.2s ease;
}
div[data-testid="stRadio"] > div > div:hover {
    background-color: #f3f4f6;
}
div[data-testid="stRadio"] > div > div[aria-selected="true"] {
    background-color: #0052cc;
    color: white !important;
    font-weight: 600;
}
/* 按钮统一大气 */
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"] {
    border-radius: 10px !important;
    height: 3.0em !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}
/* 标题样式 */
h1 {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #111827 !important;
    margin-bottom: 1rem !important;
}
h2, h3 {
    font-weight: 600 !important;
    color: #1f2937 !important;
}
/* 卡片/输入框 */
div[data-testid="stTextInput"] input,
div[data-testid="stSelect"] select {
    border-radius: 10px !important;
}
/* 表格 */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
/* 欢迎卡片样式 */
.welcome-card {
    background: linear-gradient(135deg, #0052cc 0%, #0066ff 100%);
    padding: 40px;
    border-radius: 20px;
    text-align: center;
    color: white;
    margin-bottom: 30px;
    box-shadow: 0 10px 30px rgba(0,82,204,0.2);
}
.welcome-card h1 {
    color: white !important;
    font-size: 32px !important;
    margin-bottom: 10px !important;
}
.welcome-card p {
    font-size: 18px;
    opacity: 0.9;
}
</style>
""", unsafe_allow_html=True)

# ===================== 页面配置 =====================
st.set_page_config(page_title="储能项目手册料号申请及管理系统", page_icon="⚡", layout="wide")

# ===================== 核心字段 =====================
CORE_FIELDS = ['产品型号版本', '变流单元类型', '变压器规格', '环网柜规格', 'SCC规格']
INFO_FIELDS = ['售卖区域', '项目名称']
SYSTEM_FIELDS = ['手册料号', '网址链接', '创建时间', '处理状态', '处理人']
ALL_FIELDS = CORE_FIELDS + INFO_FIELDS + SYSTEM_FIELDS

# 处理状态下拉选项
STATUS_OPTIONS = ['待审核', '已借用', '已手动录入', '已批量导入', '已归档', '已取消']

# ===================== 文件路径 =====================
BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE, "历史项目库.csv")
NEW_PROJECT_PATH = os.path.join(BASE, "待审核新项目.csv")
USER_PATH = os.path.join(BASE, "用户.csv")
SOURCE_CONFIG_PATH = os.path.join(BASE, "储能项目配置表.csv")
IMPORT_FLAG_PATH = os.path.join(BASE, ".imported")

# ===================== 工具函数 =====================
def sha256(s):
    return hashlib.sha256(str(s).encode()).hexdigest()

def load_df(path):
    if not os.path.exists(path):
        return pd.DataFrame(columns=ALL_FIELDS)
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
        return df.fillna("").astype(str)
    except:
        return pd.DataFrame(columns=ALL_FIELDS)

def save_df(df, path):
    df.fillna("").astype(str).to_csv(path, index=False, encoding='utf-8-sig')

def match_rate(new_item, hist_item):
    cnt = 0
    for f in CORE_FIELDS:
        a = str(new_item.get(f, "")).strip().lower()
        b = str(hist_item.get(f, "")).strip().lower()
        if a == b and a != "" and a != "N/A":
            cnt += 1
    total = len([f for f in CORE_FIELDS if str(new_item.get(f, "")).strip() != "" and str(new_item.get(f, "")).strip() != "N/A"])
    return round(cnt / total * 100, 1) if total > 0 else 0.0

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='数据')
    return output.getvalue()

# 获取历史下拉选项（去重、排序、去空 + 加 N/A）
def get_options(df, col):
    if col not in df.columns:
        return ["N/A"]
    opts = sorted([x.strip() for x in df[col].unique() if x.strip() != ''])
    return ["N/A"] + opts

# ===================== 初始化 =====================
if not os.path.exists(USER_PATH):
    save_df(pd.DataFrame(columns=['username','pwd','role']), USER_PATH)

if not os.path.exists(NEW_PROJECT_PATH):
    save_df(pd.DataFrame(columns=ALL_FIELDS), NEW_PROJECT_PATH)

# 首次自动导入原始配置表
if not os.path.exists(HISTORY_PATH) and os.path.exists(SOURCE_CONFIG_PATH) and not os.path.exists(IMPORT_FLAG_PATH):
    src = pd.read_csv(SOURCE_CONFIG_PATH, encoding='utf-8-sig').fillna("")
    if "网站链接" in src.columns:
        src = src.rename(columns={"网站链接":"网址链接"})
    src["创建时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    src["处理状态"] = src.get("手册状态", "已归档").fillna("已归档")
    src["处理人"] = "admin"
    for c in ALL_FIELDS:
        if c not in src.columns:
            src[c] = ""
    src = src[ALL_FIELDS]
    save_df(src, HISTORY_PATH)
    with open(IMPORT_FLAG_PATH, "w") as f:
        f.write("ok")

if not os.path.exists(HISTORY_PATH):
    save_df(pd.DataFrame(columns=ALL_FIELDS), HISTORY_PATH)

# ===================== 登录 =====================
if 'login' not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ''
    st.session_state.role = ''

user_df = load_df(USER_PATH)
if 'admin' not in user_df['username'].values:
    admin = pd.DataFrame([{'username':'admin','pwd':sha256('123456'),'role':'管理员'}])
    save_df(admin, USER_PATH)

def login():
    st.markdown("## 🔐 登录系统")
    u = st.text_input('账号')
    p = st.text_input('密码', type='password')
    if st.button('登录', use_container_width=True):
        df = load_df(USER_PATH)
        row = df[df['username'] == u]
        if not row.empty and row.iloc[0]['pwd'] == sha256(p):
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = row.iloc[0]['role']
            st.rerun()
        else:
            st.error('账号或密码错误')

if not st.session_state.login:
    login()
    st.stop()

# ===================== 加载数据 =====================
hist_df = load_df(HISTORY_PATH)
new_df = load_df(NEW_PROJECT_PATH)

# 下拉选项
area_opts = get_options(hist_df, '售卖区域')
model_opts = get_options(hist_df, '产品型号版本')
converter_opts = get_options(hist_df, '变流单元类型')
trans_opts = get_options(hist_df, '变压器规格')
cab_opts = get_options(hist_df, '环网柜规格')
scc_opts = get_options(hist_df, 'SCC规格')

# ===================== 主界面 =====================
st.title('⚡ 储能项目手册料号申请及管理系统')
st.info(f'当前用户：{st.session_state.user}｜角色：{st.session_state.role}')
role = st.session_state.role

# ———————— 美化菜单 + 新增【首页】 ————————
menu = ['🏠 首页', '📥 提交新项目', '📚 历史项目库']
if role == '普通用户':
    menu += ['📄 我的提交']
else:
    menu += ['⚙️ 待审核项目', '📤 批量导入', '👥 用户管理']

page = st.sidebar.radio('**主菜单**', menu)

# ------------------------------
# 🏠 欢迎首页（新增）
# ------------------------------
if page == '🏠 首页':
    st.markdown(f"""
    <div class="welcome-card">
        <h1>欢迎回来，{st.session_state.user}！</h1>
        <p>储能项目手册料号申请及管理系统</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("历史项目总数", len(hist_df))
    with col2:
        st.metric("待审核项目", len(new_df[new_df['处理状态'] == '待审核']))
    with col3:
        st.metric("今日日期", datetime.now().strftime("%Y-%m-%d"))

    st.markdown("### 系统功能指南")
    st.info("""
    - 📥 **提交新项目**：申请储能项目手册料号（下拉可选历史，也可直接输入新项目参数）
    - 📚 **历史项目库**：查看、搜索、修改、删除历史项目
    - ⚙️ **待审核项目**：管理员审核料号申请
    - 📤 **批量导入**：批量导入项目数据
    - 👥 **用户管理**：账号权限管理
    """)

# ------------------------------
# 📥 提交新项目【已精简优化：单下拉组件支持选择+手动输入，删除右侧冗余输入框】
# ------------------------------
elif page == '📥 提交新项目':
    st.header('📥 提交新项目配置')
    st.caption('✅ 三列紧凑排版，下拉+自定义输入')
    with st.form('new_form'):
        c1,c2,c3 = st.columns(3)
        def set_field(col,field_name,option_list):
            with col:
                select_val = st.selectbox(field_name,option_list)
                input_val = st.text_input(f"{field_name}_手动填写",value=select_val).strip()
            return input_val

        # 第一排
        售卖区域 = set_field(c1,"售卖区域",area_opts)
        产品型号版本 = set_field(c2,"产品型号版本",model_opts)
        变流单元类型 = set_field(c3,"变流单元类型",converter_opts)
        # 第二排
        变压器规格 = set_field(c1,"变压器规格",trans_opts)
        环网柜规格 = set_field(c2,"环网柜规格",cab_opts)
        SCC规格 = set_field(c3,"SCC规格",scc_opts)

        st.divider()
        项目名称 = st.text_input('项目名称（必填）').strip()
        submit_btn = st.form_submit_button('✅ 提交新项目',use_container_width=True)
        if submit_btn:
            if not 项目名称:
                st.error('项目名称不能为空')
            else:
                data = {
                    '售卖区域':售卖区域,'产品型号版本':产品型号版本,'变流单元类型':变流单元类型,
                    '变压器规格':变压器规格,'环网柜规格':环网柜规格,'SCC规格':SCC规格,
                    '项目名称':项目名称,'手册料号':'','网址链接':'',
                    '创建时间':datetime.now().strftime('%Y-%m-%d %H:%M'),'处理状态':'待审核','处理人':st.session_state.user
                }
                new_df = load_df(NEW_PROJECT_PATH)
                new_df = pd.concat([new_df, pd.DataFrame([data])], ignore_index=True)
                save_df(new_df, NEW_PROJECT_PATH)
                st.success('提交成功，等待管理员审核')
# ------------------------------
# 📄 我的提交
# ------------------------------
elif page == '📄 我的提交' and role == '普通用户':
    st.header('📄 我提交的项目')
    df = load_df(NEW_PROJECT_PATH)
    mine = df[df['处理人'] == st.session_state.user]
    st.dataframe(mine, use_container_width=True)
    if not mine.empty:
        t = datetime.now().strftime("%Y%m%d%H%M")
        st.download_button('📥 导出Excel', to_excel(mine), f'我的提交_{t}.xlsx', use_container_width=True)

# ------------------------------
# ⚙️ 待审核项目
# ------------------------------
elif page == '⚙️ 待审核项目' and role == '管理员':
    st.header('⚙️ 待审核项目')
    todo = new_df[new_df['处理状态'] == '待审核']
    if todo.empty:
        st.success('暂无待审核项目')
        st.stop()

    st.dataframe(todo, use_container_width=True)
    t = datetime.now().strftime("%Y%m%d%H%M")
    st.download_button('📥 导出待审核', to_excel(todo), f'待审核_{t}.xlsx', use_container_width=True)

    idx = st.selectbox('选择项目', todo.index, format_func=lambda x: todo.loc[x,'项目名称'])
    item = todo.loc[idx]

    st.subheader('📌 项目信息')
    st.dataframe(pd.DataFrame([item]), use_container_width=True)

    st.subheader('🔍 最佳匹配')
    matches = []
    for _, h in hist_df.iterrows():
        r = match_rate(item, h)
        if r > 0:
            matches.append((r, h))
    matches.sort(reverse=True, key=lambda x:x[0])
    if matches:
        st.success(f'最佳匹配：{matches[0][0]}%')
        st.dataframe(pd.DataFrame([matches[0][1]]), use_container_width=True)
    else:
        st.warning('无匹配项目')

    col1, col2 = st.columns(2)
    if col1.button('🔗 借用最佳匹配', type='primary', use_container_width=True):
        if not matches:
            st.error('无匹配项')
        else:
            item['手册料号'] = matches[0][1]['手册料号']
            item['网址链接'] = matches[0][1]['网址链接']
            item['处理状态'] = '已借用'
            new_df2 = new_df.drop(idx)
            hist_df2 = pd.concat([hist_df, pd.DataFrame([item])], ignore_index=True)
            save_df(new_df2, NEW_PROJECT_PATH)
            save_df(hist_df2, HISTORY_PATH)
            st.success('已借用')
            st.rerun()

    if col2.button('✏️ 手动录入', type='secondary', use_container_width=True):
        st.session_state['edit_idx'] = idx
        st.rerun()

# 手动录入
if 'edit_idx' in st.session_state and role == '管理员':
    idx = st.session_state.edit_idx
    new_df = load_df(NEW_PROJECT_PATH)
    hist_df = load_df(HISTORY_PATH)
    if idx in new_df.index:
        st.header('✏️ 手动录入手册信息')
        item = new_df.loc[idx]
        pn = st.text_input('手册料号', item.get('手册料号', ''))
        url = st.text_input('网址链接', item.get('网址链接', ''))
        if st.button('保存并入库', use_container_width=True):
            item['手册料号'] = pn.strip()
            item['网址链接'] = url.strip()
            item['处理状态'] = '已手动录入'
            new_df2 = new_df.drop(idx)
            hist_df2 = pd.concat([hist_df, pd.DataFrame([item])], ignore_index=True)
            save_df(new_df2, NEW_PROJECT_PATH)
            save_df(hist_df2, HISTORY_PATH)
            del st.session_state['edit_idx']
            st.success('保存成功')
            st.rerun()

# ------------------------------
# 📤 批量导入
# ------------------------------
elif page == '📤 批量导入' and role == '管理员':
    st.header('📤 批量导入项目到历史库')
    uploaded = st.file_uploader('上传Excel/CSV', type=['xlsx','csv'])
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded, encoding='utf-8-sig').fillna("")
            else:
                df = pd.read_excel(uploaded).fillna("")

            need_cols = ['售卖区域','项目名称','产品型号版本','变流单元类型','变压器规格','环网柜规格','SCC规格']
            miss = [c for c in need_cols if c not in df.columns]
            if miss:
                st.error(f'缺少字段：{miss}')
            else:
                st.dataframe(df, use_container_width=True)
                if st.button('✅ 确认导入历史库', use_container_width=True):
                    df['创建时间'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    df['处理状态'] = '已批量导入'
                    df['处理人'] = st.session_state.user
                    for c in ALL_FIELDS:
                        if c not in df.columns:
                            df[c] = ''
                    df = df[ALL_FIELDS]
                    new_hist = pd.concat([hist_df, df], ignore_index=True)
                    save_df(new_hist, HISTORY_PATH)
                    st.success(f'导入成功 {len(df)} 条')
                    st.rerun()
        except Exception as e:
            st.error(f'导入失败：{str(e)}')

# ------------------------------
# 📚 历史项目库
# ------------------------------
elif page == '📚 历史项目库':
    st.header('📚 历史项目库（搜索/筛选/修改/删除/导出）')
    df = load_df(HISTORY_PATH)

    kw = st.text_input('🔍 搜索：名称/型号/料号/变压器/SCC等全字段')
    if kw:
        df = df[df.apply(lambda r: kw.lower() in ' '.join(r.astype(str)).lower(), axis=1)]

    with st.expander('高级筛选'):
        c1,c2,c3 = st.columns(3)
        areas = ['全部'] + [x for x in area_opts if x]
        models = ['全部'] + [x for x in model_opts if x]
        stats = ['全部'] + sorted([x for x in df['处理状态'].unique() if x])
        area = c1.selectbox('售卖区域', areas)
        model = c2.selectbox('产品型号', models)
        stat = c3.selectbox('处理状态', stats)
        if area != '全部':
            df = df[df['售卖区域'] == area]
        if model != '全部':
            df = df[df['产品型号版本'] == model]
        if stat != '全部':
            df = df[df['处理状态'] == stat]

    st.dataframe(df, use_container_width=True)
    t = datetime.now().strftime("%Y%m%d%H%M")
    if not df.empty:
        st.download_button('📥 导出Excel', to_excel(df), f'历史项目库_{t}.xlsx', use_container_width=True)

    if role == '管理员' and not df.empty:
        st.subheader('🛠️ 项目修改/删除')
        idx = st.selectbox('选择要操作的项目', df.index, format_func=lambda x: df.loc[x,'项目名称'])
        item = df.loc[idx].copy()

        with st.form('edit_form'):
            c1, c2 = st.columns(2)
            
            item['售卖区域'] = c1.selectbox('售卖区域', area_opts, index=area_opts.index(item['售卖区域']) if item['售卖区域'] in area_opts else 0)
            item['产品型号版本'] = c2.selectbox('产品型号版本', model_opts, index=model_opts.index(item['产品型号版本']) if item['产品型号版本'] in model_opts else 0)
            item['变流单元类型'] = c1.selectbox('变流单元类型', converter_opts, index=converter_opts.index(item['变流单元类型']) if item['变流单元类型'] in converter_opts else 0)
            item['变压器规格'] = c2.selectbox('变压器规格', trans_opts, index=trans_opts.index(item['变压器规格']) if item['变压器规格'] in trans_opts else 0)
            item['环网柜规格'] = c1.selectbox('环网柜规格', cab_opts, index=cab_opts.index(item['环网柜规格']) if item['环网柜规格'] in cab_opts else 0)
            item['SCC规格'] = c2.selectbox('SCC规格', scc_opts, index=scc_opts.index(item['SCC规格']) if item['SCC规格'] in scc_opts else 0)

            item['项目名称'] = c1.text_input('项目名称', item['项目名称'])
            item['手册料号'] = c2.text_input('手册料号', item['手册料号'])
            item['网址链接'] = c1.text_input('网址链接', item['网址链接'])

            current_status = item['处理状态']
            if current_status not in STATUS_OPTIONS:
                status_list = [current_status] + STATUS_OPTIONS
            else:
                status_list = STATUS_OPTIONS
            
            item['处理状态'] = c2.selectbox('处理状态', status_list, index=status_list.index(current_status))

            save_edit = st.form_submit_button('💾 保存修改', use_container_width=True)

        if save_edit:
            df.loc[idx] = item
            save_df(df, HISTORY_PATH)
            st.success('修改成功！')
            st.rerun()

        if st.button('🗑️ 删除此项目', type='secondary', use_container_width=True):
            df = df.drop(idx)
            save_df(df, HISTORY_PATH)
            st.warning('已删除')
            st.rerun()

        with st.expander('⚠️ 重置历史项目库（清空所有）'):
            if st.button('确认清空历史库（不可恢复）', use_container_width=True):
                save_df(pd.DataFrame(columns=ALL_FIELDS), HISTORY_PATH)
                st.warning('已清空历史库')
                st.rerun()

# ------------------------------
# 👥 用户管理
# ------------------------------
elif page == '👥 用户管理' and role == '管理员':
    st.header('👥 用户管理')
    df = load_df(USER_PATH)
    st.dataframe(df, use_container_width=True)

    st.subheader('新增用户')
    u = st.text_input('账号')
    p = st.text_input('密码')
    r = st.selectbox('角色', ['普通用户','管理员'])
    if st.button('添加用户', use_container_width=True):
        if u and p:
            new_row = {'username':u,'pwd':sha256(p),'role':r}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_df(df, USER_PATH)
            st.success('添加成功')
            st.rerun()
        else:
            st.error('账号密码不能为空')
