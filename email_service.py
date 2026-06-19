import os
from dotenv import load_dotenv
import psycopg2
from config import DB_CONFIG

load_dotenv()

class EmailService:
    # SendGrid Configuration
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
    
    SENDER_EMAIL = "noreply@pickleball-tournament.com"
    SENDER_NAME = "Quản Lý Giải Pickleball"

    @staticmethod
    def send_invitation_email(giai_name, giai_id, vdv_name, vdv_email, dia_diem, thoi_gian, base_url="https://pickleball-m7wn.onrender.com"):
        """Gửi email mời tham gia (qua SendGrid)"""
        
        # Nếu chưa cấu hình SendGrid
        if not EmailService.SENDGRID_API_KEY:
            return False, "⚠️ SendGrid API key chưa được cấu hình. Hãy thêm SENDGRID_API_KEY vào .env hoặc environment variables."
        
        subject = f'Thư mời tham gia "{giai_name}"'
        
        body = f"""Xin chào Anh/Chị {vdv_name},

Chào mừng Anh/Chị đến với giải đấu "{giai_name}", sẽ được tổ chức tại địa chỉ "{dia_diem}" vào lúc "{thoi_gian}".

Thông tin chi tiết giải đấu xem tại website: {base_url}/giai-dau/{giai_id}

Thông tin đăng nhập:
- Email: {vdv_email}
- Mật khẩu: 123456789 (mặc định)

Ban tổ chức rất mong Anh/Chị có mặt đầy đủ và đúng giờ để giải đấu được tổ chức thành công tốt đẹp.

Xin trân trọng cảm ơn.

Ban Tổ Chức"""

        try:
            import requests
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": vdv_email, "name": vdv_name}],
                        "subject": subject
                    }
                ],
                "from": {"email": EmailService.SENDER_EMAIL, "name": EmailService.SENDER_NAME},
                "content": [{"type": "text/plain", "value": body}]
            }
            
            headers = {
                "Authorization": f"Bearer {EmailService.SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(EmailService.SENDGRID_API_URL, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 202]:
                EmailService._log_email(giai_id, vdv_email, subject)
                return True, "✅ Gửi email thành công"
            else:
                error_msg = response.text[:200] if response.text else "Unknown error"
                return False, f"❌ Lỗi SendGrid: {error_msg}"
                
        except ImportError:
            return False, "❌ Lỗi: Module 'requests' chưa được cài. Chạy: pip install requests"
        except Exception as e:
            return False, f"❌ Lỗi gửi email: {str(e)}"

    @staticmethod
    def send_bulk_invitation(giai_id, giai_name, players, dia_diem, thoi_gian, base_url="https://pickleball-m7wn.onrender.com"):
        """Gửi email hàng loạt cho toàn bộ VĐV"""
        results = []
        for p in players:
            p_id, giai_id_check, ten, trinh, tien, email = p[:6]
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
        """Lưu log gửi email vào database"""
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
        except Exception as e:
            print(f"⚠️ Không thể log email: {str(e)}")