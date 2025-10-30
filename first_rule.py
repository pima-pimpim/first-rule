# app.py
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Projects JSON → Dropdown & Tables", layout="wide")
st.title("📁 เลือก Project ID แล้วแสดงข้อมูลเป็นตาราง")

# ---------- โหลด JSON ----------
col1, col2 = st.columns(2)
data = None

with col1:
    f = st.file_uploader("อัปโหลดไฟล์ JSON", type=["json"])
    if f:
        data = json.load(f)

with col2:
    txt = st.text_area("หรือวาง JSON ตรงนี้", height=220)
    if txt.strip():
        try:
            data = json.loads(txt)
        except Exception as e:
            st.error(f"อ่าน JSON ไม่ได้: {e}")

if data is None:
    st.info("อัปโหลดหรือวาง JSON ก่อนครับ")
    st.stop()

# ---------- ดึง list ของ projects ----------
projects = data.get("projects", data)  # เผื่อผู้ใช้ส่งเป็น list ตรง ๆ
if not isinstance(projects, list) or len(projects) == 0:
    st.warning("ไม่พบรายการ projects ใน JSON")
    st.stop()

# DataFrame สำหรับทำดรอปดาวน์และตารางหลัก
df_all = pd.json_normalize(projects, sep=".")

# ทำ label สำหรับดรอปดาวน์: "project_id — title"
labels = []
id_by_label = {}
for p in projects:
    pid = str(p.get("project_id", ""))
    title = str(p.get("title", ""))
    label = f"{pid} — {title}" if title else pid
    labels.append(label)
    id_by_label[label] = pid

choice = st.selectbox("เลือกโครงการ", labels, index=0)
selected_id = id_by_label[choice]

# ---------- เลือกแถวของโครงการนั้น ----------
row_df = df_all[df_all["project_id"].astype(str) == str(selected_id)]
if row_df.empty:
    st.warning("ไม่พบ project_id ที่เลือก")
    st.stop()

row = row_df.iloc[0]

# ---------- ตาราง Key–Value (ตัดคอลัมน์ลิสต์ย่อยออก) ----------
nested_cols = [c for c in row.index if c.endswith("similar_projects_by_title")
               or c.endswith("similar_projects_by_objective")]
base_cols = [c for c in row.index if c not in nested_cols]

kv_df = (
    row[base_cols]
    .to_frame(name="value")
    .rename_axis("field")
    .reset_index()
)

st.subheader("📋 ข้อมูลหลัก (Key–Value)")
st.dataframe(kv_df, use_container_width=True, height=360)

st.download_button(
    "⬇️ ดาวน์โหลดข้อมูลหลัก (CSV)",
    data=kv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"{selected_id}_main.csv",
    mime="text/csv"
)

# แสดง objective แบบอ่านง่าย
if "objective" in row.index and isinstance(row["objective"], str):
    st.markdown("**📝 Objective (เต็ม):**")
    st.text_area("Objective", row["objective"], height=200, label_visibility="collapsed")

# ---------- ตาราง Similar by Title ----------
st.subheader("🔎 Similar Projects — by Title")
sel_obj = next((p for p in projects if str(p.get("project_id","")) == str(selected_id)), None)

def show_nested_table(nested_list, title_fn):
    if isinstance(nested_list, list) and len(nested_list):
        df_nested = pd.json_normalize(nested_list, sep=".")
        st.dataframe(df_nested, use_container_width=True, height=280)
        st.download_button(
            f"⬇️ ดาวน์โหลด {title_fn} (CSV)",
            data=df_nested.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{selected_id}_{title_fn.replace(' ','_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("ไม่มีรายการ")

if sel_obj is None:
    st.info("ไม่พบรายละเอียดโครงการที่เลือกในโครงสร้างต้นฉบับ")
else:
    show_nested_table(sel_obj.get("similar_projects_by_title", []), "similar_by_title")

    st.subheader("🔎 Similar Projects — by Objective")
    show_nested_table(sel_obj.get("similar_projects_by_objective", []), "similar_by_objective")

# ---------- แสดงธง no_matches (ถ้ามี) ----------
if "no_matches" in row.index:
    st.markdown(f"**✅ no_matches:** `{row['no_matches']}`")