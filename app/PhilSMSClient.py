import requests
import json

class PhilSMSClient:
    def __init__(self, token, sender_id):
        self.token = token
        self.sender_id = sender_id
        self.url = "https://app.philsms.com/api/v3/sms/send"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def send_sms(self, recipient, message):
        send_data = {
            'sender_id': self.sender_id,
            'recipient': recipient,
            'message': message
        }
        response = requests.post(self.url, headers=self.headers, data=json.dumps(send_data))
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "success":
                print("Message was successfully delivered.")
                print(f"Message UID: {response_data['data']['uid']}")
                print(f"Cost: {response_data['data']['cost']}")
            else:
                print(f"Failed to send message: {response_data.get('message')}")
        else:
            print(f"HTTP Error: {response.status_code}")
            print(response.text)


# Replace 'your_api_token' with your actual PhilSMS API token
api_token = '944|9Szci3KSbDkuxNGOzsL9nRycelhylzLoidyCNf4u'

# Replace 'your_sender_id' with your registered sender ID from PhilSMS
sender_id = 'PhilSMS'

# Create an instance of the PhilSMSClient
sms_client = PhilSMSClient(token=api_token, sender_id=sender_id)

# Define the recipient's phone number and the message content
recipient_number = '+639157581588'  # Replace with the recipient's mobile number
message_content = 'Testing.'

# Send the SMS message
sms_client.send_sms(recipient=recipient_number, message=message_content)
