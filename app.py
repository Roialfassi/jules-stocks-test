import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_talisman import Talisman

from config import config
from services import firebase_service, trading_service, gamification, research_service, market_data
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
        storage_uri=app.config['RATELIMIT_STORAGE_URI']
    )
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    if os.environ.get('FLASK_ENV') == 'production':
        talisman = Talisman(app, content_security_policy=app.config['CSP'])

    # --- Firebase Initialization ---
    try:
        firebase_service.initialize_firebase(app.config['FIREBASE_CONFIG_PATH'])
    except Exception as e:
        print(f"CRITICAL: Could not initialize Firebase. Error: {e}")

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
            firebase_service.create_user_with_group(
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
        id_token = request.json.get('token')
        decoded_token = firebase_service.verify_token(id_token)
        if not decoded_token:
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

        uid = decoded_token['uid']
        user_profile = firebase_service.get_user(uid)
        if not user_profile:
            return jsonify({'status': 'error', 'message': 'User profile not found in database'}), 404

        session['user_token'] = id_token
        session['user'] = {
            'uid': uid, 'email': user_profile.get('email'), 'username': user_profile.get('username'),
            'researchGroup': user_profile.get('researchGroup'), 'role': user_profile.get('role', 'user')
        }
        return jsonify({'status': 'success'})

    @app.route('/api/logout', methods=['POST'])
    def api_logout():
        session.clear()
        return jsonify({"status": "success", "message": "Logged out"})

    @app.route('/api/password-reset', methods=['POST'])
    def api_password_reset():
        email = request.json.get('email')
        if not validators.is_valid_email(email):
            return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400

        success = firebase_service.send_password_reset_email(email)
        if success:
            return jsonify({'status': 'success', 'message': 'If an account exists for this email, a password reset link has been sent.'})
        return jsonify({'status': 'error', 'message': 'Failed to send reset email'}), 500

    # == User API ==
    @app.route('/api/user/profile')
    @decorators.login_required
    def api_get_user_profile():
        user = firebase_service.get_user(session['user']['uid'])
        return jsonify(user)

    @app.route('/api/user/balance')
    @decorators.login_required
    def api_get_user_balance():
        balance_ref = firebase_service.db.collection('balances').document(session['user']['uid'])
        balance = balance_ref.get()
        if balance.exists:
            return jsonify(balance.to_dict())
        return jsonify({'cashBalance': 10000, 'totalPortfolioValue': 10000}), 404

    @app.route('/api/user/delete', methods=['DELETE'])
    @decorators.login_required
    def api_delete_user():
        # A real implementation would be more complex, handling data archival.
        uid = session['user']['uid']
        try:
            # Delete from Auth
            firebase_service.auth.delete_user(uid)
            # Delete from Firestore (users, balances, etc.)
            firebase_service.db.collection('users').document(uid).delete()
            firebase_service.db.collection('balances').document(uid).delete()
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
        history = [{'timestamp': tx['timestamp'].isoformat(), 'value': tx.get('portfolioValueAfter', 10000)} for tx in transactions]
        history.reverse()
        if not history:
             history.append({'timestamp': firebase_service.get_user(session['user']['uid'])['createdAt'].isoformat(), 'value': 10000})
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
        progress_docs = firebase_service.db.collection('users').document(session['user']['uid']).collection('achievements').stream()
        progress = [doc.to_dict() for doc in progress_docs]
        for p in progress:
            if 'completedAt' in p:
                p['completedAt'] = p['completedAt'].isoformat()
        return jsonify(progress)

    @app.route('/api/gamification/stats')
    @decorators.login_required
    def api_get_gamification_stats():
        stats_doc = firebase_service.db.collection('gamification').document(session['user']['uid']).get()
        if stats_doc.exists:
            return jsonify(stats_doc.to_dict())
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
        users_docs = firebase_service.db.collection('users').stream()
        users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            user_data['createdAt'] = user_data['createdAt'].isoformat()
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