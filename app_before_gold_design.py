
import base64
import csv
import html
import io
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import qrcode
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps

# ---------------- SCHOOL SETTINGS ----------------
BASE = Path(__file__).parent
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
    return sqlite3.connect(DATABASE)


def initialize_database():
    with db() as con:
        con.execute("""
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
        """)

        # Add missing columns if opening an older version
        # of this project.
        columns = {
            row[1]
            for row in con.execute(
                "PRAGMA table_info(students)"
            ).fetchall()
        }

        # Preserve existing records from the first prototype.
        migrations = {
            "student_id": "TEXT",
            "index_no": "TEXT",
            "gender": "TEXT NOT NULL DEFAULT 'Not specified'",
            "valid_until": "TEXT NOT NULL DEFAULT '2028-01-31'",
        }

        for column, definition in migrations.items():
            if column not in columns:
                con.execute(
                    f"ALTER TABLE students ADD COLUMN {column} {definition}"
                )


initialize_database()


def get_students(search=""):
    term = f"%{search.strip()}%"
    with db() as con:
        return con.execute("""
            SELECT id, student_id, index_no, full_name,
                   class_name, gender, school_year,
                   valid_until, photo_path
            FROM students
            WHERE full_name LIKE ?
               OR COALESCE(student_id, '') LIKE ?
               OR COALESCE(index_no, '') LIKE ?
            ORDER BY full_name COLLATE NOCASE
        """, (term, term, term)).fetchall()


def get_student(record_id):
    with db() as con:
        return con.execute("""
            SELECT id, student_id, index_no, full_name,
                   class_name, gender, school_year,
                   valid_until, photo_path
            FROM students WHERE id = ?
        """, (record_id,)).fetchone()


def generate_student_id(con):
    # IDs are generated and saved permanently.
    # Example: BSIS/2026/00001
    prefix = f"BSIS/{date.today().year}/"
    rows = con.execute(
        "SELECT student_id FROM students WHERE student_id LIKE ?",
        (prefix + "%",)
    ).fetchall()

    highest = 0
    for row in rows:
        value = row[0] or ""
        try:
            highest = max(highest, int(value.rsplit("/", 1)[1]))
        except (ValueError, IndexError):
            pass

    return f"{prefix}{highest + 1:05d}"


# ---------------- QR CODE ----------------
def make_qr(student):
    record_id, student_id, index_no, name, class_name, gender, year, valid, photo = student

    number = index_no if class_name in SENIOR_FOUR else student_id
    contents = (
        f"School: {SCHOOL}\n"
        f"Record ID: {record_id}\n"
        f"Name: {name}\n"
        f"Class: {class_name}\n"
        f"Number: {number or ''}\n"
        f"Valid until: {valid}"
    )

    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(contents)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def photo_data(path):
    file = Path(path)
    if not file.exists():
        return ""

    try:
        with Image.open(file) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((800, 1000))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90)

        return base64.b64encode(buffer.getvalue()).decode()
    except Exception:
        return ""


# ---------------- CARD DESIGN ----------------
def show_cards(student, school_name):
    rid, student_id, index_no, name, class_name, gender, year, valid, photo = student

    senior_four = class_name in SENIOR_FOUR
    number_label = "INDEX NUMBER" if senior_four else "STUDENT ID"
    number = index_no if senior_four else student_id

    school = html.escape(school_name.strip() or SCHOOL)
    name = html.escape(name)
    class_name = html.escape(class_name)
    gender = html.escape(gender)
    valid = html.escape(valid)
    number = html.escape(number or "NOT SET")

    photo64 = photo_data(photo)
    if photo64:
        student_photo = (
            f'<img class="photo" '
            f'src="data:image/jpeg;base64,{photo64}">'
        )
    else:
        student_photo = (
            '<div class="photo placeholder">STUDENT PHOTO</div>'
        )


    document = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0; padding: 12px; background: #eee;
        font-family: Arial, sans-serif; color: #25151a;
      }}
      .toolbar {{
        text-align: center; font-size: 12px;
        margin-bottom: 12px;
      }}
      button {{
        padding: 9px 18px; background: #76172e;
        color: white; border: 0; border-radius: 4px;
        cursor: pointer; margin-top: 7px;
      }}
      .card {{
        position: relative; overflow: hidden;
        width: 2.125in; height: 3.375in;
        margin: 0 auto 16px; background: #fffdfd;
        border: 1px solid #76172e; border-radius: 0.12in;
        page-break-after: always; break-after: page;
      }}
      .band {{
        height: 0.19in; background: #76172e;
        border-bottom: 2px solid #c5a269;
      }}
      .front {{ text-align: center; padding: 0.08in 0.10in;}}
      .crest {{
        margin: 0 auto 2px; width: 0.34in; height: 0.34in;
        border: 2px solid #76172e; border-radius: 50%;
        display: flex; justify-content: center; align-items: center;
        color: #76172e; font-weight: bold; font-size: 8px;
      }}
      .school {{
       color: #64172a; font-size: 11px;
    font-weight: 900; line-height: 1.15;
      }}
      .school-sub {{
        font-size: 6px; font-weight: bold; letter-spacing: 2px;
      }}
      .motto {{
        font-size: 6px; font-style: italic;
        color: #8b3a4c; margin-top: 2px;
      }}
      .id-title {{
        display: inline-block; color: #76172e;
        font-size: 7px; font-weight: bold; letter-spacing: 2px;
        border-bottom: 1px solid #c5a269; padding: 2px 12px;
      }}
      .photo {{
        width: 1.12in;
    height: 1.25in;
    object-fit: cover;
    border: 2px solid #76172e;
    border-radius: 0.08in;
    display: block;
    margin: 0.08in auto;
      }}
      .placeholder {{
        display: flex; justify-content: center; align-items: center;
        font-size: 7px; color: #777; background: #eee;
      }}
      .student-name {{
        font-size: 10px;
    font-weight: 900;
    color: #64172a;
    white-space: normal;
    overflow-wrap: anywhere;
    text-transform: uppercase;
      }}
      .role {{ font-size: 5px; letter-spacing: 3px; margin: 2px; }}
      .details {{
        display: grid;
    grid-template-columns: 1fr 1fr;
    border-top: 1px solid #c7bfc2;
    margin: 0.06in 4px 0;
    padding-top: 0.06in;
      }}
      .detail + .detail {{ border-left: 1px solid #c7bfc2; }}
      .label {{
        font-size: 7px; font-weight: bold; letter-spacing: 1px;
        color: #294655;
      }}
      .value {{
        font-size: 8px; font-weight: bold; margin-top: 2px;
      }}
      .validity {{
        font-size: 6px; letter-spacing: 1px;
        font-weight: bold; margin-top: 3px;
      }}
      .number-band {{
        position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 0.32in;
    background: #76172e;
    border-top: 2px solid #c5a269;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
      }}
      .number-label {{ font-size: 5px; letter-spacing: 1.5px; }}
      .number {{ font-size: 9px;
    font-weight: 900;
    letter-spacing: 1px; }}
      .back {{  padding: 0.12in 0.16in 0.16in; }}
      .back-title {{text-align: center;
    color: #64172a;
    font-size: 10px;
    font-weight: 900;
    line-height: 1.2;
      }}
      .back-sub {{  text-align: center;
    font-size: 7px;
    font-weight: bold;
    margin-top: 3px; }}
      .terms-title {{
         text-align: center;
    font-size: 10px;
    font-weight: 900;
    margin: 0.12in 0 0.10in;
      }}
      .terms {{ font-size: 8px;
    line-height: 1.4;
    text-align: left; }}
      .terms p {{ margin: 0 0 0.12in; }}
      .return {{
         text-align: center;
    font-size: 7px;
    color: #76172e;
    font-weight: bold;
    margin-top: 0.10in;
      }}
      .contact {{
         text-align: center;
    font-size: 7px;
    font-weight: bold;
    font-style: italic;
    line-height: 1.4;
    margin-top: 0.06in;
      }}
      .qr {{ width: 0.38in; height: 0.38in; float: right; margin: 2px; }}
      .bottom-band {{
        position: absolute; bottom: 0; height: 0.10in;
        width: 100%; background: #76172e;
        border-top: 2px solid #c5a269;
      }}
      @page {{ size: auto; margin: 0.15in; }}
      @media print {{
        body {{ margin: 0; padding: 0; background: white; }}
        .toolbar {{ display: none; }}
        .card {{ margin: 0 auto; border-radius: 0.08in; }}
        * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      }}
    </style>
    </head>
    <body>
      <div class="toolbar">
        Front first, back second. Enable background graphics when printing.
        <br><button onclick="window.print()">Print front and back</button>
      </div>

      <section class="card">
        <div class="band"></div>
        <div class="front">
          <div class="crest">BSIS</div>
          <div class="school">{school}</div>
          <div class="school-sub">INTERNATIONAL SCHOOL</div>
          <div class="motto">{html.escape(MOTTO)}</div>
          <div class="id-title">STUDENT ID</div>
          {student_photo}
          <div class="student-name">{name}</div>
          <div class="role">STUDENT</div>
          <div class="details">
            <div class="detail">
              <div class="label">CLASS</div>
              <div class="value">{class_name.upper()}</div>
            </div>
            <div class="detail">
              <div class="label">GENDER</div>
              <div class="value">{gender.upper()}</div>
            </div>
          </div>
          <div class="validity">VALID UNTIL {valid.upper()}</div>
        </div>
        <div class="number-band">
          <div class="number-label">{number_label}</div>
          <div class="number">{number}</div>
        </div>
      </section>

     
<section class="card">
  <div class="band"></div>
  <div class="back">
    <div class="back-title">{school}</div>
    <div class="back-sub">STUDENT ID CARD</div>

    <div class="terms-title">TERMS AND CONDITIONS</div>

    <div class="terms">
      <p>
        <b>Identification:</b><br>
        Students are required to carry their school ID at all times
        while on campus. The ID should be worn visibly or kept readily
        available to confirm identity when requested by school staff.
      </p>

      <p>
        <b>Proper Use:</b><br>
        The student ID is issued strictly for school-related purposes.
        It must not be shared, lent to others, duplicated, or used for
        any unauthorized activities.
      </p>

      <p>
        <b>Security:</b><br>
        In case the ID is lost, misplaced, or suspected to be misused,
        it must be reported immediately to the school administration
        so appropriate action can be taken.
      </p>
    </div>

    <div class="return">
      IF FOUND, PLEASE RETURN TO THE ADDRESS BELOW
    </div>

    <div class="contact">
      {school}<br>
      {html.escape(ADDRESS)}<br>
      {html.escape(PHONE1)} / {html.escape(PHONE2)}<br>
      {html.escape(EMAIL)}
    </div>
  </div>
  <div class="bottom-band"></div>
</section>

    </body>
    </html>
    """

    components.html(document, height=650, scrolling=True)


# ---------------- APPLICATION ----------------
st.title("🎓 Better Seed International School")
st.subheader("Student ID Card Management System")
st.caption("Register students • Save records • Generate QR codes • Print IDs")

with st.sidebar:
    st.header("School settings")
    school_name = st.text_input("School name", value=SCHOOL)
    st.info("Student records and photos are stored on this computer. Back up your project folder regularly.")

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
            st.caption("Senior Four cards display the manually entered index number.")
        else:
            student_id_input = st.text_input(
                "Student identification number",
                help="Leave blank to generate it automatically."
            )
            index_no = ""
            st.caption("Leave the number blank to generate a unique student ID.")

        school_year = st.text_input("School year", value=str(date.today().year))
        valid_until = st.date_input(
            "Card valid until",
            value=date(date.today().year + 1, 1, 31),
            min_value=date(2000, 1, 1)
        )
        uploaded_photo = st.file_uploader(
            "Student photo *", type=["jpg", "jpeg", "png"]
        )
        submitted = st.form_submit_button(
            "Save student", type="primary", use_container_width=True
        )

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
                        con.execute("""
                            INSERT INTO students
                            (student_id, index_no, full_name, class_name,
                             gender, school_year, valid_until, photo_path)
                            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            index_no.strip(), full_name.strip(), class_name,
                            gender, school_year.strip(), valid_until.isoformat(),
                            str(photo_path)
                        ))
                    else:
                        student_id = student_id_input.strip()
                        if not student_id:
                            student_id = generate_student_id(con)

                        con.execute("""
                            INSERT INTO students
                            (student_id, index_no, full_name, class_name,
                             gender, school_year, valid_until, photo_path)
                            VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
                        """, (
                            student_id, full_name.strip(), class_name,
                            gender, school_year.strip(), valid_until.isoformat(),
                            str(photo_path)
                        ))

                st.success("Student saved successfully!")
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
    search = st.text_input("Search by name, student ID or index number")
    rows = get_students(search)

    st.write(f"Records found: {len(rows)}")

    if rows:
        st.dataframe([
            {
                "Record": r[0],
                "Student ID": r[1] or "",
                "Index number": r[2] or "",
                "Full name": r[3],
                "Class": r[4],
                "Gender": r[5],
                "School year": r[6],
                "Valid until": r[7],
            }
            for r in rows
        ], use_container_width=True, hide_index=True)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Record", "Student ID", "Index number", "Full name",
            "Class", "Gender", "School year", "Valid until"
        ])
        for r in rows:
            writer.writerow([
                r[0], r[1] or "", r[2] or "", r[3],
                r[4], r[5], r[6], r[7]
            ])

        st.download_button(
            "Export records to CSV",
            data=buffer.getvalue().encode("utf-8-sig"),
            file_name="school_student_records.csv",
            mime="text/csv"
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
            f"{r[3]} — {r[4]} — {r[2] if r[4] in SENIOR_FOUR else r[1]}": r[0]
            for r in rows
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
st.caption(
    "Better Seed International School • Local prototype. "
    "QR codes contain student details and are not an official identity verification service."
)
