import os
import openai
import datetime
import stripe
from flask import Flask, request, render_template, url_for, abort, redirect, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, firestore
import json
from dotenv import load_dotenv

load_dotenv()

start_chat_log = '''Human: Hello, how are you doing?
AI: I am doing great. How can I help you today?
'''

# Get the value of the environment variable
json_str = os.environ.get("serviceAccountKey")

# Parse the JSON string
service_account_key = json.loads(json_str)

# Pass the dictionary to the Certificate function
cred = credentials.Certificate(service_account_key)

firebase_admin.initialize_app(cred)

# Get a reference to the Firestore database
db = firestore.client()


# Get environment variables
openai_api_key = os.environ.get('OPENAI_API_KEY')
stripe_live_secret_key = os.environ.get('STRIPE_LIVE_SECRET_KEY')
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.environ.get('TWILIO_AUTO_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')



# Set OpenAI API key
openai.api_key = openai_api_key
#print(os.environ['OPENAI_API_KEY'])
#print(os.environ.get('twilio_account_sid'))
# Set Stripe API key
stripe.api_key = stripe_live_secret_key

# Your Account Sid and Auth Token from twilio.com/console
client = Client(twilio_account_sid, twilio_auth_token)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'i-have-a-chair-i-have-a-chair'


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
            'stripe_customer_id': None,
            'message_count': 1,
        })

    # If the user is in the database, retrieve their first text time and subscribed status
    else:

        # Update the 'message_count' field in the database by incrementing it by 1
        user_ref.update({
            'message_count': user['message_count'] + 1,
        })

        user_ref = db.collection('user_data').document(sender)
        user = user_ref.get().to_dict()

    # Check if the user is in the database
    user_ref = db.collection('user_data').document(sender)
    user = user_ref.get().to_dict()
    subscribed = user['subscribed']
    

    # If the user's not subscribed, send a message asking them to subscribe
    """
    3.
    If not subscribed and user has not signed up with stripe before
    """
    if not subscribed:
        
        # Create a stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            phone_number_collection={ # Here
                'enabled': True,      # Here
            }, 
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': 'price_1MbQQcDntfrNaBriJCIvkXyN',
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

        response_text = (f"Hi, welcome to sms-gpt! We're excited to have you on board. To get started, you can sign up for your free trial at the link below. This will allow you to ask me unlimited questions for a week. We hope you enjoy using our service! After signing up, I will send you some examples of the types of questions I can answer.{checkout_session.url}\n"
        )

        message = client.messages.create(
            body=response_text,
            from_=twilio_phone_number,
            to=sender
        )

        return str(message)

    """
    4.
    If not subscribed and user has signed up with stripe
        - if message body != SUBSCRIBE
            - send a message "your subscription is currently cancelled, text SUBSCRIBE to this number to reactivate your subscription"
        else:
            - unpause subscription
    """

    if subscribed and message_body.strip().lower() == "unsubscribe":

        # Get subscription list with customer ID 
        subscriptions = stripe.Subscription.list(customer=user['stripe_customer_id'])

        for subscription in subscriptions.data:
            if subscription.status == "active":
                # customer has an active subscription
                active_subscription_id = subscription.id

        #retrieve the subscription by id
        subscription = stripe.Subscription.retrieve(active_subscription_id)

        """
        2. 
        Change to pause subscription instead of cancel
        """

        # cancel the subscription
        subscription.cancel()

        return ''

    """Respond to incoming messages with a receipt SMS."""
    chat_log = session.get('chat_log')

    if chat_log is None:
        chat_log = start_chat_log

    prompt = f'{chat_log}Human: {message_body}\nAI:'
    # prompt = f"Respond to this prompt: {message_body}\n Given that the conversation up until this prompt was:\n{context} \n Only refer to the context if the user requests a prompt with an unclear pronoun in their prompt."
    # Use ChatGPT to generate a response
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=2048,
        temperature=0.7,
        stop=['\nHuman'],
    )
    response_text = response["choices"][0]["text"]

    session['chat_log'] = append_interaction_to_chat_log(message_body, response_text, chat_log)

    message = client.messages.create(
        body=response_text,
        from_= twilio_phone_number,
        to=sender
    )

    return str(message)


@app.route('/webhook', methods=['GET', 'POST'])
def handle_webhook():

    # REQUEST TOO BIG
    if request.content_length > 1024 ** 2:
        abort(400)

    # Extract the request payload
    payload = request.data

    # Verify the authenticity of the request using the Stripe-Signature header
    sig_header = request.headers.get("Stripe-Signature")

    # Try to construct the event using the payload and signature
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, "whsec_l1lJHeQ2REH11D3gftbwyCbyH4kHtrdx")

    except Exception as e:
        # If an exception is raised, it means the event could not be constructed
        # This could be due to an invalid payload, signature, or secret key
        print(f"Failed to construct event: {e}")
        return "", 400

    # Get the type of the event
    event_type = event['type']

    # Convert the payload to a dictionary
    payload_dict = json.loads(payload)

    customer_id = payload_dict['data']['object']['customer']

    # Retrieve the customer using their ID
    customer = stripe.Customer.retrieve(customer_id)

    # Extract the phone number from the customer object
    phone_number = customer['phone']

    user_ref = db.collection('user_data').document(phone_number)

    if event_type == 'customer.subscription.created':
        
        # Update the "subscribed" field in the Firestore database for this customer
        user_ref.update({
            'subscribed': True,
            'stripe_customer_id': customer_id
        })

        response_text = (f"Thanks for signing up! Here are some examples of questions that you can ask me:\n"
            f"\n"
            f"• What are some healthy recipes for dinner?\n"
            f"• How do I fix a leaky faucet?\n"
            f"• How do I create a budget?\n"
            f"• What are the symptoms of a cold?\n"
            f"• How do I improve my public speaking skills?\n"
            f"• What are some good exercises to do at home?\n"
            f"• Can you summarize this article? (paste link)\n"
            f"\n"
            f"I can also assist with more general questions, such as:\n"
            f"\n"
            f"• What are some interesting facts about the history of space exploration?\n"
            f"• What are the major world religions?\n"
            f"• What are the different types of political systems?\n"
            f"• What are the causes of the greenhouse effect?\n"
            f"\n"
            f"Ask your first question to get started. Have a good one!"
        )

        message = client.messages.create(
            body=response_text,
            from_=twilio_phone_number,
            to=phone_number,
        )
        print(message)

    """
    1. 
    Change this to be customer.subsctiption.updated
        if paused then ...
        elif unpaused then send "thank you for unpausing your subscription" or similar message
    """
    if event.type == 'customer.subscription.deleted':

        # Update the "subscribed" field in the Firestore database for this customer
        user_ref.update({
            'subscribed': False,
            'stripe_customer_id': 'None',
        })
        response_text = "Your subscription has successfully been cancelled."
        message = client.messages.create(
        body=response_text,
        from_= twilio_phone_number,
        to=phone_number
        )

        print(message)

    
    return "", 200

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

if __name__ == "__main__":
    app.run(debug=True)


"""
Helper functions
"""
def append_interaction_to_chat_log(question, answer, chat_log=None):
    if chat_log is None:
        chat_log = start_chat_log
    return f'{chat_log}Human: {question}\nAI: {answer}\n'