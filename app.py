import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_talisman import Talisman
import bcrypt

from config import config
from services import sqlite_service, trading_service, gamification, research_service, market_data
from utils import decorators, validators
from tasks import scheduler

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # --- Extensions Initialization ---
    csrf = CSRFProtect(app)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URI')
    )
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    if os.environ.get('FLASK_ENV') == 'production':
        talisman = Talisman(app, content_security_policy=app.config['CSP'])

    # --- Database Initialization ---
    if config_name != 'testing':
        sqlite_service.init_app(app)


    # --- Background Scheduler ---
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or os.environ.get('FLASK_ENV') == 'production':
        scheduler.init_app(app)

    # --- Before/After Request ---
    @app.after_request
    def inject_csrf_token(response):
        response.headers.set('X-CSRF-Token', generate_csrf())
        return response

    # --- HTML Page Routes ---
    @app.route('/')
    def index():
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/register')
    def register():
        return render_template('register.html')

    @app.route('/dashboard')
    @decorators.login_required
    def dashboard():
        return render_template('dashboard.html', user=session.get('user'))

    @app.route('/trading')
    @decorators.login_required
    def trading():
        return render_template('trading.html', user=session.get('user'))

    @app.route('/portfolio')
    @decorators.login_required
    def portfolio():
        return render_template('portfolio.html', user=session.get('user'))

    @app.route('/profile')
    @decorators.login_required
    def profile():
        return render_template('profile.html', user=session.get('user'))

    @app.route('/admin')
    @decorators.login_required
    @decorators.admin_required
    def admin():
        return render_template('admin.html', user=session.get('user'))

    # --- API Routes ---

    # == Authentication API ==
    @app.route('/api/register', methods=['POST'])
    def api_register():
        data = request.get_json()
        if not all(k in data for k in ['email', 'password', 'username', 'consent']):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        if not data['consent']:
            return jsonify({'status': 'error', 'message': 'Consent is required'}), 400

        is_valid, msg = validators.is_strong_password(data['password'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': msg}), 400

        try:
            sqlite_service.create_user_with_group(
                data['email'], data['password'], data['username'],
                data['consent'], request.remote_addr
            )
            return jsonify({'status': 'success', 'message': 'User registered successfully'})
        except ValueError as e:
            return jsonify({'status': 'error', 'message': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500

    @app.route('/api/session-login', methods=['POST'])
    def api_session_login():
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

        user = sqlite_service.get_user_by_email(email)

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        # Using user.id to avoid conflict with session's 'user' object
        session['user_id'] = user['id']
        session['user'] = {
            'uid': user['id'],
            'email': user['email'],
            'username': user['username'],
            'researchGroup': user['researchGroup'],
            'role': user['role']
        }
        return jsonify({'status': 'success'})

    @app.route('/api/logout', methods=['POST'])
    def api_logout():
        session.clear()
        return jsonify({"status": "success", "message": "Logged out"})

    @app.route('/api/password-reset', methods=['POST'])
    def api_password_reset():
        # This is a placeholder as password reset is not implemented for SQLite version
        return jsonify({'status': 'info', 'message': 'Password reset is not available in this version.'})

    # == User API ==
    @app.route('/api/user/profile')
    @decorators.login_required
    def api_get_user_profile():
        user_row = sqlite_service.get_user_by_id(session['user']['uid'])
        if user_row:
            user_dict = dict(user_row)
            del user_dict['password']  # Never send password hash to client
            return jsonify(user_dict)
        return jsonify({}), 404

    @app.route('/api/user/balance')
    @decorators.login_required
    def api_get_user_balance():
        db = sqlite_service.get_db()
        balance = db.execute('SELECT * FROM balances WHERE user_id = ?', (session['user']['uid'],)).fetchone()
        if balance:
            return jsonify(dict(balance))
        return jsonify({'cashBalance': 10000, 'totalPortfolioValue': 10000}), 404

    @app.route('/api/user/delete', methods=['DELETE'])
    @decorators.login_required
    def api_delete_user():
        uid = session['user']['uid']
        try:
            db = sqlite_service.get_db()
            db.execute('DELETE FROM users WHERE id = ?', (uid,))
            db.execute('DELETE FROM balances WHERE user_id = ?', (uid,))
            db.execute('DELETE FROM transactions WHERE user_id = ?', (uid,))
            db.execute('DELETE FROM holdings WHERE user_id = ?', (uid,))
            db.execute('DELETE FROM gamification WHERE user_id = ?', (uid,))
            db.execute('DELETE FROM achievements WHERE user_id = ?', (uid,))
            db.commit()
            session.clear()
            return jsonify({'status': 'success', 'message': 'Account deleted successfully'})
        except Exception as e:
            app.logger.error(f"Error deleting user {uid}: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to delete account'}), 500

    # == Trading API ==
    @app.route('/api/assets/search')
    @decorators.login_required
    def api_search_assets():
        query = request.args.get('q', '')
        results = market_data.search_assets(query)
        return jsonify(results)

    @app.route('/api/assets/<symbol>/price')
    @decorators.login_required
    def api_get_asset_price(symbol):
        details = market_data.get_asset_details(symbol)
        if not details:
            return jsonify({'status': 'error', 'message': 'Asset not found'}), 404
        details['price'] = market_data.get_current_price(symbol)
        return jsonify(details)

    @app.route('/api/assets/<symbol>/history')
    @decorators.login_required
    def api_get_asset_history(symbol):
        period = request.args.get('period', '1mo')
        history = market_data.get_historical_data(symbol, period=period)
        if history:
            return jsonify(history)
        return jsonify([]), 404

    @app.route('/api/trade/buy', methods=['POST'])
    @decorators.login_required
    def api_buy():
        data = request.get_json()
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        if not all([symbol, quantity]) or not validators.is_valid_quantity(quantity):
            return jsonify({'status': 'error', 'message': 'Invalid symbol or quantity'}), 400

        result = trading_service.execute_buy_order(session['user']['uid'], symbol, quantity)
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    @app.route('/api/trade/sell', methods=['POST'])
    @decorators.login_required
    def api_sell():
        data = request.get_json()
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        if not all([symbol, quantity]) or not validators.is_valid_quantity(quantity):
            return jsonify({'status': 'error', 'message': 'Invalid symbol or quantity'}), 400

        result = trading_service.execute_sell_order(session['user']['uid'], symbol, quantity)
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    # == Portfolio API ==
    @app.route('/api/portfolio/holdings')
    @decorators.login_required
    def api_get_holdings():
        holdings = trading_service.get_portfolio_holdings(session['user']['uid'])
        return jsonify(holdings)

    @app.route('/api/portfolio/value_history')
    @decorators.login_required
    def api_get_portfolio_history():
        # This is a simplified version. A real implementation would aggregate daily snapshots.
        transactions = trading_service.get_transaction_history(session['user']['uid'])
        history = [{'timestamp': tx['timestamp'], 'value': tx.get('portfolioValueAfter', 10000)} for tx in transactions]
        history.reverse()
        if not history:
            user = sqlite_service.get_user_by_id(session['user']['uid'])
            if user:
                history.append({'timestamp': user['createdAt'].isoformat(), 'value': 10000})
        return jsonify(history)

    @app.route('/api/transactions')
    @decorators.login_required
    def api_get_transactions():
        limit = request.args.get('limit', type=int)
        transactions = trading_service.get_transaction_history(session['user']['uid'])
        if limit:
            transactions = transactions[:limit]
        # Convert datetime objects to strings
        for tx in transactions:
            tx['timestamp'] = tx['timestamp'].isoformat()
        return jsonify(transactions)

    # == Gamification API ==
    @app.route('/api/achievements')
    @decorators.login_required
    def api_get_achievements():
        return jsonify(list(gamification.ACHIEVEMENTS.values()))

    @app.route('/api/achievements/progress')
    @decorators.login_required
    def api_get_achievement_progress():
        db = sqlite_service.get_db()
        progress_rows = db.execute('SELECT * FROM achievements WHERE user_id = ?', (session['user']['uid'],)).fetchall()
        progress = []
        for row in progress_rows:
            p = dict(row)
            if p.get('completedAt'):
                p['completedAt'] = p['completedAt'].isoformat()
            progress.append(p)
        return jsonify(progress)

    @app.route('/api/gamification/stats')
    @decorators.login_required
    def api_get_gamification_stats():
        db = sqlite_service.get_db()
        stats_row = db.execute('SELECT * FROM gamification WHERE user_id = ?', (session['user']['uid'],)).fetchone()
        if stats_row:
            return jsonify(dict(stats_row))
        return jsonify({}), 404

    @app.route('/api/leaderboard')
    @decorators.login_required
    def api_get_leaderboard():
        if session['user']['researchGroup'] != 4:
            return jsonify({'status': 'error', 'message': 'Not available for your group'}), 403
        leaderboard = gamification.get_leaderboard()
        return jsonify(leaderboard)

    # == Market Data API ==
    @app.route('/api/market/popular')
    @decorators.login_required
    def api_get_popular_assets():
        assets = []
        for symbol in market_data.POPULAR_STOCKS[:5] + market_data.POPULAR_CRYPTO[:5]:
            details = market_data.get_asset_details(symbol)
            if details:
                price = market_data.get_current_price(symbol)
                change = ((price - details['previousClose']) / details['previousClose']) * 100 if details.get('previousClose') else 0
                assets.append({'symbol': symbol, 'name': details['name'], 'price': price, 'change': change})
        return jsonify(assets)

    # == Research API (Admin only) ==
    @app.route('/api/research/analytics')
    @decorators.login_required
    @decorators.admin_required
    def api_get_admin_analytics():
        analytics = research_service.get_admin_dashboard_analytics()
        return jsonify(analytics)

    @app.route('/api/research/users')
    @decorators.login_required
    @decorators.admin_required
    def api_get_all_users():
        db = sqlite_service.get_db()
        users_rows = db.execute('SELECT id, username, email, participantId, researchGroup, consentGiven, consentTimestamp, createdAt, lastLogin, role FROM users').fetchall()
        users = []
        for row in users_rows:
            user_data = dict(row)
            user_data['createdAt'] = user_data['createdAt'].isoformat()
            if user_data.get('lastLogin'):
                user_data['lastLogin'] = user_data['lastLogin'].isoformat()
            if user_data.get('consentTimestamp'):
                user_data['consentTimestamp'] = user_data['consentTimestamp'].isoformat()
            users.append(user_data)
        return jsonify(users)

    @app.route('/api/research/export')
    @decorators.login_required
    @decorators.admin_required
    def api_export_data():
        collection = request.args.get('collection')
        if not collection:
            return jsonify({'status': 'error', 'message': 'Collection parameter is required'}), 400

        csv_data = research_service.export_data_to_csv(collection)
        if csv_data:
            return jsonify({'status': 'success', 'csv': csv_data})
        return jsonify({'status': 'error', 'message': f'Could not export {collection}'}), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=app.config['DEBUG'])