import re


VALID_TRINH_DO = {"A", "B", "C", "D"}
VALID_LOAI_DAU = {"don", "doi"}
VALID_LOAI_THANH_VIEN = {"co_dinh", "vang_lai"}
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


def _parse_int_field(value, default, minimum=None, maximum=None):
    raw = (str(value).strip() if value is not None else "")
    if raw == "":
        number = default
    else:
        number = int(raw)
    if minimum is not None and number < minimum:
        number = minimum
    if maximum is not None and number > maximum:
        number = maximum
    return number


def _parse_money_field(value):
    return _parse_int_field(value, 0, minimum=0)


def normalize_tournament_form(form):
    errors = []
    ten_giai_dau = (form.get("ten_giai_dau") or "").strip()
    dia_diem = (form.get("dia_diem") or "").strip()
    thoi_gian_bat_dau = (form.get("thoi_gian_bat_dau") or "").strip() or None
    loai_dau = (form.get("loai_dau") or "don").strip()

    if not ten_giai_dau:
        errors.append("Tên giải không được để trống.")
    if loai_dau not in VALID_LOAI_DAU:
        errors.append("Hình thức thi đấu không hợp lệ.")
        loai_dau = "don"

    numeric_fields = {}
    try:
        numeric_fields["so_luong_san"] = _parse_int_field(form.get("so_luong_san"), 1, minimum=1)
        numeric_fields["so_nguoi_du_kien"] = _parse_int_field(form.get("so_nguoi_du_kien"), 10, minimum=1)
        numeric_fields["diem_cham"] = _parse_int_field(form.get("diem_cham"), 11, minimum=1, maximum=99)
        numeric_fields["diem_toi_da"] = _parse_int_field(form.get("diem_toi_da"), 15, minimum=1, maximum=99)
        numeric_fields["chi_phi_san_bai"] = _parse_money_field(form.get("chi_phi_san_bai"))
        numeric_fields["chi_phi_nuoc_noi"] = _parse_money_field(form.get("chi_phi_nuoc_noi"))
        numeric_fields["chi_phi_giai_thuong"] = _parse_money_field(form.get("chi_phi_giai_thuong"))
        numeric_fields["chi_phi_khac"] = _parse_money_field(form.get("chi_phi_khac"))
        numeric_fields["ty_le_giai_1"] = _parse_int_field(form.get("ty_le_giai_1"), 5, minimum=0)
        numeric_fields["ty_le_giai_2"] = _parse_int_field(form.get("ty_le_giai_2"), 3, minimum=0)
        numeric_fields["ty_le_giai_3"] = _parse_int_field(form.get("ty_le_giai_3"), 2, minimum=0)
    except ValueError:
        errors.append("Các trường số chỉ được nhập số hợp lệ.")
        numeric_fields = {
            "so_luong_san": 1,
            "so_nguoi_du_kien": 10,
            "diem_cham": 11,
            "diem_toi_da": 15,
            "chi_phi_san_bai": 0,
            "chi_phi_nuoc_noi": 0,
            "chi_phi_giai_thuong": 0,
            "chi_phi_khac": 0,
            "ty_le_giai_1": 5,
            "ty_le_giai_2": 3,
            "ty_le_giai_3": 2,
        }

    if numeric_fields["diem_toi_da"] < numeric_fields["diem_cham"]:
        errors.append("Max điểm phải lớn hơn hoặc bằng điểm chạm.")
        numeric_fields["diem_toi_da"] = numeric_fields["diem_cham"]

    data = {
        "ten_giai_dau": ten_giai_dau,
        "dia_diem": dia_diem,
        "thoi_gian_bat_dau": thoi_gian_bat_dau,
        "loai_dau": loai_dau,
        **numeric_fields,
    }
    return data, errors


def normalize_team_form(form):
    ten_doi = (form.get("ten_doi") or "").strip()
    mo_ta = (form.get("mo_ta") or "").strip()

    errors = []
    if not ten_doi:
        errors.append("Tên đội bóng không được để trống.")

    return {"ten_doi": ten_doi, "mo_ta": mo_ta}, errors


def normalize_team_member_form(form):
    ten_thanh_vien = (form.get("ten_thanh_vien") or "").strip()
    trinh_do = (form.get("trinh_do") or "C").strip().upper()
    loai_thanh_vien = (form.get("loai_thanh_vien") or "co_dinh").strip()
    ghi_chu = (form.get("ghi_chu") or "").strip()

    errors = []
    if not ten_thanh_vien:
        errors.append("Tên thành viên không được để trống.")
    if trinh_do not in VALID_TRINH_DO:
        errors.append("Trình độ chỉ được chọn A, B, C hoặc D.")
        trinh_do = "C"
    if loai_thanh_vien not in VALID_LOAI_THANH_VIEN:
        errors.append("Loại thành viên không hợp lệ.")
        loai_thanh_vien = "co_dinh"

    return {
        "ten_thanh_vien": ten_thanh_vien,
        "trinh_do": trinh_do,
        "loai_thanh_vien": loai_thanh_vien,
        "ghi_chu": ghi_chu,
    }, errors


def normalize_team_month_form(form):
    errors = []
    try:
        data = {
            "muc_phi_thang": _parse_money_field(form.get("muc_phi_thang")),
            "chi_phi_san_bai": _parse_money_field(form.get("chi_phi_san_bai")),
            "chi_phi_nuoc_noi": _parse_money_field(form.get("chi_phi_nuoc_noi")),
            "chi_phi_khac": _parse_money_field(form.get("chi_phi_khac")),
            "ghi_chu": (form.get("ghi_chu") or "").strip(),
        }
    except ValueError:
        errors.append("Các trường tiền chỉ được nhập số hợp lệ.")
        data = {
            "muc_phi_thang": 0,
            "chi_phi_san_bai": 0,
            "chi_phi_nuoc_noi": 0,
            "chi_phi_khac": 0,
            "ghi_chu": (form.get("ghi_chu") or "").strip(),
        }
    return data, errors
