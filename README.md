# Flask OpenAI Chatbot

This is a simple Flask application that integrates with OpenAI's API and Twilio to create a chatbot that can respond to user messages via SMS. The chatbot utilizes OpenAI's GPT-3 language model to generate intelligent responses based on user inputs.

## How It Works

1. The user sends an SMS message to the specified phone number.
2. Twilio forwards the message to the Flask application.
3. The Flask application uses the OpenAI API to generate a response based on the user's message and the conversation history.
4. The generated response is sent back to the user as an SMS message.

## Getting Started

To run the Flask OpenAI Chatbot locally, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/flask-openai-chatbot.git
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up the necessary environment variables:

   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `TWILIO_ACCOUNT_SID`: Your Twilio account SID.
   - `TWILIO_AUTO_TOKEN`: Your Twilio authentication token.
   - `TWILIO_PHONE_NUMBER`: The phone number provided by Twilio for your application.

4. Run the Flask application:

   ```bash
   python app.py
   ```

   The application will be accessible at `http://localhost:5000`.

## Usage

To interact with the chatbot, send an SMS message to the specified phone number. The chatbot will respond with a generated message based on the conversation history.

## Screenshots

![Screenshot 1](screenshots/screenshot1.png)

*Example conversation:*

```
User: Hello, how are you?
Chatbot: I am doing great. How can I help you today?
User: What is the capital of France?
Chatbot: The capital of France is Paris.
User: How tall is Mount Everest?
Chatbot: Mount Everest is approximately 8,848 meters (29,029 feet) tall.
```

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For any questions or inquiries, please contact [email protected]
