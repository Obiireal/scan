import mnemonic
import bip32utils
import requests
import logging
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress

# Logger setup
console = Console()
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[RichHandler()])
logger = logging.getLogger("rich")

# Global variables
scanned_wallets = []  # To store wallets with non-zero balance

def clear_console():
    """Clear the console screen."""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def generate_mnemonic():
    mnemo = mnemonic.Mnemonic("english")
    return mnemo.generate(strength=128)

def recover_wallet_from_mnemonic(mnemonic_phrase):
    seed = mnemonic.Mnemonic.to_seed(mnemonic_phrase)
    root_key = bip32utils.BIP32Key.fromEntropy(seed)
    child_key = root_key.ChildKey(44 | bip32utils.BIP32_HARDEN).ChildKey(0 | bip32utils.BIP32_HARDEN).ChildKey(0 | bip32utils.BIP32_HARDEN).ChildKey(0).ChildKey(0)
    address = child_key.Address()
    balance = check_BTC_balance(address)
    return mnemonic_phrase, balance, address

def check_BTC_balance(address, retries=3, delay=0):
    for attempt in range(retries):
        try:
            response = requests.get(f"https://blockchain.info/balance?active={address}", timeout=1)
            response.raise_for_status()
            data = response.json()
            balance = data[address]["final_balance"]
            return balance / 100000000
        except requests.RequestException as e:
            if attempt < retries - 1:
                a = 2
                time.sleep(delay)
            else:
                a = 1
    return 0

def recover_wallet_from_partial_mnemonic(partial_mnemonic):
    partial_mnemonic_words = partial_mnemonic.split()
    
    if len(partial_mnemonic_words) != 11:
        logger.error("You must provide exactly 11 words.")
        return None, 0, None

    logger.info(f"Attempting to recover wallet from {len(partial_mnemonic_words)} words. Trying all possible 12th words.")
    
    wordlist = mnemonic.Mnemonic("english").wordlist

    for word in wordlist:
        full_mnemonic = ' '.join(partial_mnemonic_words + [word])
        mnemonic_phrase, balance, address = recover_wallet_from_mnemonic(full_mnemonic)

        logger.info(f"Trying mnemonic phrase: {full_mnemonic}")
        logger.info(f"Wallet Address: {address}, Balance: {balance} BTC")
        
        if balance > 0:
            logger.info(f"Found wallet with non-zero balance: {balance} BTC")
            logger.info(f"Mnemonic Phrase: {mnemonic_phrase}")
            
            # Store wallet in the scanned_wallets list
            scanned_wallets.append((mnemonic_phrase, address, balance))
            
            with open("wallet.txt", "a") as f:
                f.write(f"Mnemonic Phrase: {mnemonic_phrase}\n")
                f.write(f"Wallet Address: {address}\n")
                f.write(f"Balance: {balance} BTC\n\n")
            break

    return None, 0, None

def display_scanned_wallets():
    """Display the wallets with non-zero balances."""
    console.print("\n[bold cyan]Scanned Wallets with Non-Zero Balance[/bold cyan]\n")
    for mnemonic_phrase, address, balance in scanned_wallets:
        console.print(f"Mnemonic: {mnemonic_phrase[:20]}...", style="bold green")
        console.print(f"Address: {address[:20]}...", style="bold green")
        console.print(f"Balance: {balance:.8f} BTC", style="bold green")
        console.print("-" * 50)

def check_wallets_parallel(mnemonic_phrases):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(recover_wallet_from_mnemonic, phrase) for phrase in mnemonic_phrases]
        
        for future in as_completed(futures):
            mnemonic_phrase, balance, address = future.result()
            logger.info(f"Mnemonic Phrase: {mnemonic_phrase}")
            logger.info(f"Wallet Address: {address}, Balance: {balance} BTC")
            if balance > 0:
                logger.info(f"Found wallet with non-zero balance: {balance} BTC")
                with open("wallet.txt", "a") as f:
                    f.write(f"Mnemonic Phrase: {mnemonic_phrase}\n")
                    f.write(f"Wallet Address: {address}\n")
                    f.write(f"Balance: {balance} BTC\n\n")

def main():
    console.print("[bold green]Welcome to the Bitcoin Wallet Recovery Tool![/bold green]")
    
    choice = input("(1) Recover wallet\n(2) Check random wallets\nType choice: ")

    clear_console()

    if choice == "1":
        partial_mnemonic = input("Enter the words you remember from your mnemonic phrase, separated by spaces: ")
        recover_wallet_from_partial_mnemonic(partial_mnemonic)
    elif choice == "2":
        mnemonic_count = 0
        while True:
            mnemonic_phrases = [generate_mnemonic() for _ in range(500)]  # Generate 500 random mnemonics
            check_wallets_parallel(mnemonic_phrases)
            mnemonic_count += 500
            logger.info(f"Total Mnemonic Phrases generated: {mnemonic_count}")
    else:
        logger.error("Invalid choice. Exiting...")

    # Display scanned wallets in the console
    display_scanned_wallets()

if __name__ == "__main__":
    main()
