import openai
import datetime
import stripe
from flask import Flask, request, render_template, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import config
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pytz


# Initialize the Firebase app using the service account credentials
cred = credentials.Certificate('./serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Get a reference to the Firestore database
db = firestore.client()


# Set OpenAI API key
openai.api_key = config.openai_api_key

# Set Stripe API key
stripe.api_key = config.stripe_test_secret_key

# Your Account Sid and Auth Token from twilio.com/console
client = Client(config.twilio_account_sid, config.twilio_auth_token)


app = Flask(__name__)

@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():
    message_body = request.form["Body"]
    sender = request.form["From"]

    # Check if the user is in the database
    user_ref = db.collection('user_data').document(sender)
    user = user_ref.get().to_dict()

    # If the user is not in the database, add them and store the current time as their first text time
    if not user:
        user_ref.set({
            'first_text_time': datetime.datetime.now(),
            'subscribed': False
        })
        first_text_time = datetime.datetime.now()

    # If the user is in the database, retrieve their first text time and subscribed status
    else:
        # Parse the first_text_time string as a timezone-aware datetime object
        tz = pytz.timezone('UTC')
        first_text_time = datetime.datetime.fromisoformat(str(user['first_text_time'])).replace(tzinfo=tz)
        subscribed = user['subscribed']

    # Calculate the time difference between now and the user's first text time
    time_difference = datetime.datetime.now(tz) - first_text_time

    # If the user's first text was more than a week ago and they are not subscribed, send a message asking them to subscribe
    if time_difference.days > 7 and not subscribed:
        
        response_text = "It's been more than a week since your first text! To continue using our service, please subscribe at www.example.com/subscribe"
        # Start our response
        resp = MessagingResponse()
        # Add a message
        resp.message(response_text)
        return str(resp)

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


