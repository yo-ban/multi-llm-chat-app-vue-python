"""
暗号化ユーティリティ

Fernetを使用したデータの暗号化と復号化機能
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# 環境変数から暗号化キーを読み込み
# Fernet.generate_key()を使用してキーを生成し、安全に保管してください
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY environment variable not set.")

# キーがバイト形式であることを確認
ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()

# Fernetインスタンスを作成
f = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> bytes:
    """
    文字列データを暗号化する
    
    Args:
        data: 暗号化する文字列
        
    Returns:
        暗号化されたバイトデータ
    """
    if not data:
        return b''  # データが空の場合は空のバイトを返す
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    """
    暗号化されたバイトデータを復号化する
    
    Args:
        encrypted_data: 復号化するバイトデータ
        
    Returns:
        復号化された文字列
    """
    if not encrypted_data:
        return ''  # データが空の場合は空の文字列を返す
    return f.decrypt(encrypted_data).decode() 