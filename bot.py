from web3 import Web3
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration for all blockchains
configs = {
    'eth': {
        'rpc_url': os.getenv('ETH_ALCHEMY_URL'),  # e.g., https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
        'receiver_address': os.getenv('ETH_RECEIVER_ADDRESS'),  # Duser
        'chain_id': 11155111,  # Sepolia Testnet
        'name': 'Sepolia Testnet'
    },
    'bnb': {
        'rpc_url': os.getenv('BNB_RPC_URL'),  # e.g., https://data-seed-prebsc-1-s1.binance.org:8545/
        'receiver_address': os.getenv('BNB_RECEIVER_ADDRESS'),  # Duser
        'chain_id': 97,  # BNB Testnet
        'name': 'BNB Testnet'
    },
    'base': {
        'rpc_url': os.getenv('BASE_RPC_URL'),  # e.g., https://sepolia.base.org
        'receiver_address': os.getenv('BASE_RECEIVER_ADDRESS'),  # Duser
        'chain_id': 84532,  # Base Sepolia Testnet
        'name': 'Base Sepolia Testnet'
    },
    'polygon': {
        'rpc_url': os.getenv('POLYGON_RPC_URL'),  # e.g., https://rpc-mumbai.polygon.technology
        'receiver_address': os.getenv('POLYGON_RECEIVER_ADDRESS'),  # Duser
        'chain_id': 80001,  # Polygon Mumbai Testnet
        'name': 'Polygon Mumbai Testnet'
    },
    'arbitrum': {
        'rpc_url': os.getenv('ARBITRUM_RPC_URL'),  # e.g., https://sepolia-rollup.arbitrum.io/rpc
        'receiver_address': os.getenv('ARBITRUM_RECEIVER_ADDRESS'),  # Duser
        'chain_id': 421614,  # Arbitrum Sepolia Testnet
        'name': 'Arbitrum Sepolia Testnet'
    }
}

# Load sender wallets (address: private_key pairs)
wallets = {
    'eth': {},
    'bnb': {},
    'base': {},
    'polygon': {},
    'arbitrum': {}
}

# Load sender wallets (Auser, Buser, Cuser optional)
sender_users = ['AUSER', 'BUSER', 'CUSER']
for user in sender_users:
    for chain in configs.keys():
        address = os.getenv(f'{chain.upper()}_SENDER_{user}')
        private_key = os.getenv(f'{chain.upper()}_PRIVATE_KEY_{user}')
        if address and private_key:
            wallets[chain][address] = private_key
        else:
            print(f"Warning: {chain.upper()}_SENDER_{user} or {chain.upper()}_PRIVATE_KEY_{user} not found in .env, skipping...")

# Check if at least one wallet is configured
if not any(wallets[chain] for chain in wallets):
    print("Error: No valid sender wallets found in .env file")
    exit()

# Connect to EVM-based blockchains
w3_instances = {}
for chain, config in configs.items():
    w3_instances[chain] = Web3(Web3.HTTPProvider(config['rpc_url']))
    if not w3_instances[chain].is_connected():
        print(f"Failed to connect to {config['name']} node")
        exit()

# Convert EVM addresses to checksum format
for chain, config in configs.items():
    try:
        if config['receiver_address']:
            configs[chain]['receiver_address'] = w3_instances[chain].to_checksum_address(config['receiver_address'])
        wallets[chain] = {w3_instances[chain].to_checksum_address(addr): key for addr, key in wallets[chain].items()}
    except ValueError as e:
        print(f"Invalid address format for {chain}: {e}")
        exit()

# Gas settings for EVM chains
GAS_LIMIT = 21000  # Standard gas limit for ETH/BNB/Base/Polygon/Arbitrum transfer

# Track last known balances
last_balances = {
    chain: {addr: w3_instances[chain].eth.get_balance(addr) for addr in wallets[chain]}
    for chain in configs.keys()
}

# Generic EVM transfer function
def transfer_funds_evm(w3, private_key, sender_address, receiver_address, chain_name, chain_id):
    try:
        current_balance = w3.eth.get_balance(sender_address)
        gas_price = w3.eth.gas_price
        gas_fee = GAS_LIMIT * gas_price
        amount_to_transfer = current_balance - gas_fee
        
        if amount_to_transfer <= 0:
            print(f"Insufficient balance on {chain_name} for {sender_address} to cover gas fees")
            return False, None
        
        nonce = w3.eth.get_transaction_count(sender_address)
        tx = {
            'nonce': nonce,
            'to': receiver_address,
            'value': amount_to_transfer,
            'gas': GAS_LIMIT,
            'gasPrice': gas_price,
            'chainId': chain_id
        }
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transfer sent on {chain_name} from {sender_address}: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transfer confirmed on {chain_name} from {sender_address}: {receipt.transactionHash.hex()}")
        return True, current_balance
    except Exception as e:
        print(f"Error on {chain_name} for {sender_address}: {e}")
        return False, None

# Check and transfer for EVM chains
def check_and_transfer_evm(chain):
    global last_balances
    w3 = w3_instances[chain]
    config = configs[chain]
    for sender_address, private_key in wallets[chain].items():
        try:
            current_balance = w3.eth.get_balance(sender_address)
            if current_balance > last_balances[chain][sender_address]:
                print(f"New deposit detected on {config['name']} for {sender_address}! Current balance: {w3.from_wei(current_balance, 'ether')} {chain.upper()}")
                success, new_balance = transfer_funds_evm(w3, private_key, sender_address, config['receiver_address'], config['name'], config['chain_id'])
                if success:
                    last_balances[chain][sender_address] = new_balance
            else:
                print(f"No new deposits detected on {config['name']} for {sender_address}")
            last_balances[chain][sender_address] = current_balance
        except Exception as e:
            print(f"{config['name']} error for {sender_address}: {e}")

# Main loop
def main():
    print("Starting wallet monitoring for multiple blockchains...")
    print(f"Monitoring wallets: ETH({len(wallets['eth'])}), BNB({len(wallets['bnb'])}), Base({len(wallets['base'])}), Polygon({len(wallets['polygon'])}), Arbitrum({len(wallets['arbitrum'])})")
    while True:
        for chain in configs.keys():
            check_and_transfer_evm(chain)
        time.sleep(7)  # Check every 7 seconds

if __name__ == "__main__":
    main()
