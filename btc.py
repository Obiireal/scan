import threading
import requests
from mnemonic import Mnemonic
import hashlib
from ecdsa import SigningKey, SECP256k1
import time

# Tải danh sách từ của BIP-39
mnemo = Mnemonic("english")

# Tạo seed phrase
def generate_seed_phrase():
    return mnemo.generate(strength=128)  # 12 từ

# Chuyển seed phrase thành seed
def seed_phrase_to_seed(seed_phrase, passphrase=""):
    return mnemo.to_seed(seed_phrase, passphrase)

# Chuyển seed thành private key
def seed_to_private_key(seed):
    return seed[:32]  # Lấy 32 byte đầu tiên từ seed

# Tạo địa chỉ Bitcoin từ private key
def private_key_to_bitcoin_address(private_key):
    sk = SigningKey.from_string(private_key, curve=SECP256k1)
    vk = sk.verifying_key
    public_key = b"\x04" + vk.to_string()

    # SHA256 -> RIPEMD-160
    sha256 = hashlib.sha256(public_key).digest()
    ripemd160 = hashlib.new("ripemd160")
    ripemd160.update(sha256)
    public_key_hash = ripemd160.digest()

    # Thêm version byte (0x00 cho Bitcoin Mainnet)
    versioned_payload = b"\x00" + public_key_hash

    # Thêm checksum (SHA256 x2)
    checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
    address = versioned_payload + checksum

    # Encode Base58
    return base58_encode(address)

# Base58 encoding
def base58_encode(data):
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    value = int.from_bytes(data, "big")
    encoded = ""
    while value:
        value, mod = divmod(value, 58)
        encoded = alphabet[mod] + encoded
    n_pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * n_pad + encoded

# Truy vấn số dư của địa chỉ qua API
def get_balance_from_address(address):
    try:
        response = requests.get(f"https://api.blockchair.com/bitcoin/dashboards/address/{address}")
        response.raise_for_status()
        data = response.json()
        balance_satoshis = data["data"][address]["address"]["balance"]
        return balance_satoshis / 1e8  # Chuyển từ satoshi sang BTC
    except Exception as e:
        print(f"Error fetching balance for {address}: {e}")
    return 0

# Xử lý seed phrase trong một luồng
def process_seed_phrase(seed_phrase):
    seed = seed_phrase_to_seed(seed_phrase)
    private_key = seed_to_private_key(seed)
    address = private_key_to_bitcoin_address(private_key)

    balance = get_balance_from_address(address)
    if balance > 0:
        save_to_file(seed_phrase, "Bitcoin Wallet", balance)
        print(f"FOUND BTC! Address: {address}, Balance: {balance} BTC")

# Lưu seed phrase vào file
def save_to_file(seed_phrase, wallet_name, balance):
    with open("found_wallets.txt", "a") as file:
        file.write(f"{wallet_name} | {seed_phrase} | {balance} BTC\n")

# Chạy song song 100 seed phrase mỗi giây
def run_threads():
    threads = []
    for _ in range(100):  # Tạo 100 seed phrase song song
        seed_phrase = generate_seed_phrase()
        thread = threading.Thread(target=process_seed_phrase, args=(seed_phrase,))
        threads.append(thread)
        thread.start()

    # Đợi tất cả các luồng hoàn thành
    for thread in threads:
        thread.join()

# Chương trình chính
if __name__ == "__main__":
    while True:
        start_time = time.time()
        run_threads()  # Chạy 100 seed phrase song song
        elapsed_time = time.time() - start_time
        print(f"Processed 100 seed phrases in {elapsed_time:.2f} seconds")
