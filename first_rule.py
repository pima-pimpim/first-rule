# app.py
import io, gzip, json, requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Projects JSON (URL) → Dropdown & Tables", layout="wide")
st.title("🌐 โหลด JSON จาก URL แล้วแสดงข้อมูลเป็นตาราง")

url = st.text_input("ใส่ URL ของไฟล์ .json หรือ .json.gz", 
                    placeholder="เช่น https://raw.githubusercontent.com/username/repo/main/projects.json.gz")

load_btn = st.button("โหลดไฟล์จาก URL")

if not load_btn or not url:
    st.stop()

try:
    # ดึงข้อมูลจาก URL
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    # ตรวจชนิดไฟล์
    if url.lower().endswith(".gz"):
        data = json.load(gzip.GzipFile(fileobj=io.BytesIO(response.content)))
    else:
        data = response.json()

    st.success("โหลดข้อมูลสำเร็จ ✅")

except Exception as e:
    st.error(f"โหลดไฟล์ไม่สำเร็จ: {e}")
    st.stop()

# ------------------ แสดงข้อมูล ------------------
projects = data.get("projects", data)
if not isinstance(projects, list) or len(projects) == 0:
    st.warning("ไม่พบ 'projects' ใน JSON")
    st.stop()

df_all = pd.json_normalize(projects, sep=".")

labels, id_by_label = [], {}
for p in projects:
    pid = str(p.get("project_id", ""))
    title = str(p.get("title", "") or "")
    label = f"{pid} — {title}" if title else pid
    labels.append(label)
    id_by_label[label] = pid

choice = st.selectbox("เลือกโครงการ", labels, index=0)
selected_id = id_by_label[choice]

row_df = df_all[df_all["project_id"].astype(str) == str(selected_id)]
if row_df.empty:
    st.warning("ไม่พบ project_id ที่เลือก")
    st.stop()

row = row_df.iloc[0]
nested_cols = [c for c in row.index if c.endswith("similar_projects_by_title") or c.endswith("similar_projects_by_objective")]
base_cols = [c for c in row.index if c not in nested_cols]

kv_df = row[base_cols].to_frame(name="value").rename_axis("field").reset_index()
st.subheader("📋 ข้อมูลหลักของโครงการ")
st.dataframe(kv_df, use_container_width=True, height=360)

if "objective" in row.index and isinstance(row["objective"], str):
    st.text_area("📝 Objective (เต็ม)", row["objective"], height=200, label_visibility="collapsed")

# ตารางย่อย
def show_nested_table(nested_list, tag):
    st.subheader(f"🔎 Similar Projects — {tag}")
    if isinstance(nested_list, list) and len(nested_list):
        df_nested = pd.json_normalize(nested_list, sep=".")
        st.dataframe(df_nested, use_container_width=True, height=280)
    else:
        st.info("ไม่มีรายการ")

sel_obj = next((p for p in projects if str(p.get("project_id", "")) == selected_id), None)
if sel_obj:
    show_nested_table(sel_obj.get("similar_projects_by_title", []), "by title")
    show_nested_table(sel_obj.get("similar_projects_by_objective", []), "by objective")
