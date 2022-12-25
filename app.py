import openai
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import config


app = Flask(__name__)

# Set OpenAI API key
openai.api_key = config.openai_api_key

# Your Account Sid and Auth Token from twilio.com/console
client = Client(config.twilio_account_sid, config.twilio_auth_tokenoken)


@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():

    message_body = request.form["Body"]
    sender = request.form["From"]

    """Respond to incoming messages with a receipt SMS."""
    # Use ChatGPT to generate a response
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"User: {message_body}\nBot:",
        max_tokens=1024,
        temperature=0.7,
    )
    response_text = response["choices"][0]["text"]
    # Start our response
    resp = MessagingResponse()
    # Add a message
    resp.message(response_text)

    return str(resp)


if __name__ == "__main__":
    app.run(debug=True)


