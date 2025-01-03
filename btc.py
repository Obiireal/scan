import mnemonic
import bip32utils
import requests
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.logging import RichHandler

a = " "

# Logger setup
console = Console()
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[RichHandler()])
logger = logging.getLogger("rich")

# Global list to store wallets with non-zero balances
scanned_wallets = []

def clear_console():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_mnemonic():
    """Generate a random 12-word mnemonic."""
    mnemo = mnemonic.Mnemonic("english")
    return mnemo.generate(strength=128)

def recover_wallet_from_mnemonic(mnemonic_phrase, coin):
    """Recover a wallet for a specific coin from the mnemonic."""
    seed = mnemonic.Mnemonic.to_seed(mnemonic_phrase)

    # Determine the derivation path based on the coin
    if coin == "BTC":
        coin_index = 0
    elif coin == "ETH":
        coin_index = 60
    elif coin == "LTC":
        coin_index = 2
    else:
        logger.error(f"Unsupported coin: {coin}")
        return None, 0, None

    # Derive the address
    key = bip32utils.BIP32Key.fromEntropy(seed)
    child_key = key.ChildKey(44 | bip32utils.BIP32_HARDEN).ChildKey(coin_index | bip32utils.BIP32_HARDEN).ChildKey(0 | bip32utils.BIP32_HARDEN).ChildKey(0).ChildKey(0)
    address = child_key.Address()

    # Check balance
    if coin == "BTC":
        balance = check_BTC_balance(address)
    elif coin == "ETH":
        balance = check_ETH_balance(address)
    elif coin == "LTC":
        balance = check_LTC_balance(address)

    return mnemonic_phrase, balance, address

def check_BTC_balance(address):
    """Check Bitcoin balance using Blockchain.info."""
    try:
        response = requests.get(f"https://blockchain.info/balance?active={address}")
        response.raise_for_status()
        data = response.json()
        balance = data[address]["final_balance"]
        return balance / 10**8  # Convert Satoshis to BTC
    except requests.RequestException as e:
        a = 1
        return 0

def check_ETH_balance(address):
    """Check Ethereum balance using Blockchair API."""
    try:
        response = requests.get(f"https://api.blockchair.com/ethereum/dashboards/address/{address}")
        response.raise_for_status()
        data = response.json()
        balance = int(data["data"][address]["address"]["balance"]) / 10**18  # Convert Wei to ETH
        return balance
    except requests.RequestException as e:
        a = 2
        return 0

def check_LTC_balance(address):
    """Check Litecoin balance using SoChain API."""
    try:
        response = requests.get(f"https://sochain.com/api/v2/get_address_balance/LTC/{address}")
        response.raise_for_status()
        data = response.json()
        balance = float(data["data"]["confirmed_balance"])
        return balance
    except requests.RequestException as e:
        a = 3
        return 0

def display_scanned_wallets():
    """Display wallets with non-zero balances."""
    console.print("\n[bold cyan]Scanned Wallets with Non-Zero Balances[/bold cyan]\n")
    for wallet in scanned_wallets:
        mnemonic_phrase = wallet["mnemonic"]
        address = wallet["address"]
        balance = wallet["balance"]
        coin = wallet["coin"]

        console.print(f"Mnemonic: {mnemonic_phrase[:20]}...", style="bold green")
        console.print(f"{coin} Address: {address[:20]}...", style="bold green")
        console.print(f"{coin} Balance: {balance:.8f} {coin}", style="bold green")
        console.print("-" * 50)

def check_wallets_parallel(mnemonic_phrases, coin):
    """Check multiple wallets in parallel."""
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(recover_wallet_from_mnemonic, phrase, coin) for phrase in mnemonic_phrases]

        for future in as_completed(futures):
            mnemonic_phrase, balance, address = future.result()
            if balance >= 0:
                logger.info(f"Mnemonic: {mnemonic_phrase[:20]}...")
                logger.info(f"{coin} Address: {address}")
                logger.info(f"{coin} Balance: {balance:.8f} {coin}")

                # Save wallets with non-zero balances
                if balance > 0:
                    scanned_wallets.append({"mnemonic": mnemonic_phrase, "address": address, "balance": balance, "coin": coin})
                    with open("wallets.txt", "a") as f:
                        f.write(f"{coin} Address: {address}\n")
                        f.write(f"Balance: {balance:.8f} {coin}\n")
                        f.write(f"Mnemonic: {mnemonic_phrase}\n\n")

def main():
    """Main function to execute the tool."""
    console.print("[bold green]Welcome to the Multi-Coin Wallet Scanner![/bold green]")
    
    console.print("\n[cyan]Select an option:[/cyan]")
    console.print("(1) Scan Bitcoin (BTC)")
    console.print("(2) Scan Ethereum (ETH)")
    console.print("(3) Scan Litecoin (LTC)")

    choice = input("Enter your choice: ").strip()

    coin = None
    if choice == "1":
        coin = "BTC"
    elif choice == "2":
        coin = "ETH"
    elif choice == "3":
        coin = "LTC"
    else:
        logger.error("Invalid choice. Exiting...")
        return

    clear_console()
    logger.info(f"Starting wallet scan for {coin}...")

    # Generate random mnemonics and scan wallets
    mnemonic_count = 0
    while True:
        mnemonic_phrases = [generate_mnemonic() for _ in range(500)]
        check_wallets_parallel(mnemonic_phrases, coin)
        mnemonic_count += 500
        logger.info(f"Total mnemonics scanned: {mnemonic_count}")

    # Display wallets with non-zero balances
    display_scanned_wallets()

if __name__ == "__main__":
    main()
