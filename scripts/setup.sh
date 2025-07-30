#!/bin/bash

# Document Intelligence Platform Setup Script

set -e

echo "🚀 Setting up Document Intelligence Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
else
    echo "✅ .env file already exists."
fi

# Create uploads directory
if [ ! -d uploads ]; then
    echo "📁 Creating uploads directory..."
    mkdir -p uploads
    echo "✅ Uploads directory created."
else
    echo "✅ Uploads directory already exists."
fi

# Check if .env has been configured
if grep -q "your-supabase-url" .env; then
    echo "⚠️  Warning: Please configure your .env file with your Supabase credentials."
    echo "   Required variables:"
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_KEY"
    echo "   - SECRET_KEY"
    echo "   - DATABASE_URL"
fi

echo ""
echo "📋 Setup complete! Next steps:"
echo ""
echo "1. Edit .env file with your configuration:"
echo "   - SUPABASE_URL: Your Supabase project URL"
echo "   - SUPABASE_KEY: Your Supabase anon key"
echo "   - SECRET_KEY: A strong secret key for JWT"
echo "   - DATABASE_URL: Your PostgreSQL connection string"
echo ""
echo "2. Set up your Supabase database:"
echo "   - Run the SQL from database_schema.sql in your Supabase SQL editor"
echo ""
echo "3. Start the application:"
echo "   docker-compose up -d"
echo ""
echo "4. Access the application:"
echo "   - API: http://localhost:8000"
echo "   - Documentation: http://localhost:8000/docs"
echo "   - Celery Flower: http://localhost:5555"
echo ""
echo "🎉 Happy coding!"