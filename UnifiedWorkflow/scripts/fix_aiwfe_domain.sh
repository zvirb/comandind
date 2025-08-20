#!/bin/bash

# Fix aiwfe.com domain resolution for local development
# This script adds DNS overrides to /etc/hosts

echo "🔧 Fixing aiwfe.com domain resolution for local development..."

# Check if entries already exist
if grep -q "aiwfe.com" /etc/hosts; then
    echo "⚠️  aiwfe.com entries already exist in /etc/hosts"
    echo "Current entries:"
    grep "aiwfe.com" /etc/hosts
    read -p "Do you want to replace them? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing entries
        sudo sed -i '/aiwfe\.com/d' /etc/hosts
        echo "✅ Removed existing aiwfe.com entries"
    else
        echo "❌ Operation cancelled"
        exit 1
    fi
fi

# Add new entries
echo "Adding DNS overrides to /etc/hosts..."
echo "" | sudo tee -a /etc/hosts > /dev/null
echo "# Local development override for aiwfe.com (added $(date))" | sudo tee -a /etc/hosts > /dev/null
echo "127.0.0.1 aiwfe.com" | sudo tee -a /etc/hosts > /dev/null
echo "127.0.0.1 www.aiwfe.com" | sudo tee -a /etc/hosts > /dev/null

echo "✅ DNS overrides added successfully"

# Verify the changes
echo ""
echo "🔍 Verifying DNS resolution:"
echo "Before: aiwfe.com resolved to external IP"
echo "After:"
nslookup aiwfe.com | grep -A1 "Non-authoritative answer:"

echo ""
echo "🧪 Testing API connectivity:"
echo "Testing localhost (should work):"
curl -s -k https://localhost/api/v1/health 2>/dev/null && echo "✅ localhost API working" || echo "❌ localhost API failed"

echo "Testing aiwfe.com (should now work):"
curl -s -k https://aiwfe.com/api/v1/health 2>/dev/null && echo "✅ aiwfe.com API working" || echo "❌ aiwfe.com API failed"

echo ""
echo "🚀 Fix complete! Please:"
echo "1. Restart your browser or open in incognito mode"
echo "2. Access https://aiwfe.com"
echo "3. Try logging in - API calls should now work"

echo ""
echo "To undo this fix later, remove these lines from /etc/hosts:"
echo "127.0.0.1 aiwfe.com"
echo "127.0.0.1 www.aiwfe.com"