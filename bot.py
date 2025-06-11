from web3 import Web3
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration for Sepolia Testnet (using Alchemy)
eth_alchemy_url = os.getenv('ETH_ALCHEMY_URL')  # e.g., https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
eth_receiver_address = os.getenv('ETH_RECEIVER_ADDRESS')  # Testnet Ethereum cold storage address (Duser)

# Configuration for BNB Testnet
bnb_rpc_url = os.getenv('BNB_RPC_URL')  # e.g., https://data-seed-prebsc-1-s1.binance.org:8545/
bnb_receiver_address = os.getenv('BNB_RECEIVER_ADDRESS')  # Testnet BNB cold storage address (Duser)

# Load multiple sender wallets (address: private_key pairs)
eth_wallets = {}
bnb_wallets = {}

# Load Ethereum sender wallets (Auser, Buser, Cuser, etc.)
for user in ['AUSER', 'BUSER', 'CUSER']:  # Add more users as needed
    address = os.getenv(f'ETH_SENDER_{user}')
    private_key = os.getenv(f'ETH_PRIVATE_KEY_{user}')
    if address and private_key:
        eth_wallets[address] = private_key
    else:
        print(f"Warning: ETH_SENDER_{user} or ETH_PRIVATE_KEY_{user} not found in .env")

# Load BNB sender wallets (Auser, Buser, Cuser, etc.)
for user in ['AUSER', 'BUSER', 'CUSER']:  # Add more users as needed
    address = os.getenv(f'BNB_SENDER_{user}')
    private_key = os.getenv(f'BNB_PRIVATE_KEY_{user}')
    if address and private_key:
        bnb_wallets[address] = private_key
    else:
        print(f"Warning: BNB_SENDER_{user} or BNB_PRIVATE_KEY_{user} not found in .env")

if not eth_wallets and not bnb_wallets:
    print("Error: No valid sender wallets found in .env file")
    exit()

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

# Convert addresses to checksum format
try:
    eth_receiver_address = w3_eth.to_checksum_address(eth_receiver_address) if eth_receiver_address else None
    bnb_receiver_address = w3_bnb.to_checksum_address(bnb_receiver_address) if bnb_receiver_address else None
    eth_wallets = {w3_eth.to_checksum_address(addr): key for addr, key in eth_wallets.items()}
    bnb_wallets = {w3_bnb.to_checksum_address(addr): key for addr, key in bnb_wallets.items()}
except ValueError as e:
    print(f"Invalid address format: {e}")
    exit()

# Gas settings
GAS_LIMIT = 21000  # Standard gas limit for ETH/BNB transfer

# Track last known balances for each wallet
eth_last_balances = {addr: w3_eth.eth.get_balance(addr) for addr in eth_wallets}
bnb_last_balances = {addr: w3_bnb.eth.get_balance(addr) for addr in bnb_wallets}

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
            print(f"Insufficient balance on {chain_name} for {sender_address} to cover gas fees")
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
        print(f"Transfer sent on {chain_name} from {sender_address}: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transfer confirmed on {chain_name} from {sender_address}: {receipt.transactionHash.hex()}")
        
        return True, current_balance
    except Exception as e:
        print(f"Error on {chain_name} for {sender_address}: {e}")
        return False, None

# Check and transfer for Sepolia Testnet
def check_and_transfer_eth():
    global eth_last_balances
    for sender_address, private_key in eth_wallets.items():
        try:
            current_balance = w3_eth.eth.get_balance(sender_address)
            
            # Check if balance has increased (new deposit)
            if current_balance > eth_last_balances[sender_address]:
                print(f"New ETH deposit detected on Sepolia Testnet for {sender_address}! Current balance: {w3_eth.from_wei(current_balance, 'ether')} ETH")
                success, new_balance = transfer_funds(w3_eth, private_key, sender_address, eth_receiver_address, "Ethereum", 1)
                if success:
                    eth_last_balances[sender_address] = new_balance
            else:
                print(f"No new ETH deposits detected on Sepolia Testnet for {sender_address}")
            
            eth_last_balances[sender_address] = current_balance
        except Exception as e:
            print(f"Sepolia Testnet error for {sender_address}: {e}")

# Check and transfer for BNB Testnet
def check_and_transfer_bnb():
    global bnb_last_balances
    for sender_address, private_key in bnb_wallets.items():
        try:
            current_balance = w3_bnb.eth.get_balance(sender_address)
            
            # Check if balance has increased (new deposit)
            if current_balance > bnb_last_balances[sender_address]:
                print(f"New BNB deposit detected on BNB Testnet for {sender_address}! Current balance: {w3_bnb.from_wei(current_balance, 'ether')} BNB")
                success, new_balance = transfer_funds(w3_bnb, private_key, sender_address, bnb_receiver_address, "BNB Chain", 56)
                if success:
                    bnb_last_balances[sender_address] = new_balance
            else:
                print(f"No new BNB deposits detected on BNB Testnet for {sender_address}")
            
            bnb_last_balances[sender_address] = current_balance
        except Exception as e:
            print(f"BNB Testnet error for {sender_address}: {e}")

# Main loop to check for new deposits
def main():
    print("Starting wallet monitoring for Sepolia Testnet (Alchemy) and BNB Testnet...")
    print(f"Monitoring {len(eth_wallets)} Ethereum wallets and {len(bnb_wallets)} BNB wallets")
    while True:
        check_and_transfer_eth()
        check_and_transfer_bnb()
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()
