#!/bin/bash
# Build script for Render deployment
# ChromaDB is committed to git, no ingestion needed

echo "============================================"
echo "  AI Chat Flow - Render Build Script"
echo "============================================"
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo ""
echo "Using pre-built ChromaDB from repository"
echo "Skipping document ingestion..."
echo ""
echo "Build completed successfully!"
echo "============================================"