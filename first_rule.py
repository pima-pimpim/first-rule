import io, gzip, json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Projects JSONs (.json/.json.gz) → Combined Table", layout="wide")
st.title("📁 รวมหลายไฟล์ JSON แล้วเลือก Project ID ดูข้อมูล")

# ---------- อัปโหลดหลายไฟล์ ----------
uploaded_files = st.file_uploader(
    "อัปโหลดไฟล์ JSON/JSON.GZ หลายไฟล์ (เลือกได้หลายไฟล์พร้อมกัน)",
    type=["json", "gz"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("โปรดอัปโหลดไฟล์ .json หรือ .json.gz อย่างน้อย 1 ไฟล์")
    st.stop()

# ---------- โหลดและรวมทุกไฟล์ ----------
projects_all = []
for up in uploaded_files:
    try:
        raw = up.read()
        name = up.name.lower()
        if name.endswith(".gz"):
            with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(raw.decode("utf-8"))

        # รองรับ {"projects":[...]} หรือ list โดยตรง
        projects = data.get("projects", data) if isinstance(data, dict) else data
        if isinstance(projects, list):
            projects_all.extend(projects)
    except Exception as e:
        st.error(f"อ่านไฟล์ {up.name} ไม่สำเร็จ: {e}")

if not projects_all:
    st.warning("ไม่พบข้อมูล projects ในไฟล์ที่อัปโหลด")
    st.stop()

st.success(f"รวมข้อมูลสำเร็จ ✅ จำนวนทั้งหมด {len(projects_all):,} projects")

# ---------- สร้าง DataFrame สำหรับ dropdown ----------
df_all = pd.json_normalize(projects_all, sep=".")

labels, id_by_label = [], {}
for p in projects_all:
    pid = str(p.get("project_id", ""))
    title = str(p.get("title", "") or "")
    label = f"{pid} — {title}" if title else pid
    labels.append(label)
    id_by_label[label] = pid

choice = st.selectbox("เลือกโครงการ", labels)
selected_id = id_by_label[choice]

# ---------- ดึงแถวที่เลือก ----------
row_df = df_all[df_all["project_id"].astype(str) == str(selected_id)]
if row_df.empty:
    st.warning("ไม่พบ project_id ที่เลือก")
    st.stop()

row = row_df.iloc[0]
nested_cols = [c for c in row.index if c.endswith("similar_projects_by_title") or c.endswith("similar_projects_by_objective")]
base_cols = [c for c in row.index if c not in nested_cols]
kv_df = row[base_cols].to_frame(name="value").rename_axis("field").reset_index()

st.subheader("📋 ข้อมูลหลัก (Key–Value)")
st.dataframe(kv_df, use_container_width=True, height=360)
st.download_button(
    "⬇️ ดาวน์โหลดข้อมูลหลัก (CSV)",
    data=kv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"{selected_id}_main.csv",
    mime="text/csv"
)

# ---------- Objective ----------
if "objective" in row.index and isinstance(row["objective"], str):
    st.markdown("**📝 Objective (เต็ม):**")
    st.text_area("Objective", row["objective"], height=200, label_visibility="collapsed")

# ---------- ตาราง Similar ----------
def show_nested_table(nested_list, key_suffix):
    if isinstance(nested_list, list) and len(nested_list):
        df_nested = pd.json_normalize(nested_list, sep=".")
        st.dataframe(df_nested, use_container_width=True, height=280)
    else:
        st.info("ไม่มีรายการ")

sel_obj = next((p for p in projects_all if str(p.get("project_id","")) == str(selected_id)), None)
st.subheader("🔎 Similar Projects — by Title")
show_nested_table(sel_obj.get("similar_projects_by_title", []) if sel_obj else [], "similar_by_title")

st.subheader("🔎 Similar Projects — by Objective")
show_nested_table(sel_obj.get("similar_projects_by_objective", []) if sel_obj else [], "similar_by_objective")

if "no_matches" in row.index:
    st.markdown(f"**✅ no_matches:** `{row['no_matches']}`")