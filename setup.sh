#!/bin/bash

echo "=========================================="
echo "Learning Sequence Manager - Setup Script"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    # Generate a secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Replace placeholder in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-this/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-this/$SECRET_KEY/" .env
    fi
    
    echo "✅ .env file created with random SECRET_KEY"
    echo "⚠️  Please edit .env and set your ADMIN_USERNAME and ADMIN_PASSWORD"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Check if database exists
if [ ! -f learning_sequence_v2.db ]; then
    echo "❌ Database file not found: learning_sequence_v2.db"
    echo "   Please ensure the database file is in this directory"
    exit 1
else
    echo "✅ Database file found"
    echo ""
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "   Please install Python 3.8 or higher"
    exit 1
else
    echo "✅ Python 3 found: $(python3 --version)"
    echo ""
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed"
    echo "   Please install pip3"
    exit 1
else
    echo "✅ pip3 found"
    echo ""
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Setup complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file and set your admin credentials"
    echo "2. Run the app: python3 app.py"
    echo "3. Open browser: http://localhost:8080"
    echo ""
else
    echo ""
    echo "❌ Failed to install dependencies"
    echo "   Please check the error messages above"
    exit 1
fi
