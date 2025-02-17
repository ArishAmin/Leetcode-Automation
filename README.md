# LeetCode Bot Automation

This project is a Flask-based web application that automates solving random LeetCode problems using Selenium and a machine learning model for code generation.

## Note
- Make sure you have Google Chrome installed.
- The script runs headless by default but can be modified to display the browser for debugging.
- You can use any other more optimized LLM that has more parameters for better response.

## Features
- Fetches random LeetCode problems.
- Selects Python3 as the coding language.
- Uses codegen-350M-mono to generate solutions.
- Tracks the status of the solving process.

## Technologies Used
- **Flask** - For the web interface.
- **Selenium** - To interact with the LeetCode website.
- **Transformers** - For AI-based code generation(codegen-350M-mono).
- **BeautifulSoup** - To parse HTML content.
- **Chromedriver Autoinstaller** - For seamless Selenium setup.

