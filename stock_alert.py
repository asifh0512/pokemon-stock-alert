import os
from resend import Resend

# Henter API-key fra GitHub Secrets
api_key = os.environ["RESEND_API_KEY"]

resend = Resend(api_key)

def send_test_email():
    response = resend.emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": ["asifh0512@gmail.com"],
        "subject": "TEST - Pokemon stock alert",
        "html": "<p>🎉 Test: Resend fungerer!</p>"
    })

    print(response)

send_test_email()
print("Ferdig")
