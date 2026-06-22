import re


VALID_TRINH_DO = {"A", "B", "C", "D"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_vdv_form(form):
    ten_vdv = (form.get("ten_vdv") or "").strip()
    email = (form.get("email") or "").strip().lower()
    trinh_do = (form.get("trinh_do") or "C").strip().upper()
    ghi_chu = (form.get("ghi_chu") or "").strip()

    errors = []
    if not ten_vdv:
        errors.append("Tên VĐV không được để trống.")
    if not email:
        errors.append("Email không được để trống.")
    elif not EMAIL_RE.match(email):
        errors.append("Email không đúng định dạng.")
    if trinh_do not in VALID_TRINH_DO:
        errors.append("Trình độ chỉ được chọn A, B, C hoặc D.")

    data = {
        "ten_vdv": ten_vdv,
        "email": email,
        "trinh_do": trinh_do if trinh_do in VALID_TRINH_DO else "C",
        "ghi_chu": ghi_chu,
    }
    return data, errors
