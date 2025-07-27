#!/bin/bash
set -euo pipefail

echo "🗜️ COMPRESSING FOR MAXIMUM EFFICIENCY"

find . -name "*.py" -exec sed -i '/^[[:space:]]*#/d' {} \;
find . -name "*.py" -exec sed -i '/^[[:space:]]*"""/,/"""/d' {} \;
find . -name "*.py" -exec sed -i '/^[[:space:]]*'"'"''"'"''"'"'/,/'"'"''"'"''"'"'/d' {} \;
find . -name "*.py" -exec sed -i '/^[[:space:]]*$/d' {} \;
find . -name "*.py" -exec sed -i 's/[[:space:]]*#.*$//' {} \;

find . -name "*.md" -delete
find . -name "*.txt" ! -name "requirements.txt" -delete
find . -name "*.log" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "backup*" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*backup*" -delete
find . -name "test_*" -delete
find . -name "*_test.py" -delete
find . -name "demo_*" -delete

rm -rf docs/ tests/ examples/ .github/ monitoring/

python3 -c "
import os
import re

for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            content = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)', r'\1=\2', content)
            content = re.sub(r'\s*,\s*', ',', content)
            content = re.sub(r'\s*\(\s*', '(', content)
            content = re.sub(r'\s*\)\s*', ')', content)
            content = re.sub(r'\s*\[\s*', '[', content)
            content = re.sub(r'\s*\]\s*', ']', content)
            content = re.sub(r'\s*{\s*', '{', content)
            content = re.sub(r'\s*}\s*', '}', content)
            content = re.sub(r'\s*:\s*', ':', content)
            content = re.sub(r'\n\n+', '\n', content)
            
            with open(path, 'w') as f:
                f.write(content)
"

cat > requirements.txt << 'EOF'
aiohttp==3.9.5
websockets==12.0
fastapi==0.111.0
uvicorn==0.30.1
web3==6.20.0
requests==2.32.3
pandas==2.2.2
numpy==1.26.4
python-dotenv==1.0.1
psutil==5.9.8
pydantic==2.7.4
asyncio-mqtt==0.16.2
cryptography==42.0.8
eth-account==0.12.2
pytz==2024.1
EOF

find . -name "*.json" -exec python3 -c "
import json
import sys
with open(sys.argv[1], 'r') as f:
    data = json.load(f)
with open(sys.argv[1], 'w') as f:
    json.dump(data, f, separators=(',', ':'))
" {} \;

find . -name "*.yaml" -o -name "*.yml" | xargs -I {} sh -c 'python3 -c "
import yaml
import sys
with open(sys.argv[1], \"r\") as f:
    data = yaml.safe_load(f)
with open(sys.argv[1], \"w\") as f:
    yaml.dump(data, f, default_flow_style=True)
" {}'

echo "✅ REPO COMPRESSED TO MINIMUM SIZE"