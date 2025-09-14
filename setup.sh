#!/bin/bash

# Ensure system packages are up-to-date
apt-get update -y

# Set Streamlit config to improve performance on Cloud
mkdir -p ~/.streamlit

cat <<EOT > ~/.streamlit/config.toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = false
port = \$PORT

[client]
showErrorDetails = true
toolbarMode = "minimal"

[theme]
base="light"
primaryColor="#0E1117"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
textColor="#000000"
EOT
