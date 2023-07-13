import os
import openai
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

start_chat_log = """Human: Hello, how are you doing?
AI: I am doing great. How can I help you today?
"""

# Get environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")
twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.environ.get("TWILIO_AUTO_TOKEN")
twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")

# Set OpenAI API key
openai.api_key = openai_api_key

# Your Account Sid and Auth Token from twilio.com/console
client = Client(twilio_account_sid, twilio_auth_token)

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "i-have-a-chair-i-have-a-chair"


@app.route("/sms", methods=["POST"])
def sms_ahoy_reply():
    message_body = request.form["Body"]
    sender = request.form["From"]

    # Respond to incoming messages with a receipt SMS
    chat_log = start_chat_log

    prompt = f"{chat_log}Human: {message_body}\nAI:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=2048,
        temperature=0.7,
        stop=["\nHuman"],
    )
    response_text = response["choices"][0]["text"]

    message = client.messages.create(
        body=response_text, from_=twilio_phone_number, to=sender
    )

    return str(message)


if __name__ == "__main__":
    app.run(debug=True)
