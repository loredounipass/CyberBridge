#!/usr/bin/env bash
# Build Android APK for CyberBridge client
set -e
cd "$(dirname "$0")"

# Install buildozer if not present
if ! command -v buildozer &> /dev/null; then
    pip install buildozer
fi

# Copy needed files to build dir
mkdir -p build_android
cp main.py config.py build_android/
cp ../requirements.txt build_android/

# Create buildozer.spec if not exists
if [ ! -f build_android/buildozer.spec ]; then
cat > build_android/buildozer.spec << 'EOF'
[app]
title = CyberBridge Client
package.name = cyberbridgeclient
package.domain = org.cyberbridge
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,requests,Pillow,mss,psutil
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
EOF
fi

cd build_android
buildozer android debug
echo "APK built at: bin/cyberbridgeclient-1.0-debug.apk"
