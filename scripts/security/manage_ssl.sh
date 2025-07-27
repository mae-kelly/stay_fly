#!/bin/bash
# SSL Certificate Management

set -euo pipefail

CERT_DIR="nginx/ssl"
DOMAINS=${DOMAINS:-"localhost"}

# Create self-signed certificate
create_self_signed() {
    echo "Creating self-signed certificate..."
    
    mkdir -p "$CERT_DIR"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
        -keyout "$CERT_DIR/selfsigned.key" \
        -out "$CERT_DIR/selfsigned.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAINS"
    
    chmod 600 "$CERT_DIR/selfsigned.key"
    chmod 644 "$CERT_DIR/selfsigned.crt"
    
    echo "✅ Self-signed certificate created"
}

# Setup Let's Encrypt certificate
setup_letsencrypt() {
    echo "Setting up Let's Encrypt certificate..."
    
    # Install certbot if not available
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        apt-get update && apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Stop nginx temporarily
    systemctl stop nginx 2>/dev/null || docker-compose stop nginx 2>/dev/null || true
    
    # Obtain certificate
    certbot certonly --standalone -d "$DOMAINS" --non-interactive --agree-tos --email admin@example.com
    
    # Copy certificates to nginx directory
    cp "/etc/letsencrypt/live/$DOMAINS/fullchain.pem" "$CERT_DIR/fullchain.pem"
    cp "/etc/letsencrypt/live/$DOMAINS/privkey.pem" "$CERT_DIR/privkey.pem"
    
    chmod 600 "$CERT_DIR/privkey.pem"
    chmod 644 "$CERT_DIR/fullchain.pem"
    
    # Setup auto-renewal
    echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
    
    echo "✅ Let's Encrypt certificate setup complete"
}

# Check certificate expiration
check_expiration() {
    if [ -f "$CERT_DIR/selfsigned.crt" ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_DIR/selfsigned.crt" | cut -d= -f2)
        echo "Certificate expires: $EXPIRY"
        
        # Check if expiring within 30 days
        if openssl x509 -checkend 2592000 -noout -in "$CERT_DIR/selfsigned.crt"; then
            echo "✅ Certificate is valid for more than 30 days"
        else
            echo "⚠️ Certificate expires within 30 days"
        fi
    else
        echo "❌ No certificate found"
    fi
}

# Renew certificate
renew_certificate() {
    echo "Renewing certificate..."
    
    if [ -f "/etc/letsencrypt/live/$DOMAINS/fullchain.pem" ]; then
        certbot renew --quiet
        cp "/etc/letsencrypt/live/$DOMAINS/fullchain.pem" "$CERT_DIR/fullchain.pem"
        cp "/etc/letsencrypt/live/$DOMAINS/privkey.pem" "$CERT_DIR/privkey.pem"
        echo "✅ Certificate renewed"
    else
        echo "❌ No Let's Encrypt certificate found"
    fi
}

# Main command handler
case "${1:-}" in
    "self-signed")
        create_self_signed
        ;;
    "letsencrypt")
        setup_letsencrypt
        ;;
    "check")
        check_expiration
        ;;
    "renew")
        renew_certificate
        ;;
    *)
        echo "SSL Certificate Management"
        echo "Usage: $0 {self-signed|letsencrypt|check|renew}"
        echo ""
        echo "Commands:"
        echo "  self-signed  - Create self-signed certificate"
        echo "  letsencrypt  - Setup Let's Encrypt certificate"
        echo "  check        - Check certificate expiration"
        echo "  renew        - Renew Let's Encrypt certificate"
        echo ""
        echo "Environment variables:"
        echo "  DOMAINS - Domain names for certificate (default: localhost)"
        exit 1
        ;;
esac
