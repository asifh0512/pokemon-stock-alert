import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

def send_test_email():
    response = resend.Emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": ["asifh0512@gmail.com"],
        "subject": "TEST - Pokemon stock alert",
        "html": "<p>🎉 Resend fungerer nå!</p>"
    })

    print(response)

send_test_email()
