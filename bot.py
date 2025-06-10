from web3 import Web3
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration for Sepolia Testnet (using Alchemy)
eth_alchemy_url = os.getenv('ETH_ALCHEMY_URL')  # e.g., https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
eth_private_key = os.getenv('ETH_PRIVATE_KEY')  # Testnet Ethereum sender wallet private key
eth_sender_address = os.getenv('ETH_SENDER_ADDRESS')  # Testnet Ethereum sender wallet address
eth_receiver_address = os.getenv('ETH_RECEIVER_ADDRESS')  # Testnet Ethereum cold storage address

# Configuration for BNB Testnet
bnb_rpc_url = os.getenv('BNB_RPC_URL')  # e.g., https://data-seed-prebsc-1-s1.binance.org:8545/
bnb_private_key = os.getenv('BNB_PRIVATE_KEY')  # Testnet BNB sender wallet private key
bnb_sender_address = os.getenv('BNB_SENDER_ADDRESS')  # Testnet BNB sender wallet address
bnb_receiver_address = os.getenv('BNB_RECEIVER_ADDRESS')  # Testnet BNB cold storage address

# Connect to Sepolia Testnet (Alchemy) and BNB Testnet nodes
w3_eth = Web3(Web3.HTTPProvider(eth_alchemy_url))
w3_bnb = Web3(Web3.HTTPProvider(bnb_rpc_url))

# Check connections
if not w3_eth.is_connected():
    print("Failed to connect to Sepolia Testnet node (Alchemy)")
    exit()
if not w3_bnb.is_connected():
    print("Failed to connect to BNB Testnet node")
    exit()

# Gas settings
GAS_LIMIT = 21000  # Standard gas limit for ETH/BNB transfer

# Track last known balances
last_balance_eth = w3_eth.eth.get_balance(eth_sender_address)
last_balance_bnb = w3_bnb.eth.get_balance(bnb_sender_address)

# Generic transfer function
def transfer_funds(w3, private_key, sender_address, receiver_address, chain_name, chain_id):
    try:
        # Get current balance
        current_balance = w3.eth.get_balance(sender_address)
        
        # Get dynamic gas price
        gas_price = w3.eth.gas_price
        gas_fee = GAS_LIMIT * gas_price
        
        # Amount to transfer (total balance minus gas fee)
        amount_to_transfer = current_balance - gas_fee
        
        if amount_to_transfer <= 0:
            print(f"Insufficient balance on {chain_name} to cover gas fees")
            return False, None
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(sender_address)
        
        # Build transaction
        tx = {
            'nonce': nonce,
            'to': receiver_address,
            'value': amount_to_transfer,
            'gas': GAS_LIMIT,
            'gasPrice': gas_price,
            'chainId': chain_id  # 11155111 for Sepolia Testnet, 97 for BNB Testnet
        }
        
        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transfer sent on {chain_name}: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transfer confirmed on {chain_name}: {receipt.transactionHash.hex()}")
        
        return True, current_balance
    except Exception as e:
        print(f"Error on {chain_name}: {e}")
        return False, None

# Check and transfer for Sepolia Testnet
def check_and_transfer_eth():
    global last_balance_eth
    try:
        current_balance = w3_eth.eth.get_balance(eth_sender_address)
        
        # Check if balance has increased (new deposit)
        if current_balance > last_balance_eth:
            print(f"New ETH deposit detected on Sepolia Testnet! Current balance: {w3_eth.from_wei(current_balance, 'ether')} ETH")
            success, new_balance = transfer_funds(w3_eth, eth_private_key, eth_sender_address, eth_receiver_address, "Sepolia Testnet", 11155111)
            if success:
                last_balance_eth = new_balance
        else:
            print("No new ETH deposits detected on Sepolia Testnet")
        
        last_balance_eth = current_balance
    except Exception as e:
        print(f"Sepolia Testnet error: {e}")

# Check and transfer for BNB Testnet
def check_and_transfer_bnb():
    global last_balance_bnb
    try:
        current_balance = w3_bnb.eth.get_balance(bnb_sender_address)
        
        # Check if balance has increased (new deposit)
        if current_balance > last_balance_bnb:
            print(f"New BNB deposit detected on BNB Testnet! Current balance: {w3_bnb.from_wei(current_balance, 'ether')} BNB")
            success, new_balance = transfer_funds(w3_bnb, bnb_private_key, bnb_sender_address, bnb_receiver_address, "BNB Testnet", 97)
            if success:
                last_balance_bnb = new_balance
        else:
            print("No new BNB deposits detected on BNB Testnet")
        
        last_balance_bnb = current_balance
    except Exception as e:
        print(f"BNB Testnet error: {e}")

# Main loop to check for new deposits
def main():
    print("Starting wallet monitoring for Sepolia Testnet (Alchemy) and BNB Testnet...")
    while True:
        check_and_transfer_eth()
        check_and_transfer_bnb()
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()
