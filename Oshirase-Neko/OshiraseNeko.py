import sys
import requests
import json
import base64
import time
import urllib3
import configparser
import logging
import serial
import serial.tools.list_ports
import threading
from urllib.parse import urlparse
import argparse

# Suppress only the specific InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup argparse
parser = argparse.ArgumentParser(description="Collaborator Polling Script with ESP32.")
parser.add_argument(
    "-x", "--upstream-proxy", 
    action="store_true", 
    help="Enable the use of an upstream proxy"
)
args = parser.parse_args()

# Read configuration settings from config.ini
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

polling_endpoint = config["Collaborator"]["polling-endpoint"]
poll_interval = int(config["Collaborator"]["poll-interval"])
proxy = config["Collaborator"]["proxy"]

esp32_port = config["ESP32"]["port"]
esp32_baudrate = int(config["ESP32"]["baudrate"])

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
file_handler = logging.FileHandler("interactions.log")
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Check if the collaborator server is accessible
domain = urlparse(polling_endpoint).netloc
try:
    response = requests.get(f"{polling_endpoint}", timeout=5)
    if response.status_code == 200:
        logging.info(f"Collaborator server {domain} is accessible.")
    else:
        logging.error(
            f"Collaborator server {domain} returned status code {response.status_code}. Exiting."
        )
        sys.exit(1)
except requests.RequestException as e:
    logging.error(
        f"Unable to access collaborator server {domain}. Exception: {e}. Exiting."
    )
    sys.exit(1)


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    available_ports = [port.device for port in ports]
    return available_ports


def save_port_to_config(port):
    config["ESP32"]["port"] = port
    with open("config.ini", "w") as configfile:
        config.write(configfile)
    logging.info(f"Serial port {port} saved to config.ini.")


# Initialize serial communication with ESP32
def initialize_serial_connection(port=esp32_port, baudrate=esp32_baudrate):
    try:
        ser = serial.Serial(port, baudrate)
        logging.info(f"Serial connection established on {port} at {baudrate} baud.")
        return ser
    except serial.SerialException as e:
        logging.error(f"Failed to establish serial connection: {e}")
        available_ports = list_serial_ports()
        if not available_ports:
            logging.error(
                "No serial ports found. Please connect your ESP32 and try again."
            )
            sys.exit(1)
        else:
            logging.info("Available serial ports:")
            for i, p in enumerate(available_ports):
                logging.info(f"{i}: {p}")
            port_choice = input(
                "Select the correct serial port number from the list above: "
            )
            try:
                port_choice_index = int(port_choice)
                if 0 <= port_choice_index < len(available_ports):
                    selected_port = available_ports[port_choice_index]
                    try:
                        ser = serial.Serial(selected_port, baudrate)
                        logging.info(
                            f"Serial connection established on {selected_port} at {baudrate} baud."
                        )
                        save_port_to_config(
                            selected_port
                        )
                        return ser
                    except serial.SerialException as e:
                        logging.error(
                            f"Failed to establish serial connection on selected port: {e}"
                        )
                        sys.exit(1)
                else:
                    logging.error("Invalid selection. Exiting.")
                    sys.exit(1)
            except ValueError:
                logging.error("Invalid input. Exiting.")
                sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


ser = initialize_serial_connection()


def send_command_esp32(command):
    if ser and ser.is_open:
        try:
            ser.write((command + "\n").encode())
            response = ser.readline().decode().strip()
            logging.debug(f"ESP32 Response: {response}")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error sending command to ESP32: {e}")
    else:
        logging.error("Attempting to use a port that is not open.")


def decode_base64(data, description="Data"):
    logging.debug(f"Raw data: {data}")
    try:
        decoded_bytes = base64.b64decode(data)
        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logging.debug(f"{description} (Text Decoding Error). Returning raw bytes.")
            return decoded_bytes
    except Exception as e:
        logging.error(f"{description} (Base64 Decoding Error): {e}")
        return None


def process_interaction(interaction):
    print("-" * 80)
    logging.info(f"Type: {interaction['protocol'].upper()}")
    logging.info(f"From: {interaction['client']}")
    logging.info(f"Time: {interaction['time']}")

    if interaction["protocol"] in ["http", "https"]:
        request = decode_base64(interaction["data"]["request"], "Request")
        if request:
            logging.info(f"Request: \n{request}")

        response = decode_base64(interaction["data"]["response"], "Response")
        if response:
            logging.info(f"Response: \n{response}")

    elif interaction["protocol"] == "dns":
        logging.info(f"Domain: {interaction['data']['subDomain']}")
        raw_request = decode_base64(interaction["data"]["rawRequest"], "Request")
        if raw_request:
            logging.info(f"DNS Query: {raw_request}")

    elif interaction["protocol"] == "smtp":
        sender = decode_base64(interaction["data"]["sender"], "Sender")
        if sender:
            logging.info(f"Sender: {sender}")

        recipient_list = interaction["data"]["recipients"]
        recipients = ", ".join(
            decode_base64(item, "Recipient") for item in recipient_list
        )
        if recipients:
            logging.info(f"Recipients: {recipients}")

        message = decode_base64(interaction["data"]["message"], "Message")
        if message:
            logging.info(f"Message: {message}")

        conversation = decode_base64(
            interaction["data"]["conversation"], "Conversation"
        )
        if conversation:
            logging.info(f"Conversation: {conversation}")

    else:
        logging.info(json.dumps(interaction, indent=2))


# Main polling loop
logging.info(
    f"Polling {domain} every {config['Collaborator']['poll-interval']} seconds."
)
try:
    while True:
        if args.upstream_proxy:
            response = requests.get(
                polling_endpoint, proxies={"http": proxy, "https": proxy}, verify=False
            )
        else:
            response = requests.get(polling_endpoint, verify=False)

        logging.debug(f"Raw server response: {response.content.decode()}")

        if response.content.decode() == "{}":
            logging.debug("No interactions found.")
            time.sleep(poll_interval)
            continue

        if response.status_code == 200:
            interactions = json.loads(response.content.decode())
            thread = threading.Thread(target=send_command_esp32, args=("wave",))
            thread.start()
            print("-" * 80)
            logging.info(f"Found {len(interactions['responses'])} Interactions.")
            for interaction in interactions["responses"]:
                process_interaction(interaction)
        else:
            logging.error(f"Received unexpected status code: {response.status_code}")
        time.sleep(poll_interval)
except KeyboardInterrupt:
    logging.info("Script Ended by User.")
    sys.exit(0)
except Exception as e:
    logging.error("Something went wrong.")
    logging.error(e)
    sys.exit(1)
finally:
    if ser and ser.is_open:
        ser.close()
    logging.info("Serial connection closed.")
