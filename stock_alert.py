import smtplib
from email.mime.text import MIMEText

# ====== ENDRE DENNE ======
TO_EMAIL = "asifh0512@gmail.com"
# =========================

def send_test_email():
    msg = MIMEText("TEST: Pokemon overvåking fungerer 🎉")
    msg["Subject"] = "TEST - Pokemon stock alert"
    msg["From"] = TO_EMAIL
    msg["To"] = TO_EMAIL

    # Gmail SMTP
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    # OBS: du må bruke Gmail app-passord senere
    server.login(TO_EMAIL, "PASSORD_HER")
    server.sendmail(TO_EMAIL, TO_EMAIL, msg.as_string())
    server.quit()

send_test_email()
print("Ferdig")
