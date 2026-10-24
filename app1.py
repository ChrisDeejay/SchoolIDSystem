import csv
import html
import io
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps

# ---------------- SCHOOL SETTINGS ----------------
BASE = Path(__file__).resolve().parent
PHOTOS = BASE / "student_photos"
DATABASE = BASE / "students.db"
PHOTOS.mkdir(exist_ok=True)

SCHOOL = "BETTER SEED INTERNATIONAL SCHOOL"
MOTTO = "Learning, Leading, Succeeding"
ADDRESS = "Kawuku Bwerenga Central or Nsambya-Gogonya"
PHONE1 = "0773018946"
PHONE2 = "0709 999708"
EMAIL = "betterseedinternational@gmail.com"

CLASSES = [
    "Senior One",
    "Senior Two",
    "Senior Three Arts",
    "Senior Three Science",
    "Senior Four Arts",
    "Senior Four Science",
]
SENIOR_FOUR = {"Senior Four Arts", "Senior Four Science"}

st.set_page_config(
    page_title="Better Seed School ID Manager",
    page_icon="🎓",
    layout="wide",
)


# ---------------- DATABASE ----------------
def db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con


def initialize_database():
    """Create the current table if needed and safely add missing columns."""
    with db() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE,
                index_no TEXT UNIQUE,
                full_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                gender TEXT NOT NULL,
                school_year TEXT NOT NULL,
                valid_until TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row[1] for row in con.execute("PRAGMA table_info(students)").fetchall()
        }
        migrations = {
            "student_id": "TEXT",
            "index_no": "TEXT",
            "gender": "TEXT NOT NULL DEFAULT 'Not specified'",
            "valid_until": "TEXT NOT NULL DEFAULT '2028-01-31'",
            "photo_path": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in columns:
                con.execute(f"ALTER TABLE students ADD COLUMN {column} {definition}")
        con.commit()


initialize_database()


def get_students(search=""):
    term = f"%{search.strip()}%"
    with db() as con:
        return con.execute(
            """
            SELECT id, student_id, index_no, full_name,
                   class_name, gender, school_year,
                   valid_until, photo_path
            FROM students
            WHERE full_name LIKE ?
               OR COALESCE(student_id, '') LIKE ?
               OR COALESCE(index_no, '') LIKE ?
               OR class_name LIKE ?
            ORDER BY full_name COLLATE NOCASE
            """,
            (term, term, term, term),
        ).fetchall()


def get_student(record_id):
    with db() as con:
        return con.execute(
            """
            SELECT id, student_id, index_no, full_name,
                   class_name, gender, school_year,
                   valid_until, photo_path
            FROM students WHERE id = ?
            """,
            (record_id,),
        ).fetchone()


def generate_student_id(con, year):
    """Generate the next permanent ID, e.g. BSIS/2026/00001."""
    prefix = f"BSIS/{year}/"
    rows = con.execute(
        "SELECT student_id FROM students WHERE student_id LIKE ?",
        (prefix + "%",),
    ).fetchall()
    highest = 0
    for row in rows:
        value = row[0] or ""
        try:
            highest = max(highest, int(value.rsplit("/", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"{prefix}{highest + 1:05d}"


def photo_data(path):
    if not path:
        return ""
    file = Path(path)
    if not file.is_file():
        return ""
    try:
        with Image.open(file) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((800, 1000))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90)
        import base64
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return ""


# ---------------- CARD DESIGN ----------------
def show_cards(student, school_name):
    # sqlite3.Row supports both positional and named access.
    rid = student[0]
    student_id = student[1]
    index_no = student[2]
    raw_name = student[3]
    raw_class = student[4]
    raw_gender = student[5]
    raw_year = student[6]
    raw_valid = student[7]
    photo = student[8]

    senior_four = raw_class in SENIOR_FOUR
    number_label = "INDEX NUMBER" if senior_four else "STUDENT ID"
    number = index_no if senior_four else student_id

    school = html.escape((school_name or SCHOOL).strip() or SCHOOL)
    name = html.escape(raw_name or "")
    class_name = html.escape(raw_class or "")
    gender = html.escape(raw_gender or "Not specified")
    year = html.escape(raw_year or "")
    valid = html.escape(raw_valid or "")
    number = html.escape(number or "NOT SET")
    photo64 = photo_data(photo)

    if photo64:
        student_photo = (
            f'<img class="student-photo" src="data:image/jpeg;base64,{photo64}" '
            f'alt="Student photo">'
        )
    else:
        student_photo = '<div class="student-photo photo-placeholder">STUDENT<br>PHOTO</div>'

    document = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0; padding: 12px; background: #f0f1f3;
          font-family: Arial, Helvetica, sans-serif; color: #25151a;
        }}
        .toolbar {{ text-align: center; font-size: 12px; margin-bottom: 12px; color: #34445a; }}
        .toolbar button {{
          padding: 9px 18px; background: #76172e; color: white; border: 0;
          border-radius: 5px; cursor: pointer; margin-top: 7px; font-weight: bold;
        }}
        .toolbar button:hover {{ background: #64172a; }}
        .cards {{ display: flex; flex-direction: column; align-items: center; gap: 16px; }}
        .card {{
          position: relative; overflow: hidden; isolation: isolate;
          width: 2.125in; height: 3.375in; flex: 0 0 auto;
          margin: 0 auto 12px; border: 1.5px solid #c7a34b; border-radius: 10px;
          background:
            radial-gradient(ellipse at top right, rgba(215,180,91,.14), transparent 42%),
            linear-gradient(145deg, #ffffff 0%, #fffdf7 100%);
          color: #25151a; page-break-after: always; break-after: page;
          -webkit-print-color-adjust: exact; print-color-adjust: exact;
        }}
        .gold-frame {{ position: absolute; inset: 7px; border: 1px solid #c7a34b; border-radius: 7px; pointer-events: none; z-index: 10; }}
        .gold-corner {{ position: absolute; width: 23px; height: 23px; border-color: #b58a2a; border-style: solid; pointer-events: none; z-index: 11; }}
        .gold-corner.top-left {{ top: 10px; left: 10px; border-width: 2px 0 0 2px; border-top-left-radius: 5px; }}
        .gold-corner.top-right {{ top: 10px; right: 10px; border-width: 2px 2px 0 0; border-top-right-radius: 5px; }}
        .gold-corner.bottom-left {{ bottom: 10px; left: 10px; border-width: 0 0 2px 2px; border-bottom-left-radius: 5px; }}
        .gold-corner.bottom-right {{ bottom: 10px; right: 10px; border-width: 0 2px 2px 0; border-bottom-right-radius: 5px; }}
        .front-content {{ position: relative; z-index: 1; text-align: center; padding: 12px 12px 43px; }}
        .school-header {{ display: flex; align-items: center; justify-content: center; gap: 7px; margin: 1px 2px 0; }}
        .crest-placeholder {{
          width: 42px; height: 42px; flex: 0 0 42px; border: 1.5px dashed #b58a2a;
          border-radius: 50%; background: #fffdf6; color: #96701e; display: flex;
          flex-direction: column; justify-content: center; align-items: center;
          text-align: center; font-size: 6.5px; font-weight: 800; line-height: 1.3;
        }}
        .school {{ color: #64172a; font-size: 10px; font-weight: 900; line-height: 1.15; letter-spacing: .2px; text-align: center; }}
        .motto {{ font-size: 6.5px; font-style: italic; color: #8b6a20; margin-top: 3px; }}
        .gold-divider {{ height: 2px; margin: 6px auto; width: 88%; background: linear-gradient(to right, transparent, #b58a2a, #ead9a4, #b58a2a, transparent); }}
        .id-title {{
          display: block; color: #fff; background: #76172e; border-radius: 2px;
          font-size: 7px; font-weight: bold; letter-spacing: 1.6px; padding: 5px 4px;
          margin: 0 4px 6px;
        }}
        .student-photo {{
          width: 1.02in; height: 1.10in; object-fit: cover; display: block;
          margin: 5px auto 5px; border: 2px solid #c7a34b; border-radius: 5px; background: #f5f0e3;
        }}
        .photo-placeholder {{ display: flex; align-items: center; justify-content: center; color: #8b6a20; font-size: 8px; font-weight: bold; }}
        .student-name {{ font-size: 10px; line-height: 1.15; font-weight: 900; color: #64172a; overflow-wrap: anywhere; text-transform: uppercase; margin: 3px 0 3px; }}
        .role {{ font-size: 5.5px; letter-spacing: 2px; margin: 2px; color: #8b6a20; font-weight: bold; }}
        .details {{ display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid #d8c99f; margin: 5px 3px 0; padding-top: 5px; }}
        .detail {{ min-width: 0; padding: 0 3px; }}
        .detail + .detail {{ border-left: 1px solid #d8c99f; }}
        .label {{ font-size: 6px; font-weight: bold; letter-spacing: .6px; color: #6d7480; }}
        .value {{ font-size: 7px; line-height: 1.2; font-weight: bold; margin-top: 3px; overflow-wrap: anywhere; }}
        .validity {{ font-size: 6.5px; letter-spacing: .5px; font-weight: bold; margin-top: 5px; color: #8b6a20; }}
        .number-band {{
          position: absolute; bottom: 0; left: 0; width: 100%; min-height: 0.34in;
          background: #76172e; border-top: 2px solid #c7a34b; color: white;
          display: flex; flex-direction: column; justify-content: center; align-items: center;
          padding: 4px 12px; z-index: 2;
        }}
        .number-label {{ font-size: 5.5px; letter-spacing: 1.3px; }}
        .number {{ font-size: 9px; font-weight: 900; letter-spacing: .7px; overflow-wrap: anywhere; text-align: center; }}
        .back-content {{ position: relative; z-index: 1; padding: 18px 16px 14px; }}
        .back-title {{ text-align: center; color: #64172a; font-size: 10px; font-weight: 900; line-height: 1.2; margin-top: 3px; }}
        .back-sub {{ text-align: center; font-size: 7px; font-style: italic; color: #8b6a20; margin-top: 4px; }}
        .terms-title {{ text-align: center; color: white; background: #76172e; font-size: 8px; font-weight: 900; letter-spacing: 1px; padding: 5px 3px; margin: 12px 1px 8px; }}
        .terms {{ font-size: 7.3px; line-height: 1.4; text-align: left; padding: 0 3px; }}
        .terms p {{ margin: 0 0 8px; }}
        .return {{ text-align: center; font-size: 6.5px; color: #8b6a20; font-weight: 900; margin-top: 8px; }}
        .contact {{
          position: absolute; z-index: 1; left: 16px; right: 16px; bottom: 16px;
          text-align: center; border-top: 1px solid #c7a34b; padding-top: 5px;
          font-size: 6.3px; font-weight: bold; line-height: 1.35; overflow-wrap: anywhere;
        }}
        .contact strong {{ color: #8b6a20; }}
        @page {{ size: auto; margin: 0.15in; }}
        @media print {{
          body {{ margin: 0; padding: 0; background: white; }}
          .toolbar {{ display: none !important; }}
          .cards {{ display: block; }}
          .card {{ margin: 0 auto; border-radius: 8px; }}
          * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        }}
      </style>
    </head>
    <body>
      <div class="toolbar">
        Front first, back second. Enable “Background graphics” when printing.
        <br><button onclick="window.print()">Print front and back</button>
      </div>
      <div class="cards">
        <section class="card">
          <div class="gold-frame"></div>
          <div class="gold-corner top-left"></div><div class="gold-corner top-right"></div>
          <div class="gold-corner bottom-left"></div><div class="gold-corner bottom-right"></div>
          <div class="front-content">
            <div class="school-header">
              <div class="crest-placeholder"><span>OFFICIAL</span><span>CREST</span></div>
              <div class="school">{school}</div>
            </div>
            <div class="motto">{html.escape(MOTTO)}</div>
            <div class="gold-divider"></div>
            <div class="id-title">STUDENT IDENTITY CARD</div>
            {student_photo}
            <div class="student-name">{name}</div>
            <div class="role">STUDENT</div>
            <div class="details">
              <div class="detail"><div class="label">CLASS</div><div class="value">{class_name.upper()}</div></div>
              <div class="detail"><div class="label">GENDER</div><div class="value">{gender.upper()}</div></div>
            </div>
            <div class="validity">SCHOOL YEAR {year} · VALID UNTIL {valid}</div>
          </div>
          <div class="number-band"><div class="number-label">{number_label}</div><div class="number">{number}</div></div>
        </section>

        <section class="card">
          <div class="gold-frame"></div>
          <div class="gold-corner top-left"></div><div class="gold-corner top-right"></div>
          <div class="gold-corner bottom-left"></div><div class="gold-corner bottom-right"></div>
          <div class="back-content">
            <div class="back-title">{school}</div>
            <div class="back-sub">{html.escape(MOTTO)}</div>
            <div class="gold-divider"></div>
            <div class="terms-title">TERMS AND CONDITIONS</div>
            <div class="terms">
              <p><b>Identification:</b><br>Carry this card while on school premises and present it when requested by authorised school staff.</p>
              <p><b>Proper use:</b><br>This card is for school-related purposes only. Do not lend, alter, copy, or misuse it.</p>
              <p><b>Lost or damaged card:</b><br>Report a lost or damaged card promptly to the school administration.</p>
              <p><b>Ownership:</b><br>This card remains the property of the school and must be returned when requested.</p>
            </div>
            <div class="return">IF FOUND, PLEASE RETURN TO THE SCHOOL</div>
          </div>
          <div class="contact">
            <strong>CONTACT THE SCHOOL</strong><br>
            {html.escape(ADDRESS)}<br>
            Tel: {html.escape(PHONE1)} / {html.escape(PHONE2)}<br>
            {html.escape(EMAIL)}
          </div>
        </section>
      </div>
    </body>
    </html>
    """
    components.html(document, height=790, scrolling=True)


# ---------------- APPLICATION ----------------
st.title("🎓 Better Seed International School")
st.subheader("Student ID Card Management System")
st.caption("Register students • Save local records • Print portrait ID cards")

with st.sidebar:
    st.header("School settings")
    school_name = st.text_input("School name", value=SCHOOL)
    st.info(
        "Student records and photos are stored on this computer. "
        "Back up students.db and the student_photos folder regularly."
    )

register_tab, records_tab, print_tab = st.tabs(
    ["Register Student", "Student Records", "Preview & Print"]
)

# ---------------- REGISTRATION ----------------
with register_tab:
    st.header("Register a student")
    with st.form("register_form", clear_on_submit=True):
        class_name = st.selectbox("Class", CLASSES)
        full_name = st.text_input("Student's full name *")
        gender = st.selectbox("Gender", ["Female", "Male", "Other / Not specified"])

        if class_name in SENIOR_FOUR:
            index_no = st.text_input("Senior Four index number *")
            student_id_input = ""
            st.caption("Senior Four Arts and Senior Four Science use a manually entered index number.")
        else:
            student_id_input = st.text_input(
                "Student identification number",
                help="Leave blank to generate the next ID automatically.",
            )
            index_no = ""
            st.caption("Leave blank to generate an ID such as BSIS/2026/00001.")

        school_year = st.text_input("School year", value=str(date.today().year))
        valid_until = st.date_input(
            "Card valid until",
            value=date(date.today().year + 1, 1, 31),
            min_value=date(2000, 1, 1),
        )
        uploaded_photo = st.file_uploader("Student photo *", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Save student", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not full_name.strip():
            errors.append("Enter the student's full name.")
        if not school_year.strip():
            errors.append("Enter the school year.")
        if class_name in SENIOR_FOUR and not index_no.strip():
            errors.append("Enter the Senior Four index number.")
        if uploaded_photo is None:
            errors.append("Upload a student photo.")

        if errors:
            for message in errors:
                st.error(message)
        else:
            photo_path = None
            try:
                uploaded_photo.seek(0)
                with Image.open(uploaded_photo) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    image.thumbnail((1200, 1600))
                    photo_path = PHOTOS / f"{uuid.uuid4().hex}.jpg"
                    image.save(photo_path, "JPEG", quality=90)

                with db() as con:
                    if class_name in SENIOR_FOUR:
                        con.execute(
                            """
                            INSERT INTO students
                            (student_id, index_no, full_name, class_name, gender,
                             school_year, valid_until, photo_path)
                            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (index_no.strip(), full_name.strip(), class_name, gender,
                             school_year.strip(), valid_until.isoformat(), str(photo_path)),
                        )
                        saved_number = index_no.strip()
                        number_type = "Index number"
                    else:
                        student_id = student_id_input.strip()
                        if not student_id:
                            student_id = generate_student_id(con, school_year.strip())
                        con.execute(
                            """
                            INSERT INTO students
                            (student_id, index_no, full_name, class_name, gender,
                             school_year, valid_until, photo_path)
                            VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
                            """,
                            (student_id, full_name.strip(), class_name, gender,
                             school_year.strip(), valid_until.isoformat(), str(photo_path)),
                        )
                        saved_number = student_id
                        number_type = "Student ID"

                st.success("Student saved successfully!")
                st.write(f"{number_type}: **{saved_number}**")
                st.info("Open Preview & Print to print the student's card.")

            except sqlite3.IntegrityError:
                if photo_path and photo_path.exists():
                    photo_path.unlink()
                st.error("That student ID or index number already exists. Check the number.")
            except Exception as error:
                if photo_path and photo_path.exists():
                    photo_path.unlink()
                st.error(f"Could not save student: {error}")


# ---------------- STUDENT RECORDS ----------------
with records_tab:
    st.header("Student records")
    search = st.text_input("Search by name, student ID, index number or class")
    rows = get_students(search)
    st.write(f"Records found: {len(rows)}")

    if rows:
        st.dataframe(
            [
                {
                    "Record": row["id"],
                    "Student ID": row["student_id"] or "",
                    "Index number": row["index_no"] or "",
                    "Full name": row["full_name"],
                    "Class": row["class_name"],
                    "Gender": row["gender"],
                    "School year": row["school_year"],
                    "Valid until": row["valid_until"],
                }
                for row in rows
            ],
            use_container_width=True,
            hide_index=True,
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Record", "Student ID", "Index number", "Full name", "Class",
            "Gender", "School year", "Valid until",
        ])
        for row in rows:
            writer.writerow([
                row["id"], row["student_id"] or "", row["index_no"] or "",
                row["full_name"], row["class_name"], row["gender"],
                row["school_year"], row["valid_until"],
            ])

        st.download_button(
            "Export records to CSV",
            data=buffer.getvalue().encode("utf-8-sig"),
            file_name="school_student_records.csv",
            mime="text/csv",
        )
    else:
        st.info("No student records found.")


# ---------------- PREVIEW AND PRINT ----------------
with print_tab:
    st.header("Preview and print ID card")
    rows = get_students()
    if not rows:
        st.info("Register a student first.")
    else:
        options = {
            f"{row['full_name']} — {row['class_name']} — "
            f"{row['index_no'] if row['class_name'] in SENIOR_FOUR else row['student_id']}": row["id"]
            for row in rows
        }
        selected = st.selectbox("Select student", list(options.keys()))
        student = get_student(options[selected])
        if student:
            st.caption(
                "The front is shown first and the back second. "
                "Test the dimensions on ordinary paper before using card stock."
            )
            show_cards(student, school_name)

st.divider()
st.caption("Better Seed International School • Local student ID card system • No QR code")
