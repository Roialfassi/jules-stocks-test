from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from services.auth import auth_service
from services.trading import trading_service
from services.market_data import market_data
from services.gamification import gamification_service
from services.research import research_service
from utils.decorators import login_required, admin_required
from tasks.scheduler import init_scheduler
import csv
import io

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

if Config.SCHEDULER_API_ENABLED:
    init_scheduler(app)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per 15 minute")
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Try logging in with the unified interface (REST for Firebase, DB check for SQLite)
    user = auth_service.login_user(email, password)

    if user and 'id' in user:
        session['user_id'] = user['id']
        # Log login
        research_service.log_action(user['id'], 'LOGIN')
        gamification_service.check_daily_login(user['id'])
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')
    consent = data.get('consent', False)

    try:
        uid, user_data = auth_service.register_user(email, password, username, consent)
        if uid:
            session['user_id'] = uid
            research_service.log_action(uid, 'REGISTER', {'group': user_data['researchGroup']})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Registration failed'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/password-reset', methods=['POST'])
@limiter.limit("3 per hour")
def password_reset():
    # Stub: In real app, send email via Firebase or SMTP
    email = request.json.get('email')
    if email:
        return jsonify({'success': True, 'message': 'Reset email sent'})
    return jsonify({'error': 'Email required'}), 400

@app.route('/dashboard')
@login_required
def dashboard():
    user = auth_service.get_user(session['user_id'])
    balance = trading_service.get_balance(session['user_id'])

    # Check achievements logic for notification
    achievements = gamification_service.get_recent_achievements(session['user_id'])

    # Leaderboard for group 4
    leaderboard = []
    if user.get('researchGroup') == 4:
        leaderboard = gamification_service.get_leaderboard()

    return render_template('dashboard.html',
                          user=user,
                          balance=balance,
                          achievements=achievements,
                          leaderboard=leaderboard)

@app.route('/trading')
@login_required
def trading():
    user = auth_service.get_user(session['user_id'])
    return render_template('trading.html', user=user)

@app.route('/portfolio')
@login_required
def portfolio():
    user = auth_service.get_user(session['user_id'])
    return render_template('portfolio.html', user=user)

@app.route('/profile')
@login_required
def profile():
    user = auth_service.get_user(session['user_id'])
    stats = trading_service.get_balance(session['user_id'])
    gamification = gamification_service.get_user_gamification(session['user_id'])
    achievements = gamification_service.get_all_achievements(session['user_id'])
    return render_template('profile.html', user=user, stats=stats, gamification=gamification, achievements=achievements)

@app.route('/admin')
@admin_required
def admin():
    stats = research_service.get_study_stats()
    return render_template('admin.html', stats=stats)

# Trading API
@app.route('/api/assets/search')
@login_required
def search_assets():
    query = request.args.get('q', '')
    results = market_data.search_assets(query)
    return jsonify(results)

@app.route('/api/assets/<symbol>/price')
@login_required
def get_price(symbol):
    price = market_data.get_price(symbol)
    if price:
        return jsonify({'symbol': symbol, 'price': price})
    return jsonify({'error': 'Asset not found'}), 404

@app.route('/api/assets/<symbol>/history')
@login_required
def get_history(symbol):
    history = market_data.get_history(symbol)
    return jsonify(history)

@app.route('/api/trade', methods=['POST'])
@login_required
def trade():
    data = request.json
    symbol = data.get('symbol')
    action = data.get('action') # BUY or SELL
    quantity = float(data.get('quantity'))

    result = trading_service.execute_trade(session['user_id'], symbol, quantity, action)
    if result['success']:
        # Log research data
        research_service.log_action(session['user_id'], 'TRADE', {
            'symbol': symbol, 'action': action, 'quantity': quantity,
            'price': result['price'], 'tx_id': result['transaction_id']
        })

        # Gamification checks
        gamification_service.check_trade_achievements(session['user_id'], result)
        gamification_service.award_xp(session['user_id'], 10)

    return jsonify(result)

@app.route('/api/portfolio')
@login_required
def get_portfolio_data():
    portfolio = trading_service.get_portfolio(session['user_id'])
    # Firestore stream to list of dicts
    holdings = [doc.to_dict() for doc in portfolio]
    return jsonify(holdings)

@app.route('/api/portfolio/history')
@login_required
def get_portfolio_history():
    history = trading_service.get_portfolio_history(session['user_id'])
    return jsonify(history)

@app.route('/api/research/action', methods=['POST'])
@login_required
def log_research_action():
    data = request.json
    action_type = data.get('actionType')
    details = data.get('details')
    research_service.log_action(session['user_id'], action_type, details)
    return jsonify({'success': True})

@app.route('/api/achievements')
@login_required
def get_achievements():
    achs = gamification_service.get_all_achievements(session['user_id'])
    return jsonify(achs)

@app.route('/api/gamification/stats')
@login_required
def get_gamification_stats():
    stats = gamification_service.get_user_gamification(session['user_id'])
    return jsonify(stats)

@app.route('/api/leaderboard')
@login_required
def get_leaderboard():
    board = gamification_service.get_leaderboard()
    return jsonify(board)

# Admin Exports
@app.route('/api/admin/export/users')
@admin_required
def export_users():
    csv_data = research_service.export_users_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=users.csv"}
    )

@app.route('/api/admin/export/trades')
@admin_required
def export_trades():
    csv_data = research_service.export_trades_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=trades.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
