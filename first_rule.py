# app.py
import io
import json
import gzip
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Projects JSON (.json/.json.gz) → Dropdown & Tables", layout="wide")
st.title("📁 เลือก Project ID แล้วแสดงข้อมูลเป็นตาราง")

# ---------- อัปโหลดไฟล์ (รองรับ .json และ .json.gz) ----------
uploaded = st.file_uploader("อัปโหลดไฟล์ JSON หรือ JSON.GZ", type=["json", "gz"])

data = None
if uploaded:
    with st.spinner("กำลังอ่านไฟล์..."):
        try:
            # ใช้ชื่อไฟล์ตัดสินใจวิธีอ่าน
            name = uploaded.name.lower()
            raw = uploaded.read()  # อ่านครั้งเดียว
            if name.endswith(".gz"):
                # ไฟล์บีบอัด: เปิดผ่าน gzip จากบัฟเฟอร์
                with gzip.open(io.BytesIO(raw), mode="rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                # ไฟล์ .json ปกติ: โหลดจากบัฟเฟอร์โดยตรง
                data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

if data is None:
    st.info("อัปโหลดไฟล์ .json หรือ .json.gz เพื่อเริ่มต้น")
    st.stop()

# ---------- ดึง list ของ projects ----------
# รองรับทั้งโครงสร้าง {"projects":[...]} และ list โดยตรง
projects = data.get("projects", data) if isinstance(data, dict) else data
if not isinstance(projects, list) or len(projects) == 0:
    st.warning("ไม่พบรายการ projects ใน JSON")
    st.stop()

# DataFrame รวมสำหรับใช้ทำดรอปดาวน์และค้นหาแถว
df_all = pd.json_normalize(projects, sep=".")

# ---------- ทำ dropdown เลือก project ----------
labels = []
id_by_label = {}
for p in projects:
    pid = str(p.get("project_id", ""))
    title = str(p.get("title", ""))
    label = f"{pid} — {title}" if title else pid
    labels.append(label)
    id_by_label[label] = pid

choice = st.selectbox("เลือกโครงการ (project_id — title)", labels, index=0)
selected_id = id_by_label[choice]

# ---------- แถวที่เลือก ----------
row_df = df_all[df_all["project_id"].astype(str) == str(selected_id)]
if row_df.empty:
    st.warning("ไม่พบ project_id ที่เลือก")
    st.stop()

row = row_df.iloc[0]

# ---------- ตาราง Key–Value (ไม่รวมตารางย่อย) ----------
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

# ---------- แสดง objective เต็ม ----------
if "objective" in row.index and isinstance(row["objective"], str):
    st.markdown("**📝 Objective (เต็ม):**")
    st.text_area("Objective", row["objective"], height=200, label_visibility="collapsed")

# ---------- ตาราง Similar Projects ----------
def show_nested_table(nested_list, key_suffix):
    if isinstance(nested_list, list) and len(nested_list):
        df_nested = pd.json_normalize(nested_list, sep=".")
        st.dataframe(df_nested, use_container_width=True, height=280)
        st.download_button(
            f"⬇️ ดาวน์โหลด {key_suffix} (CSV)",
            data=df_nested.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{selected_id}_{key_suffix}.csv",
            mime="text/csv"
        )
    else:
        st.info("ไม่มีรายการ")

# หา object ต้นฉบับที่เลือก (เพื่อเข้าถึงลิสต์ย่อยแบบไม่ flatten)
sel_obj = next((p for p in projects if str(p.get("project_id","")) == str(selected_id)), None)

st.subheader("🔎 Similar Projects — by Title")
show_nested_table(sel_obj.get("similar_projects_by_title", []) if sel_obj else [], "similar_by_title")

st.subheader("🔎 Similar Projects — by Objective")
show_nested_table(sel_obj.get("similar_projects_by_objective", []) if sel_obj else [], "similar_by_objective")

# ---------- ธง no_matches (ถ้ามี) ----------
if "no_matches" in row.index:
    st.markdown(f"**✅ no_matches:** `{row['no_matches']}`")