#!/bin/bash
# API Key Management Script

set -euo pipefail

KEYS_DIR="data/keys"
ENCRYPTED_KEYS_DIR="$KEYS_DIR/encrypted"

mkdir -p "$ENCRYPTED_KEYS_DIR"
chmod 700 "$KEYS_DIR" "$ENCRYPTED_KEYS_DIR"

# Encrypt API key
encrypt_key() {
    local key_name="$1"
    local key_value="$2"
    
    echo "$key_value" | openssl enc -aes-256-cbc -salt -pbkdf2 -out "$ENCRYPTED_KEYS_DIR/$key_name.enc"
    echo "Key $key_name encrypted and stored securely"
}

# Decrypt API key
decrypt_key() {
    local key_name="$1"
    
    if [ ! -f "$ENCRYPTED_KEYS_DIR/$key_name.enc" ]; then
        echo "Error: Key $key_name not found"
        exit 1
    fi
    
    openssl enc -aes-256-cbc -d -salt -pbkdf2 -in "$ENCRYPTED_KEYS_DIR/$key_name.enc"
}

# List stored keys
list_keys() {
    echo "Stored encrypted keys:"
    ls -la "$ENCRYPTED_KEYS_DIR"/*.enc 2>/dev/null | awk '{print $9}' | sed 's/.*\///' | sed 's/\.enc$//' || echo "No keys found"
}

# Main command handler
case "${1:-}" in
    "encrypt")
        if [ $# -ne 3 ]; then
            echo "Usage: $0 encrypt <key_name> <key_value>"
            exit 1
        fi
        encrypt_key "$2" "$3"
        ;;
    "decrypt")
        if [ $# -ne 2 ]; then
            echo "Usage: $0 decrypt <key_name>"
            exit 1
        fi
        decrypt_key "$2"
        ;;
    "list")
        list_keys
        ;;
    *)
        echo "Usage: $0 {encrypt|decrypt|list}"
        echo "Examples:"
        echo "  $0 encrypt okx_api_key 'your-api-key-here'"
        echo "  $0 decrypt okx_api_key"
        echo "  $0 list"
        exit 1
        ;;
esac
