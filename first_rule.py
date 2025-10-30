# app.py
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="JSON → Table with Dropdowns", layout="wide")
st.title("📄 JSON → Dropdown Filter → Table")

# -------- โหลด JSON --------
col1, col2 = st.columns(2)
data = None

with col1:
    f = st.file_uploader("อัปโหลดไฟล์ JSON", type=["json"])
    if f:
        data = json.load(f)

with col2:
    txt = st.text_area("หรือวาง JSON ที่นี่", height=160, placeholder='เช่น [{"date":"2025-10-01","cat":"A","value":10}, ...]')
    if txt.strip():
        try:
            data = json.loads(txt)
        except Exception as e:
            st.error(f"อ่าน JSON ไม่ได้: {e}")

if data is None:
    st.info("อัปโหลดหรือวาง JSON ก่อนนะ")
    st.stop()

# -------- แปลง JSON → DataFrame (รองรับ nested) --------
try:
    df = pd.json_normalize(data, sep=".")
except Exception:
    df = pd.DataFrame(data)

if df.empty:
    st.warning("ไม่พบข้อมูลที่แปลงเป็นตารางได้")
    st.stop()

# -------- helper: ทำค่าให้นับ unique ได้เสมอ --------
def _serialize_cell(x):
    # ทำให้ list/dict/set กลายเป็น string ที่เทียบเท่ากันได้
    if isinstance(x, (list, dict, set)):
        try:
            return json.dumps(x, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(x)
    return x

def safe_nunique(s: pd.Series) -> int:
    try:
        return s.nunique(dropna=True)
    except TypeError:
        return s.map(_serialize_cell).nunique(dropna=True)

def safe_unique_options(s: pd.Series):
    # คืนค่ารายการ option เป็น string ที่อ่านง่าย
    try:
        uniq = s.dropna().unique().tolist()
    except TypeError:
        uniq = s.dropna().map(_serialize_cell).unique().tolist()
    # แปลงเป็นสตริงสำหรับแสดงผลเสมอ (ไม่ทำให้ข้อมูลต้นทางเปลี่ยน)
    return sorted([str(u) for u in uniq])

# -------- แยกชนิดคอลัมน์ + พยายาม parse วันที่ --------
for c in df.columns:
    if df[c].dtype == "object":
        # parse datetime แบบไม่บังคับ
        try:
            df[c] = pd.to_datetime(df[c])
        except Exception:
            pass

num_cols = df.select_dtypes(include=["number", "float", "int"]).columns.tolist()
dt_cols  = df.select_dtypes(include=["datetime64[ns]","datetimetz"]).columns.tolist()
cat_cols = [c for c in df.columns if c not in num_cols + dt_cols]

st.subheader("🎚️ ตัวกรองด้วยดรอปดาวน์ (เลือกได้หลายอย่าง)")
with st.expander("ตั้งค่าตัวกรอง"):
    # ใช้ safe_nunique แทน .nunique ตรง ๆ
    default_filter_cols = []
    for c in cat_cols:
        try:
            if safe_nunique(df[c]) <= 100:
                default_filter_cols.append(c)
        except Exception:
            # ถ้ามีปัญหาใด ๆ ข้ามคอลัมน์นั้นไป
            continue
    default_filter_cols = default_filter_cols[:6]

    filter_cols = st.multiselect(
        "เลือกคอลัมน์สำหรับทำดรอปดาวน์",
        cat_cols,
        default=default_filter_cols,
        help="ควรเลือกคอลัมน์ที่มีจำนวนค่าจำเพาะไม่เยอะนัก (≤ ~100)"
    )

    # สร้างดรอปดาวน์ตามคอลัมน์ที่เลือก
    filters = {}
    flt_cols_layout = st.columns(min(3, max(1, len(filter_cols))))
    for i, c in enumerate(filter_cols):
        options = ["(ทั้งหมด)"] + safe_unique_options(df[c])
        with flt_cols_layout[i % len(flt_cols_layout)]:
            sel = st.multiselect(f"{c}", options=options, default="(ทั้งหมด)")
        filters[c] = sel

    # กรองช่วงวันที่ (ถ้ามีคอลัมน์วันที่)
    if dt_cols:
        st.markdown("**ช่วงวันที่ (ถ้ามีคอลัมน์วันที่ให้เลือก)**")
        date_col = st.selectbox("คอลัมน์วันที่", ["(ไม่ใช้)"] + dt_cols, index=0)
        if date_col != "(ไม่ใช้)":
            min_d, max_d = pd.to_datetime(df[date_col].min()), pd.to_datetime(df[date_col].max())
            d_range = st.date_input("เลือกช่วงวันที่", (min_d.date(), max_d.date()))
            if isinstance(d_range, tuple) and len(d_range) == 2:
                start_d, end_d = pd.to_datetime(d_range[0]), pd.to_datetime(d_range[1])
            else:
                start_d, end_d = min_d, max_d
        else:
            date_col = None
            start_d = end_d = None
    else:
        date_col = None
        start_d = end_d = None

# -------- นำตัวกรองไปใช้ --------
df_filtered = df.copy()

# กรองหมวดหมู่ (เทียบแบบสตริงเสมอ เพื่อให้ตรงกับตัวเลือก)
for c, sel in filters.items():
    if sel and "(ทั้งหมด)" not in sel:
        df_filtered = df_filtered[df_filtered[c].map(_serialize_cell).astype(str).isin(sel)]

# กรองวันที่
if date_col and start_d is not None and end_d is not None:
    df_filtered = df_filtered[
        (pd.to_datetime(df_filtered[date_col]) >= start_d) &
        (pd.to_datetime(df_filtered[date_col]) <= end_d)
    ]

# เลือกคอลัมน์ที่จะแสดง & จำกัดจำนวนแถว
st.subheader("📋 ตารางข้อมูล")
show_cols = st.multiselect("เลือกคอลัมน์ที่จะแสดง", df_filtered.columns.tolist(), default=df_filtered.columns.tolist()[:10])
limit = st.slider("จำกัดจำนวนแถวที่แสดง", 10, 5000, 500)

table_df = df_filtered[show_cols] if show_cols else df_filtered
st.dataframe(table_df.head(limit), use_container_width=True, height=420)

# ดาวน์โหลดผลลัพธ์
st.download_button(
    "⬇️ ดาวน์โหลดตาราง (CSV)",
    data=table_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_table.csv",
    mime="text/csv"
)
