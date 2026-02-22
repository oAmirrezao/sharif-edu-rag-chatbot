# build_kb.py
import json, re, os, uuid
from bs4 import BeautifulSoup

DATA_DIR    = "./data"
OUTPUT_FILE = "chunks.json"
CHUNK_SIZE  = 250   # تعداد کلمات هر chunk
OVERLAP     = 50    # همپوشانی بین chunk‌ها

# ─────────────────────────────────────────────────────────────────
# نگاشت نام فایل → نام فارسی آیین‌نامه
# ─────────────────────────────────────────────────────────────────
FILE_NAMES = {
    "ai_etiquette.html":        "آداب‌نامه استفاده از ابزار هوش مصنوعی",
    "undergraduate_new.html":   "آیین‌نامه آموزشی دوره کارشناسی (ورودی ۱۴۰۲ و بعد)",
    "undergraduate_old.html":   "آیین‌نامه آموزشی دوره کارشناسی (ورودی ۱۴۰۱ و ماقبل)",
    "article_submission.html":  "آیین‌نامه ارسال مقاله به مجلات علمی و همایش‌ها",
    "exam_regulations.html":    "آیین‌نامه برگزاری و غیبت در امتحانات",
    "double_major.html":        "آیین‌نامه تحصیل همزمان در دو رشته (استعداد درخشان)",
    "teaching_assistant.html":  "آیین‌نامه دستیاری آموزشی",
    "coop.html":                "آیین‌نامه دوره کار و آموزش پایدار (کوآپ)",
    "minor.html":               "آیین‌نامه دوره‌های فرعی دانشگاه صنعتی شریف",
    "prerequisites.html":       "آیین‌نامه روابط پیش‌نیازی و همنیازی",
    "internship.html":          "آیین‌نامه کارآموزی",
    "internship_grade.html":    "دستورالعمل اخذ و ارائه نمره درس کارآموزی",
    "online_courses.html":      "دستورالعمل ارائه دروس به صورت غیرحضوری",
    "medical_absence.html":     "دستورالعمل بررسی موارد غیبت پزشکی در امتحان پایان‌ترم",
    "bachelor_project.html":    "دستورالعمل ثبت‌نام و ارائه نمره درس پروژه کارشناسی",
    "professor_referral.html":  "شرایط استفاده از معرفی به استاد",
    "guest_external.html":      "شرایط مهمانی دانشجویان شریف در دانشگاه‌های دولتی",
    "saipa_scholarship.html":   "شرایط و ضوابط پذیرش دانشجوی بورسیه گروه خودروسازی سایپا",
    "transfer.html":            "شیوه‌نامه انتقال به دانشگاه صنعتی شریف",
    "guest_internal.html":      "شیوه‌نامه مهمانی در دانشگاه صنعتی شریف",
    "course_equivalency.html":  "شیوه‌نامه پذیرش و تطبیق دروس دانشجویان مهمان، انتقالی، انصرافی و تغییر رشته",
    "change_major.html":        "قوانین تغییر رشته در آیین‌نامه آموزشی دوره کارشناسی",
    "military_exemption.html":  "قوانین و مقررات معافیت تحصیلی و مشوق‌های خدمتی",
    "olympiad_cr.html":         "لیست دروس قابل پذیرش (CR) برای دانشجویان مدال‌آور المپیاد",
    "graduation_deadline.html": "مهلت انجام امور فراغت از تحصیل",
    "academic_charter.html":    "نظام‌نامه آموزشی دانشگاه صنعتی شریف",
}

# ─────────────────────────────────────────────────────────────────
# الگوهای شناسایی ساختار آیین‌نامه
# ─────────────────────────────────────────────────────────────────
STRUCTURAL_PATTERN = re.compile(
    r'^(ماده\s*\d+|بند\s*\d+|تبصره\s*\d*|فصل\s*\d+|'
    r'بخش\s*\d+|الف[‌\s]|ب[‌\s]|ج[‌\s]|د[‌\s])'
)

# خطوطی که باید نادیده گرفته شوند (هدر/فوتر/منو)
SKIP_PATTERNS = re.compile(
    r'^(دانشگاه صنعتی شریف|مدیریت امور آموزشی|صفحه\s*\d+|'
    r'چاپ|بازگشت|منو|ورود|خروج|جستجو|آیین‌نامه‌ها و مقررات'
    r'|تمامی حقوق|©|https?://|www\.).*$',
    re.IGNORECASE
)


def normalize(text: str) -> str:
    """نرمال‌سازی متن فارسی"""
    # یکسان‌سازی کاراکترهای عربی/فارسی
    text = text.replace('ك', 'ک').replace('ي', 'ی')
    text = text.replace('\u200c', ' ')   # نیم‌فاصله → فاصله
    text = re.sub(r'\s+', ' ', text)     # فاصله‌های چندگانه
    text = re.sub(r'[_\-]{3,}', '', text)  # خط‌های جداکننده
    return text.strip()


def is_skip_line(line: str) -> bool:
    """آیا خط باید نادیده گرفته شود؟"""
    if len(line) < 3:
        return True
    if SKIP_PATTERNS.match(line):
        return True
    # خطوط عددی صرف (شماره صفحه)
    if re.match(r'^\d{1,3}$', line):
        return True
    return False


def make_chunk(text: str, reg_name: str, article_num: str = "") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "regulation_name": reg_name,
        "article_number": article_num,
        "text": normalize(text),
    }


def split_long_text(text: str, reg_name: str, article_num: str,
                    size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list:
    """تقسیم متن بلند با پنجره لغزنده"""
    words = text.split()
    if len(words) <= size:
        t = normalize(text)
        return [make_chunk(t, reg_name, article_num)] if len(t) > 20 else []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk_text = normalize(' '.join(words[start:end]))
        if len(chunk_text) > 20:
            chunks.append(make_chunk(chunk_text, reg_name, article_num))
        if end == len(words):
            break
        start += size - overlap
    return chunks


def parse_html(filepath: str, reg_name: str) -> list:
    """استخراج و chunking یک فایل HTML"""
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # حذف عناصر غیرمتنی
    for tag in soup.find_all(['header', 'footer', 'nav',
                               'script', 'style', 'noscript',
                               'iframe', 'button', 'form']):
        tag.decompose()

    # تلاش برای استخراج محتوای اصلی
    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', class_=re.compile(r'content|main|body', re.I)) or
        soup.find('body') or
        soup
    )

    lines = [
        l.strip()
        for l in main_content.get_text('\n').split('\n')
        if l.strip() and not is_skip_line(l.strip())
    ]

    all_chunks = []
    current_article = ""
    current_buf = []

    def flush():
        """ذخیره buffer فعلی به‌عنوان chunk"""
        if current_buf:
            joined = ' '.join(current_buf)
            all_chunks.extend(
                split_long_text(joined, reg_name, current_article)
            )

    for line in lines:
        is_structural = STRUCTURAL_PATTERN.match(line)

        if is_structural:
            flush()
            current_article = is_structural.group(0).strip()
            current_buf = [line]
        else:
            current_buf.append(line)
            # اگر buffer خیلی بزرگ شد، flush کن
            if len(' '.join(current_buf).split()) >= CHUNK_SIZE:
                flush()
                current_buf = []

    flush()  # آخرین buffer
    return all_chunks


# ─────────────────────────────────────────────────────────────────
# اجرای اصلی
# ─────────────────────────────────────────────────────────────────
def main():
    all_chunks = []
    missing = []

    for fname, rname in FILE_NAMES.items():
        fp = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fp):
            missing.append(fname)
            print(f"  [SKIP] فایل یافت نشد: {fname}")
            continue

        chs = parse_html(fp, rname)
        all_chunks.extend(chs)
        print(f"  ✅ {rname[:40]:<40} → {len(chs):>4} chunk")

    print(f"\n{'─'*60}")
    print(f"📦 مجموع chunks: {len(all_chunks)}")
    if missing:
        print(f"⚠️  فایل‌های گم‌شده ({len(missing)}): {', '.join(missing)}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"💾 ذخیره شد: {OUTPUT_FILE}")

    # آمار
    print(f"\n📊 آمار chunks به تفکیک آیین‌نامه:")
    from collections import Counter
    counts = Counter(c['regulation_name'] for c in all_chunks)
    for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   {cnt:>4}  {name}")


if __name__ == "__main__":
    main()
