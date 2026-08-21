import socket
import requests
import subprocess

def test_basic_connection():
    print("=== ТЕСТ СЕТИ ===\n")
    
    # 1. Проверка DNS
    print("1. Проверка DNS...")
    try:
        socket.gethostbyname('google.com')
        print("✅ DNS работает")
    except Exception as e:
        print(f"❌ DNS не работает: {e}")
    
    # 2. Проверка ping
    print("\n2. Проверка ping...")
    try:
        result = subprocess.run(['ping', '-c', '2', '8.8.8.8'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ping работает")
        else:
            print(f"❌ Ping не работает: {result.stderr.decode()}")
    except Exception as e:
        print(f"❌ Ошибка ping: {e}")
    
    # 3. Проверка HTTP с разными таймаутами
    print("\n3. Проверка HTTP...")
    for timeout in [5, 10, 30]:
        try:
            print(f"   Таймаут {timeout} сек...", end=" ")
            r = requests.get('https://www.google.com', timeout=timeout)
            print(f"✅ {r.status_code}")
            break
        except requests.exceptions.Timeout:
            print(f"❌ Таймаут")
        except Exception as e:
            print(f"❌ Ошибка: {type(e).__name__}")
    
    # 4. Проверка Google Sheets API
    print("\n4. Проверка Google Sheets API...")
    try:
        r = requests.get('https://sheets.googleapis.com', timeout=10)
        print(f"✅ Ответ: {r.status_code}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_basic_connection()