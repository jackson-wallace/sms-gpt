import openai
import datetime
import stripe
from flask import Flask, request, render_template, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import config
import firebase_admin
from firebase_admin import credentials, firestore
import json


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

# Initialize Flask app
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
            'subscribed': False,
            'stripe_customer_id': None
        })

    # If the user is in the database, retrieve their first text time and subscribed status
    else:
        # Parse the first_text_time string as a timezone-aware datetime object
        subscribed = user['subscribed']

    # If the user's not subscribed, send a message asking them to subscribe
    if not subscribed:
        
        # Create a stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            phone_number_collection={ # Here
                'enabled': True,      # Here
            }, 
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': 'price_1MJhvzDntfrNaBriGgMwEYLy',
                    'quantity': 1,
                },
            ],
            mode='subscription',
            subscription_data={
                'trial_period_days' : 7,
                },
            success_url=url_for('success', _external=True),
            cancel_url=url_for('cancel', _external=True),
        )

        # Include a link to the checkout session in the response text
        response_text = f"It's been more than a week since your first text! To continue using our service, please subscribe at {checkout_session.url}"
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


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Extract the request payload
    payload = request.data

    # Verify the authenticity of the request using the Stripe-Signature header
    sig_header = request.headers.get("Stripe-Signature")

    # Try to construct the event using the payload and signature
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, "whsec_EYuk89gAUshXjU1XUnX5tKXVyZzJlP0N")
    except Exception as e:
        # If an exception is raised, it means the event could not be constructed
        # This could be due to an invalid payload, signature, or secret key
        print(f"Failed to construct event: {e}")
        return "", 400

    # Get the type of the event
    event_type = event['type']

    # Convert the payload to a dictionary
    payload_dict = json.loads(payload)

    # Access the customer field
    customer_id = payload_dict['data']['object']['customer']

    # Retrieve the customer using their ID
    customer = stripe.Customer.retrieve(customer_id)

    # Extract the phone number from the customer object
    phone_number = customer['phone']

    if event_type == 'customer.subscription.created':
        
        # Update the "subscribed" field in the Firestore database for this customer
        user_ref = db.collection('user_data').document(phone_number)
        user_ref.update({
            'subscribed': True,
            'stripe_customer_id': customer_id
        })

    return "", 200



@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

if __name__ == "__main__":
    app.run(debug=True)


