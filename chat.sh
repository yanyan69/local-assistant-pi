#!/bin/bash
SERVER_URL="http://192.168.11.186:5000/api/robot"

clear
echo "============================================="
echo "🤖 OFFLINE ROBOT CORE ASSISTANT CONSOLE 🤖"
echo " Type your command or question below.        "
echo " Type 'exit' or 'quit' to close.            "
echo "============================================="
echo ""

while true; do
    # Read user input prompt
    read -p "You >>> " USER_INPUT
    
    # Check if the user wants to leave the environment
    if [[ "$USER_INPUT" == "exit" || "$USER_INPUT" == "quit" ]]; then
        echo "Closing connection. Goodbye!"
        break
    fi
    
    # Skip empty returns
    if [[ -z "$USER_INPUT" ]]; then
        continue
    fi
    
    echo "Sending to server..."
    
    # Transmit the payload over the offline router network
    RESPONSE=$(curl -s -X POST "$SERVER_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"$USER_INPUT\"}")
        
    # Print the clean response string from the server
    echo "Bot >>> $RESPONSE"
    echo ""
done
