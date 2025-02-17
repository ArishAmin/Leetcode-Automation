from flask import Flask, render_template, request, jsonify
from model import LeetCodeBot
import threading
import os
import traceback

app = Flask(__name__)
bot = None
bot_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-bot', methods=['POST'])
def start_bot():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        try:
            problem_count = int(data.get('problemCount', 1))
            if problem_count < 1 or problem_count > 10:
                return jsonify({'error': 'Problem count must be between 1 and 10'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid problem count'}), 400

        global bot, bot_thread
        
        # Stop existing bot if running
        if bot and bot.running:
            return jsonify({'error': 'Bot is already running'}), 409
        
        # Clean up old bot instance
        if bot:
            try:
                bot.stop()
            except:
                pass
        
        # Create new bot instance
        try:
            bot = LeetCodeBot()
        except Exception as e:
            return jsonify({'error': f'Failed to initialize bot: {str(e)}'}), 500

        bot.set_problem_count(problem_count)
        bot.running = True
        
        # Start bot in a separate thread
        try:
            bot_thread = threading.Thread(target=bot.start_solving)
            bot_thread.daemon = True
            bot_thread.start()
        except Exception as e:
            bot.running = False
            return jsonify({'error': f'Failed to start bot thread: {str(e)}'}), 500
        
        return jsonify({
            'message': 'Bot started successfully',
            'problemCount': problem_count
        }), 202

    except Exception as e:
        error_msg = f"Error starting bot: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/bot-status')
def bot_status():
    try:
        if not bot:
            return jsonify({
                'status': 'Not initialized',
                'is_running': False,
                'is_loading': False,
                'current_problem': None,
                'solved_problems': []
            })
        
        status_info = bot.get_status()
        current_problem = bot.get_current_problem()
        solved_problems = bot.get_solved_problems()
        
        return jsonify({
            'status': status_info.get('status', 'Unknown'),
            'is_running': bot.running,
            'is_loading': status_info.get('is_loading', False),
            'current_problem': current_problem,
            'solved_problems': solved_problems,
            'total_solved': len(solved_problems)
        })

    except Exception as e:
        error_msg = f"Error getting bot status: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/stop-bot', methods=['POST'])
def stop_bot():
    try:
        global bot, bot_thread
        
        if not bot:
            return jsonify({'message': 'Bot is not running'}), 200
            
        if not bot.running:
            return jsonify({'message': 'Bot is already stopped'}), 200
        
        try:
            bot.stop()
            if bot_thread:
                bot_thread.join(timeout=5)
        except Exception as e:
            return jsonify({'error': f'Error stopping bot: {str(e)}'}), 500
        finally:
            bot = None
            bot_thread = None
        
        return jsonify({'message': 'Bot stopped successfully'})

    except Exception as e:
        error_msg = f"Error stopping bot: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)