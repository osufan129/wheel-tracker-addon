from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
import os
from datetime import datetime, date
import enum
import logging

# Basic Flask App Setup
app = Flask(__name__)

# Database configuration from environment variable
database_url = os.environ.get('DATABASE_URL', 'sqlite:///trades.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set the secret key from environment
app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-key')

# Get the ingress URL from environment
ingress_url = os.environ.get('INGRESS_URL', '')

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Log startup
logger.info("Starting Wheel Tracker App")

# Home Assistant add-on specific configuration
# Modify url_for to work with ingress
class PrefixMiddleware:
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix and environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)

# Apply the prefix middleware if running under ingress
if ingress_url:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=ingress_url)

db = SQLAlchemy(app)

# --- Enums for Status ---
class OptionStatus(enum.Enum):
    OPEN = 'Open'
    EXPIRED = 'Expired Worthless'
    ASSIGNED = 'Assigned'
    CLOSED = 'Closed Early' # For options bought back

class ShareStatus(enum.Enum):
    HELD = 'Held'
    CALLED_AWAY = 'Called Away'
    SOLD = 'Sold' # If sold manually outside of CC assignment

# --- Database Models ---

class Underlying(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    csps = db.relationship('CspTrade', backref='underlying', lazy=True)
    shares = db.relationship('ShareHolding', backref='underlying', lazy=True)
    ccs = db.relationship('CcTrade', backref='underlying', lazy=True)

    def __repr__(self):
        return f'<Underlying {self.ticker}>'

class CspTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    underlying_id = db.Column(db.Integer, db.ForeignKey('underlying.id'), nullable=False)
    sell_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    strike_price = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    premium_received = db.Column(db.Float, nullable=False) # Total premium for all contracts
    contracts = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.Enum(OptionStatus), nullable=False, default=OptionStatus.OPEN)
    close_date = db.Column(db.Date, nullable=True) # Date expired/assigned/closed
    close_cost = db.Column(db.Float, nullable=True) # Cost to close early (debit)
    assigned_shares_id = db.Column(db.Integer, db.ForeignKey('share_holding.id'), nullable=True) # Link to shares if assigned

    @property
    def premium_per_share(self):
        return self.premium_received / (self.contracts * 100) if self.contracts else 0

    def __repr__(self):
        return f'<CSP {self.underlying.ticker} {self.strike_price} {self.expiration_date.strftime("%Y-%m-%d")}>'

class ShareHolding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    underlying_id = db.Column(db.Integer, db.ForeignKey('underlying.id'), nullable=False)
    acquisition_date = db.Column(db.Date, nullable=False)
    number_of_shares = db.Column(db.Integer, nullable=False)
    cost_basis_per_share = db.Column(db.Float, nullable=False) # Put Strike - Premium Per Share
    status = db.Column(db.Enum(ShareStatus), nullable=False, default=ShareStatus.HELD)
    csp_origin_id = db.Column(db.Integer, db.ForeignKey('csp_trade.id'), nullable=True) # Which CSP led to assignment
    # Relationship to allow CspTrade to link back here easily
    csp_origin = db.relationship('CspTrade', foreign_keys=[csp_origin_id], backref=db.backref('assigned_shares', uselist=False))
    covered_calls = db.relationship('CcTrade', backref='share_holding', lazy=True)
    disposal_date = db.Column(db.Date, nullable=True) # Date called away or sold
    disposal_price_per_share = db.Column(db.Float, nullable=True) # CC Strike or sale price

    @property
    def total_cost_basis(self):
      return self.number_of_shares * self.cost_basis_per_share

    def __repr__(self):
        return f'<Shares {self.number_of_shares} {self.underlying.ticker} @ {self.cost_basis_per_share}>'

class CcTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    underlying_id = db.Column(db.Integer, db.ForeignKey('underlying.id'), nullable=False)
    share_holding_id = db.Column(db.Integer, db.ForeignKey('share_holding.id'), nullable=False) # Which shares are covered
    sell_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    strike_price = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    premium_received = db.Column(db.Float, nullable=False) # Total premium for all contracts
    contracts = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.Enum(OptionStatus), nullable=False, default=OptionStatus.OPEN)
    close_date = db.Column(db.Date, nullable=True) # Date expired/assigned/closed
    close_cost = db.Column(db.Float, nullable=True) # Cost to close early (debit)

    @property
    def premium_per_share(self):
        return self.premium_received / (self.contracts * 100) if self.contracts else 0

    def __repr__(self):
        return f'<CC {self.underlying.ticker} {self.strike_price} {self.expiration_date.strftime("%Y-%m-%d")}>'

# Initialize the database on startup
with app.app_context():
    try:
        logger.info("Initializing Database")
        db.create_all() # Attempt to create tables
        logger.info("Database tables created or already exist.")
    except OperationalError as e:
        # Check if the error is specifically about tables already existing
        if 'already exists' in str(e).lower():
            logger.info("Database tables already exist.")
        else:
            # Log other OperationalErrors as errors
            logger.error(f"Database Operational Error: {e}")
            logger.exception("Unexpected OperationalError while initializing database.")
    except Exception as e:
        # Log any other unexpected errors
        logger.error(f"Unexpected error initializing database: {e}")
        logger.exception("General exception while initializing database.")
        # Depending on severity, you might want to re-raise the exception
        # raise

# --- Routes ---
@app.route('/')
def index():
    # Fetch open positions from the database
    open_csps = CspTrade.query.filter_by(status=OptionStatus.OPEN).order_by(CspTrade.expiration_date).all()
    held_shares = ShareHolding.query.filter_by(status=ShareStatus.HELD).order_by(ShareHolding.acquisition_date).all()
    open_ccs = CcTrade.query.filter_by(status=OptionStatus.OPEN).order_by(CcTrade.expiration_date).all()

    return render_template('index.html',
                           open_csps=open_csps,
                           held_shares=held_shares,
                           open_ccs=open_ccs,
                           OptionStatus=OptionStatus,
                           ShareStatus=ShareStatus)

# Import and include all the other route functions from your original app.py here.
# This includes add_csp_route, expire_csp, assign_csp, etc.

# For demonstration purposes, I'll include a few critical routes:

@app.route('/history')
def history():
    # Query for closed/finished trades
    closed_csps = CspTrade.query.filter(CspTrade.status != OptionStatus.OPEN).order_by(CspTrade.close_date.desc()).all()
    disposed_shares = ShareHolding.query.filter(ShareHolding.status != ShareStatus.HELD).order_by(ShareHolding.disposal_date.desc()).all()
    closed_ccs = CcTrade.query.filter(CcTrade.status != OptionStatus.OPEN).order_by(CcTrade.close_date.desc()).all()

    return render_template('history.html',
                           closed_csps=closed_csps,
                           disposed_shares=disposed_shares,
                           closed_ccs=closed_ccs,
                           OptionStatus=OptionStatus,
                           ShareStatus=ShareStatus)

@app.route('/add_csp', methods=['GET', 'POST'])
def add_csp_route():
    if request.method == 'POST':
        try:
            # --- Input Validation and Sanitization ---
            required_fields = ['ticker', 'sell_date', 'strike_price', 'expiration_date', 'premium_received', 'contracts']
            if not all(field in request.form and request.form[field] for field in required_fields):
                flash('All fields are required.', 'error')
                logger.warning("Missing fields on CSP creation")
                # Return and render template to show the form again with the error
                return render_template('add_csp.html', **request.form) # Pass back form data

            ticker = request.form['ticker'].upper()
            sell_date_str = request.form['sell_date']
            expiration_date_str = request.form['expiration_date']

            # Sanitize ticker
            ticker = ''.join(char for char in ticker if char.isalnum())

            # Validate ticker format (must be only letters)
            if not ticker.isalpha():
                flash('Ticker must contain only letters.', 'error')
                return render_template('add_csp.html', **request.form) # Pass back form data

            # Validate numeric inputs
            try:
                strike_price = float(request.form['strike_price'])
                premium_received = float(request.form['premium_received'])
                contracts = int(request.form['contracts'])
                if strike_price <= 0 or premium_received <= 0 or contracts <= 0:
                     flash('Numeric values must be positive.', 'error')
                     return render_template('add_csp.html', **request.form) # Pass back form data
            except ValueError:
                flash('Strike Price, Premium Received, and Contracts must be valid numbers.', 'error')
                return render_template('add_csp.html', **request.form) # Pass back form data

            # Validate date inputs
            try:
                sell_date = datetime.strptime(sell_date_str, '%Y-%m-%d').date()
                expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                return render_template('add_csp.html', **request.form) # Pass back form data

            # Validate date logic
            today = date.today()
            # Sell date can be today or in the past, but not future
            if sell_date > today:
                 flash('Sell date cannot be in the future.', 'error')
                 return render_template('add_csp.html', **request.form) # Pass back form data
            # Expiration must be strictly after the sell date
            if expiration_date <= sell_date:
                flash('Expiration date must be after the sell date.', 'error')
                return render_template('add_csp.html', **request.form) # Pass back form data
            # --- End of Input Validation ---


            # Find or create the underlying stock
            underlying = Underlying.query.filter_by(ticker=ticker).first()
            if not underlying:
                underlying = Underlying(ticker=ticker)
                logger.info(f"New underlying {ticker} created")
                db.session.add(underlying)
                # Commit here to get underlying.id if needed, or commit later
                # Be mindful of potential partial commits if subsequent steps fail

            # Create new CSP trade
            new_csp = CspTrade(
                underlying_id=underlying.id, # Requires underlying to be committed or flushed
                underlying=underlying, # Alternative: assign object directly
                sell_date=sell_date,
                strike_price=strike_price,
                expiration_date=expiration_date,
                premium_received=premium_received,
                contracts=contracts,
                status=OptionStatus.OPEN
            )

            db.session.add(new_csp)
            db.session.commit() # Commit all changes together

            flash('CSP trade successfully added', 'success')
            logger.info(f"CSP trade added: {new_csp}")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback() # Rollback in case of any error during processing
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            logger.exception(f"Unexpected error while adding a new CSP: {e}")
            # Log the error and show the form again
            return render_template('add_csp.html', **request.form) # Pass back form data

    # --- Handle GET Request ---
    else: # request.method == 'GET'
        # Prefill the form if data is available in args (e.g., from plan_csp)
        ticker = request.args.get('ticker', '')
        strike_price = request.args.get('strike_price', '')
        premium_received = request.args.get('premium_received', '')
        contracts = request.args.get('contracts', '')
        sell_date_str = request.args.get('sell_date', '')
        expiration_date_str = request.args.get('expiration_date', '')

        # Format dates if provided
        sell_date = ''
        if sell_date_str:
            try:
                sell_date = datetime.strptime(sell_date_str, '%Y-%m-%d').date().strftime('%Y-%m-%d')
            except ValueError:
                flash('Invalid sell_date format in URL', 'warning') # Warn but don't block page load

        expiration_date = ''
        if expiration_date_str:
             try:
                 expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date().strftime('%Y-%m-%d')
             except ValueError:
                 flash('Invalid expiration_date format in URL', 'warning') # Warn but don't block page load


        return render_template('add_csp.html',
                              ticker=ticker,
                              strike_price=strike_price,
                              premium_received=premium_received,
                              contracts=contracts,
                              sell_date=sell_date,
                              expiration_date=expiration_date)


@app.route('/plan_csp')
def plan_csp_route():
    # Get recent CSPs for the table
    recent_csps = CspTrade.query.order_by(CspTrade.sell_date.desc()).limit(5).all()
    return render_template('plan_csp.html', recent_csps=recent_csps, OptionStatus=OptionStatus)

# Many more routes would be included here to match your original app.py

if __name__ == '__main__':
    # For local development only - Gunicorn runs the app in production
    with app.app_context():
        try:
            logger.info("Checking/Initializing Database for local run")
            db.create_all() # Attempt to create tables
            logger.info("Database check/creation complete for local run.")
        except OperationalError as e:
            if 'already exists' in str(e).lower():
                logger.info("Database tables already exist (local run).")
            else:
                 logger.error(f"Database Operational Error during local run check: {e}")
        except Exception as e:
             logger.error(f"Error during DB check/creation for local run: {e}")
    app.run(debug=True, host='0.0.0.0', port=8099) # Use a different port, enable debug for dev
