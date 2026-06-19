import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2
from config import DB_CONFIG

class EmailService:
    # Cấu hình email (sửa theo SMTP của bạn)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "your-email@gmail.com"  # Sửa thành email của bạn
    SENDER_PASSWORD = "your-app-password"   # Sửa thành mật khẩu ứng dụng Gmail

    @staticmethod
    def send_invitation_email(giai_name, giai_id, vdv_name, vdv_email, dia_diem, thoi_gian, base_url="https://pickleball-m7wn.onrender.com"):
        """Gửi email mời tham gia"""
        subject = f'Thư mời tham gia "{giai_name}"'
        
        body = f"""Xin chào Anh/Chị {vdv_name},

Chào mừng Anh/Chị đến với giải đấu "{giai_name}", sẽ được tổ chức tại địa chỉ "{dia_diem}" vào lúc "{thoi_gian}".

Thông tin chi tiết giải đấu xem tại website: {base_url}/giai-dau/{giai_id}

Ban tổ chức rất mong Anh/Chị có mặt đầy đủ và đúng giờ để giải đấu được tổ chức thành công tốt đẹp.

Xin trân trọng cảm ơn.

BTC"""

        try:
            msg = MIMEMultipart()
            msg["From"] = EmailService.SENDER_EMAIL
            msg["To"] = vdv_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT) as server:
                server.starttls()
                server.login(EmailService.SENDER_EMAIL, EmailService.SENDER_PASSWORD)
                server.send_message(msg)

            # Lưu log gửi email
            EmailService._log_email(None, vdv_email, subject)
            return True, "Gửi email thành công"
        except Exception as e:
            return False, f"Lỗi gửi email: {str(e)}"

    @staticmethod
    def send_bulk_invitation(giai_id, giai_name, players, dia_diem, thoi_gian, base_url="https://pickleball-m7wn.onrender.com"):
        """Gửi email hàng loạt cho toàn bộ VĐV"""
        results = []
        for p in players:
            p_id, giai_id_check, ten, trinh, tien, email, ghi_chu = p if len(p) >= 7 else p + (None,) * (7 - len(p))
            if not email:
                results.append(f"⏭️ {ten}: Không có email")
                continue
            success, msg = EmailService.send_invitation_email(giai_name, giai_id, ten, email, dia_diem, thoi_gian, base_url)
            if success:
                results.append(f"✅ {ten}: {msg}")
            else:
                results.append(f"❌ {ten}: {msg}")
        return results

    @staticmethod
    def _log_email(giai_id, email, subject):
        """Lưu log gửi email"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_log (giai_dau_id, recipient_email, subject)
                VALUES (%s, %s, %s);
            """, (giai_id, email, subject))
            conn.commit()
            cursor.close()
            conn.close()
        except:
            pass